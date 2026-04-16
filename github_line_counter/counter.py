import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .config import CATEGORIES, SKIP_DIR_NAMES, SKIP_SUFFIXES, SOURCE_EXTENSIONS, SOURCE_FILENAMES
from .github import list_repos
from .models import RepoCount, RepoInfo
from .shell import run_cmd


def detect_category(topics: list[str]) -> tuple[str | None, str | None]:
    matches = [category for category in CATEGORIES if category in topics]
    if not matches:
        return None, "missing category topic"
    if len(matches) > 1:
        return None, f"multiple category topics: {', '.join(matches)}"
    return matches[0], None


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


def count_repo_lines(repo: RepoInfo, work_root: str) -> RepoCount:
    category, category_error = detect_category(repo.topics)
    if category_error:
        return RepoCount(repo=repo, category=None, lines=0, files=0, skipped_reason=category_error)

    clone_dir = os.path.join(work_root, repo.name_with_owner.replace("/", "__"))
    try:
        run_cmd(["gh", "repo", "clone", repo.name_with_owner, clone_dir, "--", "--depth=1"])
        tracked = run_cmd(["git", "ls-files", "-z"], cwd=clone_dir)
        total_lines = 0
        counted_files = 0
        for rel_path in [entry for entry in tracked.split("\x00") if entry]:
            if not should_count_file(rel_path):
                continue
            full_path = os.path.join(clone_dir, rel_path)
            if is_probably_binary(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as handle:
                    total_lines += sum(1 for _ in handle)
                counted_files += 1
            except OSError:
                continue
        return RepoCount(repo=repo, category=category, lines=total_lines, files=counted_files)
    finally:
        shutil.rmtree(clone_dir, ignore_errors=True)


def collect_payload(owner: str, limit: int, workers: int) -> dict:
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

    print(f"[count_github_lines] counting {len(repos)} repos", flush=True)
    with tempfile.TemporaryDirectory(prefix="gh-line-count-") as tempdir:
        results: list[RepoCount] = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            future_map = {
                executor.submit(count_repo_lines, repo, tempdir): repo.name_with_owner
                for repo in repos
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

