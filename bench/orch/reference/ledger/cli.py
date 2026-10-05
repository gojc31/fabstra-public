import argparse
import json
import os
import sys
from decimal import Decimal

from ledger.parse import ParseError, parse_csv
from ledger.report import render_text, summarise
from ledger.rules import RulesError, categorise, load_rules


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledger")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("summarize")
    s.add_argument("csv")
    s.add_argument("--rules", required=True)
    s.add_argument("--json", action="store_true")
    return parser


def _default(obj):
    if isinstance(obj, Decimal):
        return f"{obj:.2f}"
    raise TypeError(f"not JSON serialisable: {type(obj).__name__}")


def main(argv=None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    for path in (args.csv, args.rules):
        if not os.path.isfile(path):
            print(f"error: file not found: {path}", file=sys.stderr)
            return 1
    try:
        rules = load_rules(args.rules)
        txs = [categorise(t, rules) for t in parse_csv(args.csv)]
    except (ParseError, RulesError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    summary = summarise(txs)
    if args.json:
        print(json.dumps(summary, indent=2, default=_default))
    else:
        print(render_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
