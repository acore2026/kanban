import json

from .models import RepoInfo
from .shell import run_cmd


def list_repos(owner: str, limit: int) -> list[RepoInfo]:
    output = run_cmd(
        [
            "gh",
            "repo",
            "list",
            owner,
            "--limit",
            str(limit),
            "--json",
            "nameWithOwner,url,repositoryTopics,isFork,isArchived",
        ]
    )
    repos = []
    for item in json.loads(output):
        raw_topics = item.get("repositoryTopics") or []
        topics = [
            topic["name"]
            for topic in raw_topics
            if isinstance(topic, dict) and "name" in topic
        ]
        repos.append(
            RepoInfo(
                name_with_owner=item["nameWithOwner"],
                url=item["url"],
                topics=topics,
            )
        )
    return repos
