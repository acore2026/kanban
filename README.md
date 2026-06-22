# GitHub Line Counter

Count source lines across GitHub repositories and display the results in a local visual dashboard.

The tool groups repositories by a local `repos.yaml` file:

- `arch`
- `acn`
- `up`
- `compute`

Repositories missing from `repos.yaml`, or mapped to `unknown`/`NA`/blank, are ignored.

Example:

```yaml
acore2026/acn_gw: acn
acore2026/arc-ui: arch
acore2026/tp: unknown
```

## Requirements

- Python `>=3.10`
- [`uv`](https://docs.astral.sh/uv/)
- GitHub CLI, `gh`
- An authenticated GitHub CLI session:

```bash
gh auth status
```

## Run Dashboard

Start the dashboard on port `9004`:

```bash
uv run main.py acore2026 --port 9004
```

Then open:

```text
http://<server-ip>:9004
```

The server binds to `0.0.0.0`, so use the machine's real IP address when opening it from another machine.

## JSON Output

Print the same data as JSON without starting the dashboard:

```bash
uv run main.py acore2026 --json
```

## Useful Options

Limit the number of repositories fetched from GitHub:

```bash
uv run main.py acore2026 --limit 50 --port 9004
```

Increase parallel repo processing:

```bash
uv run main.py acore2026 --workers 8 --port 9004
```

Use a different mapping file:

```bash
uv run main.py acore2026 --repo-map ./my-repos.yaml --port 9004
```

Run as a Python module:

```bash
uv run python -m github_line_counter acore2026 --port 9004
```

## Notes

- The first startup can take a while because the tool builds a complete snapshot before serving the page.
- Source lines are counted from GitHub repository tarballs.
- Minified JavaScript/CSS, common build folders, virtual environments, and dependency folders are ignored.
- GitHub topics are no longer used for categorization.
