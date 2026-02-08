# any-hook Documentation

This directory contains the Sphinx documentation for any-hook.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install -e ".[docs]"
```

Or with uv:

```bash
uv sync --extra docs
```

### Build HTML Documentation

```bash
cd docs
make html
```

Or directly with sphinx-build:

```bash
cd docs
sphinx-build -b html . _build/html
```

### View Documentation

After building, open `docs/_build/html/index.html` in your web browser.

## Documentation Structure

- `index.rst` - Main documentation homepage
- `modifiers/` - Detailed documentation for each modifier
  - `index.rst` - Modifiers overview
  - Individual modifier pages (`.rst` files)
- `api/` - Core API reference
- `conf.py` - Sphinx configuration
- `_static/` - Static files (CSS, JS, images)
- `_templates/` - Custom Sphinx templates
- `_build/` - Generated documentation (not in git)

## CI/CD

Documentation is automatically built in GitHub Actions on every push and pull request.
See `.github/workflows/tests.yml` for the workflow configuration.

## Customization

To customize the documentation:

1. **Add content**: Edit `.rst` files or add new ones
2. **Change theme**: Modify `html_theme` in `conf.py`
3. **Add extensions**: Add to `extensions` list in `conf.py`
4. **Customize styling**: Add CSS to `_static/`

## Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Read the Docs Sphinx Theme](https://sphinx-rtd-theme.readthedocs.io/)
