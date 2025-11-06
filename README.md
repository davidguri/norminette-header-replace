![Logo](/ascii-art-logo.png)

Batch-update 42-style headers with your name and realistic, same-day timestamps.

## Quick install (recommended)

Anyone can install the CLI:

```bash
pipx install "git+https://github.com/davidguri/norminette-header-replace.git"
```

## How to use

Below are a couple ways to use the cli. The `name` tag is the username you use at 42

### Help

```bash
norminette-header-replace --help
```

### Batch-replace

```bash
norminette-header-replace . \
  --name "jdoe" \
  --recursive \
  --preserve-width
```

### Add missing

```bash
norminette-header-replace . \
  --name "jdoe" \
  --email "john.doe@learner.42.tech" \
  --recursive \
  --preserve-width \
  --add-missing
```

### Dry-run (recommended first)

```bash
norminette-header-replace . --name "jdoe" --recursive --dry-run
```

### If you don't use pipx

```bash
git clone https://github.com/davidguri/norminette-header-replace
cd norminette-header-replace
python3 -m pip install .
norminette-header-replace --help
```
