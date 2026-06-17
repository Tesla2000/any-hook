# Knowledge Base: Creating Pre-commit Hooks

This directory is a self-contained knowledge base about **writing, configuring, and maintaining pre-commit hooks** (the `pre-commit` framework, custom hook scripts, CI integration, etc.).

## Structure

- `raw/` — source material dropped in by the user (articles, docs, transcripts, code snippets, configs). Files here are never edited, only read and processed.
- `wiki/` — the organized knowledge base. Markdown pages cross-referenced with `[[wikilinks]]`.
- `learnings.md` — running log of what worked / didn't when building and using this KB.
- `CLAUDE.md` — this file. The schema and processing instructions.

## Processing a new file in `raw/`

When a new file appears in `raw/`, do the following:

1. **Read the raw file** in full.
2. **Extract key concepts** — discrete, reusable ideas (e.g. "hook stages", "language-specific hooks", "`pre-commit-config.yaml` syntax", "CI integration", "skipping hooks", "writing a custom hook"). Each concept worth its own page becomes a wiki page.
3. **Create or update wiki pages** in `wiki/` — one page per concept (see "Page conventions" below). If a concept already has a page, merge new information into it rather than duplicating.
4. **Cross-reference** — every page should link to related pages using `[[Page Name]]` wikilinks (exact match to the target page's filename without `.md`). Add a `## Related` section listing relevant links if not naturally covered in prose.
5. **Update `wiki/index.md`** — add/update entries linking to any new or changed pages, grouped by category.
6. **Update `learnings.md`** — append a dated entry noting what was extracted, any gaps, ambiguities, or conflicts found with existing pages, and how they were resolved.
7. **Never delete or edit files in `raw/`.** Treat them as immutable source material.

## Page conventions (`wiki/*.md`)

- **Filename**: `Title Case With Spaces.md` (matches the wikilink text exactly).
- **Frontmatter** (YAML):
  ```yaml
  ---
  title: Page Title
  tags: [tag1, tag2]
  sources: [raw/source-file.ext]
  updated: YYYY-MM-DD
  ---
  ```
- **Body structure**:
  - One-paragraph summary first.
  - `## Details` — the substantive explanation, examples, config snippets.
  - `## Related` — bullet list of `[[wikilinks]]` to related pages, each with a short note on the relationship.
- Keep pages focused on one concept. Split large pages rather than letting them sprawl.
- Prefer concrete examples (actual `.pre-commit-config.yaml` snippets, shell commands) over abstract description.
- When information conflicts across sources, note both views in the page and cite the source file each came from (via the `sources` frontmatter field).

## `wiki/index.md`

A single entry-point page listing all wiki pages grouped by category (e.g. "Concepts", "Configuration", "Hook Authoring", "CI/Tooling", "Troubleshooting"). Keep entries to one line each with a short description and a `[[wikilink]]`.

## Conventions

- Use `[[Wikilink]]` syntax everywhere for cross-references — no raw markdown links between wiki pages.
- Dates in `YYYY-MM-DD` format.
- No code comments inside example configs beyond what's needed to explain a non-obvious flag/option.
- Keep prose terse — this is a reference KB, not a tutorial.
