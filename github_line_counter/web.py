import json
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .config import CATEGORIES
from .counter import collect_payload


def render_html(payload: dict, error: str | None = None) -> str:
    totals = payload.get("totals", {})
    repos = [repo for repo in payload.get("repos", []) if repo.get("category")]
    owner = escape(payload.get("owner", ""))
    total_lines = sum(item.get("lines", 0) for item in totals.values())
    total_files = sum(item.get("files", 0) for item in totals.values())

    category_cards = "".join(
        f"""
        <section class="card category-{category}">
          <div class="eyebrow">{category.upper()}</div>
          <div class="metric">{totals.get(category, {}).get('lines', 0):,}</div>
          <div class="meta">{totals.get(category, {}).get('files', 0):,} files</div>
        </section>
        """
        for category in CATEGORIES
    )

    repo_cards = "".join(_render_repo_card(repo) for repo in repos)
    error_html = f'<div class="error">{escape(error)}</div>' if error else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub Code Lines</title>
  <style>{_css()}</style>
</head>
<body>
  <main class="wrap">
    {error_html}
    <section class="hero">
      <div class="headline">
        <div class="eyebrow">GitHub Code Inventory</div>
        <h1>{owner}</h1>
        <div class="sub">Tracked source lines grouped by your local repo map. Repositories with blank or unknown categories are ignored.</div>
      </div>
      <div class="summary">
        <section class="mini-stat">
          <div class="eyebrow">Total Lines</div>
          <div class="value">{total_lines:,}</div>
        </section>
        <section class="mini-stat">
          <div class="eyebrow">Total Files</div>
          <div class="value">{total_files:,}</div>
        </section>
      </div>
    </section>
    <section class="category-grid">{category_cards}</section>
    <section class="panel">
      <div class="toolbar">
        <div>
          <h2>Repository Grid</h2>
          <div class="sub">Each card shows the repo category, counted files, and counted lines.</div>
        </div>
        <form method="post" action="/refresh">
          <button class="button" type="submit">Refresh From GitHub</button>
        </form>
      </div>
      <div class="repo-grid">{repo_cards}</div>
    </section>
  </main>
</body>
</html>
"""


def _render_repo_card(repo: dict) -> str:
    repo_name = escape(repo["repo"])
    category = escape(repo["category"])
    topics = "".join(f'<span class="topic">{escape(topic)}</span>' for topic in repo.get("topics", []))
    return f"""
    <article class="repo-card {category}">
      <div>
        <a href="https://github.com/{repo_name}" target="_blank" rel="noreferrer">{repo_name}</a>
        <div class="repo-category">{category}</div>
      </div>
      <div class="repo-metrics">{repo.get('lines', 0):,} lines / {repo.get('files', 0):,} files</div>
      <div class="topics">{topics}</div>
    </article>
    """


def _send_response(handler: BaseHTTPRequestHandler, body: bytes, content_type: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
    handler.send_header("Pragma", "no-cache")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def serve_dashboard(owner: str, limit: int, workers: int, port: int, repo_map_path: str = "repos.yaml") -> int:
    state = {"payload": None, "error": None}

    def refresh() -> None:
        print("[count_github_lines] building dashboard snapshot", flush=True)
        try:
            state["payload"] = collect_payload(owner, limit, workers, repo_map_path)
            state["error"] = None
        except Exception as exc:
            state["payload"] = state["payload"] or {
                "owner": owner,
                "totals": {},
                "repos": [],
                "skipped": [],
            }
            state["error"] = str(exc)
            print(f"[count_github_lines] error: {state['error']}", flush=True)

    refresh()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            payload = state["payload"] or {"owner": owner, "totals": {}, "repos": [], "skipped": []}
            if parsed.path == "/data":
                body = json.dumps(
                    {"payload": payload, "error": state["error"], "loading": False},
                    indent=2,
                ).encode("utf-8")
                _send_response(self, body, "application/json; charset=utf-8")
                return
            body = render_html(payload, error=state["error"]).encode("utf-8")
            _send_response(self, body, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/refresh":
                self.send_error(404)
                return
            refresh()
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[count_github_lines] serving dashboard on http://0.0.0.0:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _css() -> str:
    return """
    :root {
      --bg: #f4efe6;
      --panel: rgba(255,255,255,0.74);
      --ink: #1d1b16;
      --muted: #6c6458;
      --line: rgba(29,27,22,0.12);
      --arch: #c95b35;
      --acn: #1f6c5c;
      --up: #2d5e9d;
      --compute: #9f7a16;
      --bad: #8f2d23;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(201,91,53,0.20), transparent 28%),
        radial-gradient(circle at top right, rgba(31,108,92,0.18), transparent 24%),
        linear-gradient(180deg, #f8f2e8 0%, var(--bg) 100%);
    }
    .wrap { max-width: 1280px; margin: 0 auto; padding: 32px 20px 48px; }
    .hero { display: grid; grid-template-columns: 2fr 1fr; gap: 18px; align-items: end; margin-bottom: 22px; }
    .headline, .mini-stat, .card, .panel, .repo-card {
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--panel);
      backdrop-filter: blur(12px);
      box-shadow: 0 20px 50px rgba(60,40,10,0.08);
    }
    .headline { padding: 28px; }
    h1, h2 { margin: 0 0 12px; font-weight: 600; letter-spacing: -0.03em; }
    h1 { font-size: clamp(2rem, 4vw, 4.3rem); }
    h2 { font-size: 1.3rem; }
    .sub, .repo-metrics { color: var(--muted); font-size: 1rem; line-height: 1.5; }
    .summary { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .mini-stat, .card, .panel, .repo-card { padding: 20px; }
    .mini-stat .value, .metric { font-size: clamp(1.8rem, 3vw, 3rem); font-weight: 700; line-height: 1; }
    .eyebrow, .meta, .repo-category { text-transform: uppercase; letter-spacing: 0.14em; font-size: 0.75rem; color: var(--muted); }
    .category-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }
    .card { min-height: 160px; position: relative; overflow: hidden; }
    .card::after { content: ""; position: absolute; inset: auto -24px -32px auto; width: 110px; height: 110px; border-radius: 999px; opacity: 0.12; }
    .category-arch::after { background: var(--arch); }
    .category-acn::after { background: var(--acn); }
    .category-up::after { background: var(--up); }
    .category-compute::after { background: var(--compute); }
    .toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
    .button { appearance: none; border: 0; border-radius: 999px; background: var(--ink); color: white; padding: 12px 18px; font: inherit; cursor: pointer; }
    .repo-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }
    .repo-card { min-height: 170px; display: flex; flex-direction: column; gap: 12px; border-left-width: 8px; }
    .repo-card.arch { border-left-color: var(--arch); }
    .repo-card.acn { border-left-color: var(--acn); }
    .repo-card.up { border-left-color: var(--up); }
    .repo-card.compute { border-left-color: var(--compute); }
    .repo-card a { color: var(--ink); text-decoration: none; font-size: 1.1rem; font-weight: 700; }
    .repo-card a:hover { text-decoration: underline; }
    .topics { display: flex; gap: 8px; flex-wrap: wrap; margin-top: auto; }
    .topic { border-radius: 999px; padding: 5px 10px; background: rgba(29,27,22,0.06); font-size: 0.82rem; }
    .error { margin-bottom: 18px; padding: 14px 16px; border-radius: 16px; background: rgba(143,45,35,0.08); color: var(--bad); border: 1px solid rgba(143,45,35,0.2); }
    @media (max-width: 900px) { .hero, .category-grid { grid-template-columns: 1fr; } }
    """
