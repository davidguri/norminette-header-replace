# norminette_header_replace/cli.py
# CLI to update or insert 42-style headers with same-day, realistic timelines.
from __future__ import annotations

import argparse
import os
import random
import re
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

HEADER_SCAN_LINES = 20  # only look near the top

# Detect existing 42-ish fields
RE_BY      = re.compile(r"(.*?\bBy:\s*)([^<\n]*?)(\s*(<[^>]*>)?.*)$")
RE_CREATED = re.compile(r"(.*?\bCreated:\s*)(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})(\s+by\s+.*)$")
RE_UPDATED = re.compile(r"(.*?\bUpdated:\s*)(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})(\s+by\s+.*)$")

# ---------- Utilities ----------

def format_42(dt: datetime) -> str:
    """42 header datetime format."""
    return dt.strftime("%Y/%m/%d %H:%M:%S")

def looks_like_42_header(lines: List[str]) -> bool:
    """Cheap signature: has By/Created/Updated near the top."""
    chunk = "\n".join(lines[:HEADER_SCAN_LINES])
    return all(s in chunk for s in ("By:", "Created:", "Updated:"))

def adjust_width_preserving_tail(old_line: str, new_line: str) -> str:
    """
    Keep overall line length stable by adjusting the last run of spaces
    before the comment ender (*/). Best-effort; falls back to new_line.
    """
    if len(new_line) == len(old_line):
        return new_line

    end_idx = len(new_line)
    ender_pos = new_line.rfind("*/")
    if ender_pos != -1:
        end_idx = ender_pos

    diff = len(new_line) - len(old_line)

    run_start = None
    run_end = None
    i = end_idx - 1
    while i >= 0 and new_line[i] == ' ':
        run_end = i if run_end is None else run_end
        run_start = i
        i -= 1

    if run_start is None:
        return new_line  # nowhere to flex

    run_len = run_end - run_start + 1
    if diff > 0:
        # need to remove diff spaces
        if run_len > diff:
            return new_line[:run_start] + (' ' * (run_len - diff)) + new_line[run_end+1:]
        return new_line
    # need to add -diff spaces
    return new_line[:run_start] + (' ' * (run_len - diff)) + new_line[run_end+1:]

def update_by_line(line: str, name: str, email: Optional[str], preserve_width: bool) -> str:
    m = RE_BY.match(line)
    if not m:
        return line
    left, _old, tail = m.groups()
    by_val = name if not email else f"{name} <{email}>"
    new_line = f"{left}{by_val}{tail}"
    return adjust_width_preserving_tail(line, new_line) if preserve_width else new_line

def update_dt_line(line: str, re_obj: re.Pattern, new_dt: datetime, preserve_width: bool) -> str:
    m = re_obj.match(line)
    if not m:
        return line
    left, _old_dt, tail = m.groups()
    new_line = f"{left}{format_42(new_dt)}{tail}"
    return adjust_width_preserving_tail(line, new_line) if preserve_width else new_line

def collect_files(root: str, exts: Optional[List[str]], recursive: bool) -> List[str]:
    exts_set = set(e.lower() for e in exts) if exts else None
    files: List[str] = []
    if recursive:
        for dirpath, _dirs, fnames in os.walk(root):
            for fn in fnames:
                if not exts_set or os.path.splitext(fn)[1].lower() in exts_set:
                    files.append(os.path.join(dirpath, fn))
    else:
        for fn in os.listdir(root):
            p = os.path.join(root, fn)
            if os.path.isfile(p) and (not exts_set or os.path.splitext(fn)[1].lower() in exts_set):
                files.append(p)
    # default ordering: case-insensitive name
    return sorted(files, key=lambda p: p.lower())

