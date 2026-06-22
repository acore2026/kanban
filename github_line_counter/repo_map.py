from pathlib import Path

from .config import CATEGORIES


IGNORE_VALUES = {"", "na", "n/a", "none", "null", "unknown", "-"}


def load_repo_categories(path: str | Path) -> dict[str, str]:
    categories: dict[str, str] = {}
    mapping_path = Path(path)
    if not mapping_path.exists():
        raise FileNotFoundError(f"repo category file not found: {mapping_path}")

    for line_no, raw_line in enumerate(mapping_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"{mapping_path}:{line_no}: expected 'repo: category'")
        repo_name, category = [part.strip() for part in line.split(":", 1)]
        if not repo_name:
            raise ValueError(f"{mapping_path}:{line_no}: missing repo name")
        normalized = category.lower()
        if normalized in IGNORE_VALUES:
            continue
        if normalized not in CATEGORIES:
            allowed = ", ".join(CATEGORIES)
            raise ValueError(f"{mapping_path}:{line_no}: unknown category '{category}', expected one of: {allowed}")
        categories[repo_name] = normalized
    return categories

