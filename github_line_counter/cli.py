import argparse
import json
import sys

from .counter import collect_payload
from .web import serve_dashboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Count source lines across GitHub repos grouped by a local category map."
    )
    parser.add_argument("owner", help="GitHub user or organization name")
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of repositories to inspect (default: 200)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of repos to process in parallel (default: 4)",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of starting the dashboard")
    parser.add_argument("--port", type=int, default=9007, help="Dashboard port (default: 9007)")
    parser.add_argument(
        "--repo-map",
        default="repos.yaml",
        help="Local repo category mapping file (default: repos.yaml)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.json:
        try:
            payload = collect_payload(args.owner, args.limit, args.workers, args.repo_map)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    return serve_dashboard(args.owner, args.limit, args.workers, args.port, args.repo_map)
