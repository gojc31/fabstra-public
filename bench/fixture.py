"""Create the benchmark fixture: a tiny repo with five planted bugs of rising subtlety.

Usage: python fixture.py <target_dir>
"""
import os
import subprocess
import sys

MODULE = '''import re
import time


def slugify(title: str) -> str:
    """Lowercase URL slug: words joined by single hyphens, no leading/trailing hyphens."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s                                   # BUG 1: never strips edge hyphens


def paginate(items, page, per_page=10):
    """Return the items on 1-indexed page `page`."""
    start = page * per_page                    # BUG 2: 0-indexed
    return items[start:start + per_page]


def parse_price(text: str) -> float:
    """Parse a display price such as "$1,234.50" into 1234.5."""
    return float(text.strip().lstrip("$"))     # BUG 3: thousands separator breaks float()


def dedupe(items):
    """Return the unique items, preserving first-seen order."""
    return list(set(items))                    # BUG 4: set() drops order


def retry(fn, times=3, delay=0.0):
    """Call fn until it succeeds; re-raise the last error after `times` failures."""
    for _ in range(times):
        try:
            return fn()
        except Exception:
            time.sleep(delay)
    return None                                # BUG 5: swallows the final error
'''

README = '''# bench fixture
Module `util.py`: slugify, paginate, parse_price, dedupe, retry. Standard library only.
'''


def main(target):
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, "util.py"), "w", newline="\n") as f:
        f.write(MODULE)
    with open(os.path.join(target, "README.md"), "w", newline="\n") as f:
        f.write(README)
    if not os.path.isdir(os.path.join(target, ".git")):
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    subprocess.run(["git", "-c", "user.email=bench@local", "-c", "user.name=bench",
                    "commit", "-q", "-m", "fixture", "--allow-empty"], cwd=target, check=True)
    print("fixture ready:", target)


if __name__ == "__main__":
    main(sys.argv[1])
