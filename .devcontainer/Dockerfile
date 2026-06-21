FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
        build-essential \
        bubblewrap \
        socat \
        nodejs \
        npm \
        openssh-client \
        locales-all \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

RUN npm install -g @anthropic-ai/claude-code

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

ENV UV_LINK_MODE=copy
ENV PATH="/workspace/.venv/bin:${PATH}"
ENV PRE_COMMIT_HOME="/.jbdevcontainer/pre-commit"

WORKDIR /workspace

COPY pyproject.toml uv.lock .pre-commit-config.yaml README.md ./
RUN uv sync --group dev --no-install-project
RUN git config --global user.email "build@example.com" && \
    git config --global user.name "Build" && \
    git init && git add -A && git commit -m init && \
    pre-commit run --all-files; rm -rf .git

