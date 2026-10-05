"""Create a fresh 'ledger' fixture repo for the orchestration eval.

Usage: python fixture.py <target_dir>
Writes the stub project (models.py given, the rest stubs), copies brief.md,
then git-inits and commits it. Stdlib only. Prints the target path.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

FILES = {
    "CLAUDE.md": "# ledger\nThrowaway eval project. Python 3.12, stdlib only. Tests: `python -m pytest -q` (local, no network).\n",
    "ledger/__init__.py": "",
    "ledger/models.py": '''from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class Transaction:
    date: date
    description: str
    amount: Decimal          # positive = money in, negative = money out
    category: str = "Uncategorised"
''',
    "ledger/parse.py": '''def parse_csv(path):
    raise NotImplementedError
''',
    "ledger/rules.py": '''def load_rules(path):
    raise NotImplementedError


def categorise(tx, rules):
    raise NotImplementedError
''',
    "ledger/report.py": '''def summarise(txs):
    raise NotImplementedError


def render_text(summary):
    raise NotImplementedError
''',
    "ledger/cli.py": '''def main(argv=None):
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
''',
    "tests/__init__.py": "",
    "tests/test_visible.py": '''from datetime import date
from decimal import Decimal

from ledger.models import Transaction
from ledger.parse import parse_csv
from ledger.report import summarise
from ledger.rules import categorise, load_rules


def test_parse_two_row_clean_csv(tmp_path):
    p = tmp_path / "two.csv"
    p.write_text("date,description,amount\\n2026-01-05,Coffee Shop,-4.50\\n2026-01-06,Salary,1000.00\\n", encoding="utf-8")
    assert parse_csv(p) == [
        Transaction(date(2026, 1, 5), "Coffee Shop", Decimal("-4.50")),
        Transaction(date(2026, 1, 6), "Salary", Decimal("1000.00")),
    ]


def test_categorise_one_transaction_by_substring(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text('[{"match": "Coffee", "category": "Food"}]', encoding="utf-8")
    tx = Transaction(date(2026, 1, 5), "Coffee Shop", Decimal("-4.50"))
    assert categorise(tx, load_rules(p)).category == "Food"


def test_summarise_two_transactions_in_one_month():
    txs = [
        Transaction(date(2026, 1, 5), "Coffee Shop", Decimal("-4.50"), "Food"),
        Transaction(date(2026, 1, 6), "Salary", Decimal("1000.00"), "Income"),
    ]
    month = summarise(txs)["months"][0]
    assert month["month"] == "2026-01"
    assert (month["income"], month["expense"], month["net"]) == (Decimal("1000.00"), Decimal("4.50"), Decimal("995.50"))
    assert month["categories"] == [
        {"category": "Income", "total": Decimal("1000.00")},
        {"category": "Food", "total": Decimal("-4.50")},
    ]
''',
    "samples/clean.csv": """date,description,amount
2026-01-03,Salary,2500.00
2026-01-05,Corner Shop,-23.40
2026-01-09,Coffee House,-4.50
2026-02-01,Rent,-900.00
""",
    "samples/rules.json": """[
  {"match": "salary", "category": "Income"},
  {"match": "shop", "category": "Groceries"},
  {"match": "rent", "category": "Housing"}
]
""",
}


def git(target, *args):
    subprocess.run(["git", "-C", target, *args], check=True, capture_output=True)


def main():
    if len(sys.argv) != 2:
        print("usage: python fixture.py <target_dir>", file=sys.stderr)
        return 2
    target = os.path.abspath(sys.argv[1])
    os.makedirs(target, exist_ok=True)
    for rel, text in FILES.items():
        path = os.path.join(target, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    shutil.copyfile(os.path.join(HERE, "brief.md"), os.path.join(target, "brief.md"))
    git(target, "init", "-q")
    git(target, "config", "user.name", "bench")
    git(target, "config", "user.email", "bench@local")
    git(target, "config", "core.autocrlf", "false")
    git(target, "add", "-A")
    git(target, "commit", "-q", "-m", "fixture")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