def comment_style_for_ext(ext: str) -> str:
    ext = ext.lower()
    if ext in (".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".java", ".js", ".ts", ".tsx", ".cs"):
        return "c"      # /* ... */
    if ext in (".py", ".sh", ".rb", ".lua"):
        return "hash"   # # ...
    # default to C-style
    return "c"

def build_header_block(
    filename: str,
    name: str,
    email: Optional[str],
    created_dt: datetime,
    updated_dt: datetime,
    style: str = "c",
    width: int = 80
) -> List[str]:
    """
    Generate a robust 42-style header block.
    Not the ornate ASCII version—simple + norm-friendly + deterministic spacing.
    """
    created = format_42(created_dt)
    updated = format_42(updated_dt)
    by_line = f"By: {name}" + (f" <{email}>" if email else "")

    if style == "c":
        prefix = "/* "
        suffix = " */"
        inner_width = width - len(prefix) - len(suffix)

        def border(char: str = "*") -> str:
            return prefix + (char * inner_width) + suffix

        def blank() -> str:
            return prefix + (" " * inner_width) + suffix

        def content(text: str) -> str:
            return prefix + text.ljust(inner_width) + suffix

        return [
            border("*"),
            blank(),
            content(f"File: {os.path.basename(filename)}"),
            content(by_line),
            content(f"Created: {created} by {name}"),
            content(f"Updated: {updated} by {name}"),
            blank(),
            border("*"),
            "",
        ]

    # Hash style (Python/shell)
    line = "#" * width

    def hcontent(text: str) -> str:
        pad = max(0, width - 2 - len(text))
        return "# " + text + (" " * pad)

    return [
        line,
        hcontent(f"File: {os.path.basename(filename)}"),
        hcontent(by_line),
        hcontent(f"Created: {created} by {name}"),
        hcontent(f"Updated: {updated} by {name}"),
        line,
        "",
    ]

def insert_header_if_missing(
    path: str,
    name: str,
    email: Optional[str],
    created_dt: datetime,
    updated_dt: datetime,
    dry_run: bool
) -> Tuple[bool, str]:
    """
    If the file lacks a 42 header, insert one at the top.
    For scripts with a shebang, place header after the shebang.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return False, "read-fail"

    lines = content.splitlines(keepends=True)
    head = lines[:HEADER_SCAN_LINES]
    if looks_like_42_header(head):
        return False, "already-has-header"

    style = comment_style_for_ext(os.path.splitext(path)[1])
    header_lines = build_header_block(
        filename=path,
        name=name,
        email=email,
        created_dt=created_dt,
        updated_dt=updated_dt,
        style=style
    )
    header_text = "".join(l if l.endswith("\n") else l + "\n" for l in header_lines)

    insert_idx = 0
    # Preserve shebang on first line
    if lines and lines[0].startswith("#!"):
        insert_idx = 1

    new_content = "".join(lines[:insert_idx]) + header_text + "".join(lines[insert_idx:])
    if not dry_run:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception:
            return False, "write-fail"

    return True, "inserted"

def process_file_update_existing(
    path: str,
    name: str,
    email: Optional[str],
    created_dt: datetime,
    updated_dt: datetime,
    preserve_width: bool,
    dry_run: bool
) -> Tuple[bool, str]:
    """
    Update existing header fields (By/Created/Updated).
    Returns (changed, status). If no header present, returns (False, "no-42-header").
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return False, "read-fail"

    if not lines:
        return False, "empty"

    if not looks_like_42_header(lines[:HEADER_SCAN_LINES]):
        return False, "no-42-header"

    changed = False
    new_lines = list(lines)
    limit = min(HEADER_SCAN_LINES, len(lines))
    for i in range(limit):
        line = new_lines[i]
        orig = line
        if "By:" in line:
            line = update_by_line(line, name, email, preserve_width)
        if "Created:" in line:
            line = update_dt_line(line, RE_CREATED, created_dt, preserve_width)
        if "Updated:" in line:
            line = update_dt_line(line, RE_UPDATED, updated_dt, preserve_width)
        if line != orig:
            new_lines[i] = line
            changed = True

    if changed and not dry_run:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception:
            return False, "write-fail"

    return changed, "ok" if changed else "unchanged"

def plan_timeline(
    n_files: int,
    now: datetime,
    gap_min_s: int, gap_max_s: int,
    work_min_s: int, work_max_s: int
) -> List[Tuple[datetime, datetime]]:
    """
    Build [(created, updated), ...] for n_files.
      - All stamps are today (local).
      - Updated - Created in [work_min_s, work_max_s].
      - Created gaps in [gap_min_s, gap_max_s] between files.
      - Fit by end of day.
    """
    if n_files == 0:
        return []

    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)

    rng = random.Random()
    gaps = [rng.randint(gap_min_s, gap_max_s) for _ in range(max(n_files - 1, 0))]
    works = [rng.randint(work_min_s, work_max_s) for _ in range(n_files)]

    total_gaps = sum(gaps)
    max_tail = works[-1]
    total_span = total_gaps + max_tail

    latest_base = end_of_day - timedelta(seconds=total_span)
    base = min(now, latest_base)
    if base < start_of_day:
        base = start_of_day + timedelta(seconds=1)

    times: List[Tuple[datetime, datetime]] = []
    t = base
    for i in range(n_files):
        created = t
        updated = min(created + timedelta(seconds=works[i]), end_of_day)
        times.append((created, updated))
        if i < n_files - 1:
            t = t + timedelta(seconds=gaps[i])

    # Clamp to today
    return [(max(start_of_day, c), min(end_of_day, u)) for c, u in times]

