#!/usr/bin/env bash
set -e

git config --global --add safe.directory /workspace

if [ ! -f /root/.claude/settings.json ]; then
    cp /workspace/.devcontainer/claude-settings.json /root/.claude/settings.json
fi

uv sync --group dev

for i in 1 2 3; do
    npm install -g @anthropic-ai/claude-code && break
    echo "npm install attempt $i failed, retrying..."
    sleep 5
done
