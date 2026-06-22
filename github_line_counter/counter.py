import io
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath

from .config import CATEGORIES, SKIP_DIR_NAMES, SKIP_SUFFIXES, SOURCE_EXTENSIONS, SOURCE_FILENAMES
from .github import list_repos
from .models import RepoCount, RepoInfo
from .repo_map import load_repo_categories
from .shell import run_cmd


def should_count_file(path: str) -> bool:
    file_path = Path(path)
    lower_name = file_path.name.lower()
    if any(lower_name.endswith(suffix) for suffix in SKIP_SUFFIXES):
        return False
    if any(part in SKIP_DIR_NAMES for part in file_path.parts):
        return False
    if lower_name in SOURCE_FILENAMES:
        return True
    return file_path.suffix.lower() in SOURCE_EXTENSIONS


def is_probably_binary(path: str) -> bool:
    with open(path, "rb") as handle:
        return b"\x00" in handle.read(8192)


def get_github_token() -> str:
    return run_cmd(["gh", "auth", "token"]).strip()


def count_repo_lines(repo: RepoInfo, work_root: str, category: str, token: str | None = None) -> RepoCount:
    del work_root
    owner, name = repo.name_with_owner.split("/", 1)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{name}/tarball",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token or get_github_token()}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    total_lines = 0
    counted_files = 0
    with urllib.request.urlopen(request, timeout=60) as response:
        with tarfile.open(fileobj=response, mode="r|gz") as archive:
            for member in archive:
                if not member.isfile():
                    continue
                rel_path = _strip_archive_root(member.name)
                if not rel_path or not should_count_file(rel_path):
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                data = extracted.read()
                if b"\x00" in data[:8192]:
                    continue
                total_lines += len(io.TextIOWrapper(io.BytesIO(data), encoding="utf-8", errors="ignore").readlines())
                counted_files += 1
    return RepoCount(repo=repo, category=category, lines=total_lines, files=counted_files)


def _strip_archive_root(path: str) -> str:
    parts = PurePosixPath(path).parts
    if len(parts) <= 1:
        return ""
    return "/".join(parts[1:])


def collect_payload(owner: str, limit: int, workers: int, repo_map_path: str = "repos.yaml") -> dict:
    print(
        f"[count_github_lines] listing repos for {owner} (limit={limit}, workers={workers})",
        flush=True,
    )
    try:
        repos = list_repos(owner, limit)
    except Exception as exc:
        raise RuntimeError(f"failed to list repositories: {exc}") from exc

    if not repos:
        raise RuntimeError("no repositories found")

    repo_categories = load_repo_categories(repo_map_path)
    categorized_repos = [repo for repo in repos if repo.name_with_owner in repo_categories]
    if not categorized_repos:
        raise RuntimeError(f"no repositories matched categories in {repo_map_path}")

    print(f"[count_github_lines] counting {len(categorized_repos)} repos", flush=True)
    token = get_github_token()
    results: list[RepoCount] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {
            executor.submit(count_repo_lines, repo, "", repo_categories[repo.name_with_owner], token): repo.name_with_owner
            for repo in categorized_repos
        }
        for future in as_completed(future_map):
            repo_name = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    RepoCount(
                        repo=RepoInfo(name_with_owner=repo_name, url="", topics=[]),
                        category=None,
                        lines=0,
                        files=0,
                        skipped_reason=str(exc),
                    )
                )

    results.sort(key=lambda item: item.repo.name_with_owner.lower())
    totals = {category: 0 for category in CATEGORIES}
    files_by_category = {category: 0 for category in CATEGORIES}
    skipped = []
    for item in results:
        if item.category is None:
            skipped.append({"repo": item.repo.name_with_owner, "reason": item.skipped_reason})
            continue
        totals[item.category] += item.lines
        files_by_category[item.category] += item.files

    print("[count_github_lines] snapshot ready", flush=True)
    return {
        "owner": owner,
        "totals": {
            category: {"lines": totals[category], "files": files_by_category[category]}
            for category in CATEGORIES
        },
        "repos": [
            {
                "repo": item.repo.name_with_owner,
                "category": item.category,
                "lines": item.lines,
                "files": item.files,
                "topics": item.repo.topics,
                "skipped_reason": item.skipped_reason,
            }
            for item in results
            if item.category
        ],
        "skipped": skipped,
    }
