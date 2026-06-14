#!/bin/bash
input=$(cat)
file_path=$(echo "$input" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input', {}).get('file_path', ''))")

case "$file_path" in
  */kb/raw/*)
    cat <<EOF
{"decision": "block", "reason": "A new source file was written to kb/raw/ ($file_path). Per kb/CLAUDE.md, process it now: extract key concepts into wiki/ pages, cross-reference with [[wikilinks]], update wiki/index.md, and append an entry to kb/learnings.md."}
EOF
    ;;
  *)
    exit 0
    ;;
esac
