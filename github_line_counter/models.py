from dataclasses import dataclass


@dataclass
class RepoInfo:
    name_with_owner: str
    url: str
    topics: list[str]


@dataclass
class RepoCount:
    repo: RepoInfo
    category: str | None
    lines: int
    files: int
    skipped_reason: str | None = None

