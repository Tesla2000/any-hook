#!/usr/bin/env bash
set -e

git config --global --add safe.directory /workspace

if [ ! -f /root/.claude/settings.json ]; then
    cp /workspace/.devcontainer/claude-settings.json /root/.claude/settings.json
fi

uv sync --group dev
pre-commit install --overwrite --hook-type pre-commit --hook-type pre-push
