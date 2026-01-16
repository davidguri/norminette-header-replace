![Logo](/ascii-art-logo.png)

Batch-update or insert 42-style headers with your name and realistic, same-day timestamps.

## Quick install (recommended)

Anyone can install the CLI:

```bash
pipx install "git+https://github.com/davidguri/norminette-header-replace.git"
```

## How to use

Below are a couple ways to use the CLI. The `--name` value is your 42 username.
The header format follows the standard 42 ASCII scheme (as in the official vim script),
and the border stays fixed at 80 columns.

### Help

```bash
norminette-header-replace --help
```

### Batch update (default: update + insert missing)

```bash
norminette-header-replace . \
  --name "jdoe" \
  --recursive
```

### Update only (do not insert missing headers)

```bash
norminette-header-replace . \
  --name "jdoe" \
  --email "john.doe@learner.42.tech" \
  --recursive \
  --no-add-missing
```

### Dry-run (recommended first)

```bash
norminette-header-replace . --name "jdoe" --recursive --dry-run
```

### File types

The header uses the same comment styles as the vim script, based on file extension:
`.c .h .cc .hh .cpp .hpp .tpp .ipp .cxx .go .rs .php .java .kt .kts` (C-style),
`.html .htm .xml` (HTML), `.js .ts` (//), `.py` (#), `.lua` (--), `.vim`/`vimrc`,
`.el`/`emacs`/`.asm`, `.f90 .f95 .f03 .f .for`, `.tex`, `.ml .mli .mll .mly`.

You can override which files are scanned with `--ext`:

```bash
norminette-header-replace . \
  --name "jdoe" \
  --recursive \
  --ext .c .h .py .html .js
```

### If you don't use pipx

```bash
git clone https://github.com/davidguri/norminette-header-replace
cd norminette-header-replace
python3 -m pip install .
norminette-header-replace --help
```


# Coming soon

I'm of course planning to add some new features to this project, which you'll find in the form of a todo list below. If you have any ides/suggestions for what could be benefitial, you can reach me on Slack, my username is david.guri (should be pretty easy to find if you're part of the 42 Network, look in the Tirana campus). Free labor is always fun :)

- [ ] Make VS Code/Vim extension
- [ ] Add .editorconfig + lint checks for header width
- [ ] Add --exclude and .headerignore support
- [ ] Add --respect-gitignore option
- [ ] Add --updated-only to skip Created changes
- [ ] Add CI with unit tests

This project was based on the code from the official 42 Paris GitHub repo: https://github.com/42paris/42header