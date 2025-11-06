![Logo](/ascii-art-logo.png)

Batch-update 42-style headers with your name and realistic, same-day timestamps.

## Quick install (recommended)

Anyone can install the CLI:

```bash
pipx install "git+https://github.com/davidguri/norminette-header-replace.git"
```

## How to use

Below are a couple ways to use the cli

### Batch-replace

```bash
norminette-header-replace . \
  --name "David Guri" \
  --recursive \
  --preserve-width
```

### Dry-run (recommended first)

```bash
norminette-header-replace . --name "David Guri" --recursive --dry-run
```

### If you don't use pipx

```bash
git clone https://github.com/davidguri/norminette-header-replace
cd norminette-header-replace
python3 -m pip install .
norminette-header-replace --help
```