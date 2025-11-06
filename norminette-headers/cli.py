from __future__ import annotations
import argparse
import os
import random
import re
from datetime import datetime, timedelta

HEADER_SCAN_LINES = 20

RE_BY       = re.compile(r"(.*?\bBy:\s*)([^<\n]*?)(\s*(<[^>]*>)?.*)$")
RE_CREATED  = re.compile(r"(.*?\bCreated:\s*)(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})(\s+by\s+.*)$")
RE_UPDATED  = re.compile(r"(.*?\bUpdated:\s*)(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})(\s+by\s+.*)$")

def format_42(dt: datetime) -> str:
    return dt.strftime("%Y/%m/%d %H:%M:%S")

def looks_like_42_header(lines):
    chunk = "\n".join(lines[:HEADER_SCAN_LINES])
    return all(s in chunk for s in ("By:", "Created:", "Updated:"))

def adjust_width_preserving_tail(old_line: str, new_line: str) -> str:
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
        return new_line
    run_len = run_end - run_start + 1
    if diff > 0:
        if run_len > diff:
            return new_line[:run_start] + (' ' * (run_len - diff)) + new_line[run_end+1:]
        return new_line
    return new_line[:run_start] + (' ' * (run_len - diff)) + new_line[run_end+1:]

def update_by_line(line: str, name: str, preserve_width: bool) -> str:
    m = RE_BY.match(line)
    if not m:
        return line
    left, _old, tail = m.groups()
    new_line = f"{left}{name}{tail}"
    return adjust_width_preserving_tail(line, new_line) if preserve_width else new_line

def update_dt_line(line: str, re_obj: re.Pattern, new_dt: datetime, preserve_width: bool) -> str:
    m = re_obj.match(line)
    if not m:
        return line
    left, _old_dt, tail = m.groups()
    new_line = f"{left}{format_42(new_dt)}{tail}"
    return adjust_width_preserving_tail(line, new_line) if preserve_width else new_line

def collect_files(root: str, exts, recursive: bool):
    exts = set(e.lower() for e in exts) if exts else None
    files = []
    if recursive:
        for dirpath, _dirs, fnames in os.walk(root):
            for fn in fnames:
                if not exts or os.path.splitext(fn)[1].lower() in exts:
                    files.append(os.path.join(dirpath, fn))
    else:
        for fn in os.listdir(root):
            p = os.path.join(root, fn)
            if os.path.isfile(p) and (not exts or os.path.splitext(fn)[1].lower() in exts):
                files.append(p)
    return sorted(files, key=lambda p: p.lower())

def plan_timeline(n_files: int, now: datetime, gap_min_s: int, gap_max_s: int,
                  work_min_s: int, work_max_s: int) -> list[tuple[datetime, datetime]]:
    """
    Returns [(created, updated), ...] of length n_files.
    Rules:
      - All timestamps are 'today' (local date of 'now').
      - Each file Updated - Created in [work_min_s, work_max_s] seconds (3–6 mins).
      - Created times increase by [gap_min_s, gap_max_s] (1–2 mins) between files.
      - Fit within today's end-of-day.
    """
    if n_files == 0:
        return []

    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)

    # Random gaps and work durations
    rng = random.Random()
    gaps = [rng.randint(gap_min_s, gap_max_s) for _ in range(max(n_files - 1, 0))]
    works = [rng.randint(work_min_s, work_max_s) for _ in range(n_files)]

    total_gaps = sum(gaps)
    max_tail = works[-1]
    total_span = total_gaps + max_tail

    # Latest safe base so last Updated <= end_of_day
    latest_base = end_of_day - timedelta(seconds=total_span)
    # Choose base <= now if possible; else clamp to start_of_day
    base = min(now, latest_base)
    if base < start_of_day:
        base = start_of_day + timedelta(seconds=1)

    times = []
    t = base
    for i in range(n_files):
        created = t
        updated = min(created + timedelta(seconds=works[i]), end_of_day)
        times.append((created, updated))
        if i < n_files - 1:
            t = t + timedelta(seconds=gaps[i])

    # Ensure all are today (just in case)
    times = [(max(start_of_day, c), min(end_of_day, u)) for c, u in times]
    return times

def process_file_with_times(path: str, name: str, created_dt: datetime, updated_dt: datetime,
                            preserve_width: bool, dry_run: bool):
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
            line = update_by_line(line, name, preserve_width)
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

    return changed, "ok"

def infer_default_name() -> str | None:
    # Try git config
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

def main():
    ap = argparse.ArgumentParser(
        description="Update 42 headers with your name and realistic per-file timelines (today)."
    )
    ap.add_argument("directory", help="Directory to scan")
    ap.add_argument("--name", help="Name to put in 'By:' line (default: $FORTY2_NAME or git user.name)")
    ap.add_argument("--ext", nargs="*", default=[".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".py"],
                    help="File extensions to include")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subdirectories")
    ap.add_argument("--preserve-width", action="store_true", help="Preserve header line widths")
    ap.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    ap.add_argument("--order", choices=["name", "mtime"], default="name",
                    help="Order files before timestamping (default: name)")
    ap.add_argument("--gap-min", type=int, default=60, help="Seconds between consecutive files (min, default 60)")
    ap.add_argument("--gap-max", type=int, default=120, help="Seconds between consecutive files (max, default 120)")
    ap.add_argument("--work-min", type=int, default=180, help="Seconds between Created and Updated (min, default 180)")
    ap.add_argument("--work-max", type=int, default=360, help="Seconds between Created and Updated (max, default 360)")
    ap.add_argument("--seed", type=int, help="Seed for reproducible timing plan")

    args = ap.parse_args()

    name = args.name or os.getenv("FORTY2_NAME") or infer_default_name()
    if not name:
        ap.error("Please provide --name or set $FORTY2_NAME or git user.name.")

    files = collect_files(args.directory, args.ext, args.recursive)
    if args.order == "mtime":
        files.sort(key=lambda p: os.path.getmtime(p))

    n = len(files)
    if n == 0:
        print("No files found with the given extensions.")
        return

    # Reproducibility
    if args.seed is not None:
        random.seed(args.seed)

    now = datetime.now()
    times = plan_timeline(
        n_files=n,
        now=now,
        gap_min_s=args.gap_min,
        gap_max_s=args.gap_max,
        work_min_s=args.work_min,
        work_max_s=args.work_max
    )

    updated = 0
    skipped = 0
    for path, (created_dt, updated_dt) in zip(files, times):
        did_change, status = process_file_with_times(
            path, name, created_dt, updated_dt, args.preserve_width, args.dry_run
        )
        if did_change:
            action = "WOULD UPDATE" if args.dry_run else "UPDATED"
            print(f"{action}: {path}  [{format_42(created_dt)} -> {format_42(updated_dt)}]")
            updated += 1
        else:
            skipped += 1
            if status not in ("no-42-header", "ok"):
                print(f"SKIP ({status}): {path}")

    print(f"\nDone. Files: {n}. Updated: {updated}. Skipped: {skipped}.")