def infer_default_name() -> Optional[str]:
    """Try git config user.name as a fallback."""
    try:
        import subprocess
        name = subprocess.check_output(
            ["git", "config", "--get", "user.name"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if name:
            return name
    except Exception:
        pass
    return None

# ---------- CLI ----------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Update or insert 42-style headers with same-day, realistic timestamps."
    )
    ap.add_argument("directory", help="Directory to scan")
    ap.add_argument("--name", help="Name for 'By:' (default: $FORTY2_NAME or git user.name)")
    ap.add_argument("--email", help="Email for 'By:' (optional, or set $FORTY2_EMAIL)")
    ap.add_argument("--ext", nargs="*", default=[".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".py"],
                    help="File extensions to include")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subdirectories")
    ap.add_argument("--preserve-width", action="store_true",
                    help="Preserve existing header line widths when updating")
    ap.add_argument("--dry-run", action="store_true", help="Preview without writing")
    ap.add_argument("--order", choices=["name", "mtime"], default="name",
                    help="Order files before timestamping (default: name)")
    # Timing knobs (defaults match: 1–2 min gaps, 3–6 min work)
    ap.add_argument("--gap-min", type=int, default=60, help="Seconds between consecutive files (min, default 60)")
    ap.add_argument("--gap-max", type=int, default=120, help="Seconds between consecutive files (max, default 120)")
    ap.add_argument("--work-min", type=int, default=180, help="Seconds between Created and Updated (min, default 180)")
    ap.add_argument("--work-max", type=int, default=360, help="Seconds between Created and Updated (max, default 360)")
    ap.add_argument("--seed", type=int, help="Seed for reproducible timing plan")
    # Add headers when missing
    ap.add_argument("--add-missing", action="store_true",
                    help="Insert a 42-style header if the file does not have one")

    args = ap.parse_args()

    name = args.name or os.getenv("FORTY2_NAME") or infer_default_name()
    if not name:
        ap.error("Please provide --name or set $FORTY2_NAME or configure git user.name.")

    email = args.email or os.getenv("FORTY2_EMAIL")

    files = collect_files(args.directory, args.ext, args.recursive)
    if not files:
        print("No files found with the given extensions.")
        return

    if args.order == "mtime":
        files.sort(key=lambda p: os.path.getmtime(p))

    if args.seed is not None:
        random.seed(args.seed)

    now = datetime.now()
    times = plan_timeline(
        n_files=len(files),
        now=now,
        gap_min_s=args.gap_min,
        gap_max_s=args.gap_max,
        work_min_s=args.work_min,
        work_max_s=args.work_max
    )

    updated_cnt = 0
    inserted_cnt = 0
    skipped_cnt = 0

    for path, (created_dt, updated_dt) in zip(files, times):
        changed, status = process_file_update_existing(
            path, name, email, created_dt, updated_dt, args.preserve_width, args.dry_run
        )
        if changed:
            updated_cnt += 1
            print(f"{'WOULD UPDATE' if args.dry_run else 'UPDATED'}: {path} "
                  f"[{format_42(created_dt)} -> {format_42(updated_dt)}]")
            continue

        # No header found: optionally insert one
        if status == "no-42-header" and args.add-missing:
            did_insert, istatus = insert_header_if_missing(
                path, name, email, created_dt, updated_dt, args.dry_run
            )
            if did_insert:
                inserted_cnt += 1
                print(f"{'WOULD INSERT' if args.dry_run else 'INSERTED'}: {path} "
                      f"[{format_42(created_dt)} -> {format_42(updated_dt)}]")
            else:
                skipped_cnt += 1
                if istatus not in ("already-has-header",):
                    print(f"SKIP ({istatus}): {path}")
        else:
            skipped_cnt += 1
            # quiet skip for unchanged/ok

    print(f"\nDone. Files: {len(files)}. Updated: {updated_cnt}. Inserted: {inserted_cnt}. Skipped: {skipped_cnt}.")

if __name__ == "__main__":
    main()
