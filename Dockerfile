FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    GH_PROMPT_DISABLED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates gh git python3 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md main.py ./
COPY github_line_counter ./github_line_counter

EXPOSE 7104

ENTRYPOINT ["python3", "main.py"]
CMD ["acore2026", "--port", "7104"]
