"""Held-out acceptance tests for the ledger fixture. Never copied into the work dir.

Run from anywhere with PYTHONPATH=<work>:  python -m pytest -q hidden/test_hidden.py
Each test is named for the brief.md rule it checks.
"""
import json
import re
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import ledger
from ledger.models import Transaction

WORK = Path(ledger.__file__).resolve().parent.parent

HEADER = "date,description,amount\n"


def write_csv(tmp_path, text, name="in.csv", bom=False):
    p = tmp_path / name
    data = text.encode("utf-8")
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
    return p


def write_rules(tmp_path, rules, name="rules.json"):
    p = tmp_path / name
    p.write_text(json.dumps(rules), encoding="utf-8")
    return p


def parse(tmp_path, text, **kw):
    from ledger.parse import parse_csv
    return parse_csv(write_csv(tmp_path, text, **kw))


def tx(d, desc, amt, cat="Uncategorised"):
    return Transaction(d, desc, Decimal(amt), cat)


def mentions(msg, number):
    return re.search(rf"(?<!\d){number}(?!\d)", str(msg)) is not None


# ---------------------------------------------------------------- T1 parse.py

def test_parse_header_case_insensitive_extra_columns_ignored(tmp_path):
    txs = parse(tmp_path, "Date,DESCRIPTION,Amount,Balance\n2026-01-05,Shop,-4.50,100.00\n")
    assert txs == [tx(date(2026, 1, 5), "Shop", "-4.50")]


def test_parse_column_order_may_vary(tmp_path):
    txs = parse(tmp_path, "amount,Ref,description,date\n12.00,X1,Refund,2026-03-02\n")
    assert txs == [tx(date(2026, 3, 2), "Refund", "12.00")]


def test_parse_tolerates_utf8_bom(tmp_path):
    txs = parse(tmp_path, HEADER + "2026-01-05,Shop,-4.50\n", bom=True)
    assert txs == [tx(date(2026, 1, 5), "Shop", "-4.50")]


def test_parse_skips_blank_lines(tmp_path):
    txs = parse(tmp_path, HEADER + "\n2026-01-05,Shop,-4.50\n\n2026-01-06,Cafe,-3.00\n\n")
    assert [t.description for t in txs] == ["Shop", "Cafe"]


def test_parse_dates_iso_and_day_first(tmp_path):
    txs = parse(tmp_path, HEADER + "2026-02-01,A,1.00\n03/04/2026,B,1.00\n31/12/2025,C,1.00\n")
    assert [t.date for t in txs] == [date(2026, 2, 1), date(2026, 4, 3), date(2025, 12, 31)]


def test_parse_bad_date_raises_parse_error_with_line_number(tmp_path):
    from ledger.parse import ParseError
    assert issubclass(ParseError, ValueError)
    text = HEADER + "2026-01-05,Shop,-1.00\n2026-01-06,Cafe,-2.00\nJan 9 2026,Bad,-7.00\n"
    with pytest.raises(ParseError) as exc:
        parse(tmp_path, text)
    assert mentions(exc.value, 4)


def test_parse_amount_dollar_with_thousands_separator(tmp_path):
    txs = parse(tmp_path, HEADER + '2026-01-05,Laptop,"$1,234.50"\n')
    assert txs[0].amount == Decimal("1234.50")
    assert isinstance(txs[0].amount, Decimal)


def test_parse_amount_parentheses_mean_negative(tmp_path):
    txs = parse(tmp_path, HEADER + "2026-01-05,Fee,(45.00)\n")
    assert txs[0].amount == Decimal("-45.00")


def test_parse_amount_leading_minus_means_negative(tmp_path):
    txs = parse(tmp_path, HEADER + "2026-01-05,Fee,-45.00\n")
    assert txs[0].amount == Decimal("-45.00")


def test_parse_amount_pound_symbol(tmp_path):
    txs = parse(tmp_path, HEADER + "2026-01-05,Tea,£3.20\n")
    assert txs[0].amount == Decimal("3.20")


def test_parse_amount_is_decimal_not_float(tmp_path):
    txs = parse(tmp_path, HEADER + "2026-01-05,A,0.10\n2026-01-06,B,0.20\n")
    assert all(type(t.amount) is Decimal for t in txs)
    assert txs[0].amount + txs[1].amount == Decimal("0.30")


def test_parse_bad_amount_raises_parse_error_with_line_number(tmp_path):
    from ledger.parse import ParseError
    with pytest.raises(ParseError) as exc:
        parse(tmp_path, HEADER + "2026-01-05,Shop,-1.00\n2026-01-06,Cafe,abc\n")
    assert mentions(exc.value, 3)


def test_parse_description_whitespace_collapsed(tmp_path):
    txs = parse(tmp_path, HEADER + '2026-01-05,"  Corner   Shop\t Ltd ",-4.50\n')
    assert txs[0].description == "Corner Shop Ltd"


def test_parse_duplicates_keep_first_in_file_order(tmp_path):
    text = HEADER + (
        "2026-01-05,Shop,-4.50\n"
        "2026-01-06,Cafe,-3.00\n"
        "2026-01-05,  Shop ,-4.50\n"      # duplicate of row 1 after normalisation
        "2026-01-05,Shop,-4.51\n"         # different amount: kept
        "2026-01-04,Bakery,-2.00\n"
    )
    txs = parse(tmp_path, text)
    assert [(t.date.day, t.description, t.amount) for t in txs] == [
        (5, "Shop", Decimal("-4.50")),
        (6, "Cafe", Decimal("-3.00")),
        (5, "Shop", Decimal("-4.51")),
        (4, "Bakery", Decimal("-2.00")),
    ]


# ---------------------------------------------------------------- T2 rules.py

def test_rules_first_matching_rule_wins(tmp_path):
    from ledger.rules import categorise, load_rules
    rules = load_rules(write_rules(tmp_path, [
        {"match": "coffee", "category": "Cafe"},
        {"match": "coffee shop", "category": "Shops"},
    ]))
    assert categorise(tx(date(2026, 1, 1), "Coffee Shop", "-3"), rules).category == "Cafe"


def test_rules_match_is_case_insensitive_substring(tmp_path):
    from ledger.rules import categorise, load_rules
    rules = load_rules(write_rules(tmp_path, [{"match": "TESCO", "category": "Groceries"}]))
    assert categorise(tx(date(2026, 1, 1), "card payment tesco metro", "-3"), rules).category == "Groceries"


def test_rules_no_match_stays_uncategorised(tmp_path):
    from ledger.rules import categorise, load_rules
    rules = load_rules(write_rules(tmp_path, [{"match": "rent", "category": "Housing"}]))
    assert categorise(tx(date(2026, 1, 1), "Coffee", "-3"), rules).category == "Uncategorised"


def test_rules_empty_array_loads_and_leaves_uncategorised(tmp_path):
    from ledger.rules import categorise, load_rules
    rules = load_rules(write_rules(tmp_path, []))
    assert len(list(rules)) == 0
    assert categorise(tx(date(2026, 1, 1), "Coffee", "-3"), rules).category == "Uncategorised"


def test_rules_categorise_returns_new_transaction_without_mutation(tmp_path):
    from ledger.rules import categorise, load_rules
    rules = load_rules(write_rules(tmp_path, [{"match": "coffee", "category": "Cafe"}]))
    original = tx(date(2026, 1, 1), "Coffee", "-3")
    result = categorise(original, rules)
    assert result is not original
    assert isinstance(result, Transaction)
    assert result.category == "Cafe"
    assert original.category == "Uncategorised"
    assert (result.date, result.description, result.amount) == (original.date, original.description, original.amount)


def test_rules_missing_key_raises_rules_error_naming_index(tmp_path):
    from ledger.rules import RulesError, load_rules
    assert issubclass(RulesError, ValueError)
    with pytest.raises(RulesError) as exc:
        load_rules(write_rules(tmp_path, [
            {"match": "a", "category": "A"},
            {"match": "b", "category": "B"},
            {"match": "c"},
        ]))
    assert mentions(exc.value, 2)


def test_rules_non_string_value_raises_rules_error_naming_index(tmp_path):
    from ledger.rules import RulesError, load_rules
    with pytest.raises(RulesError) as exc:
        load_rules(write_rules(tmp_path, [
            {"match": "a", "category": "A"},
            {"match": 7, "category": "B"},
        ]))
    assert mentions(exc.value, 1)


# ---------------------------------------------------------------- T3 report.py

def test_summary_empty_input():
    from ledger.report import summarise
    assert summarise([]) == {"months": []}


def test_summary_expense_positive_but_category_total_negative():
    from ledger.report import summarise
    month = summarise([
        tx(date(2026, 1, 5), "Salary", "1000.00", "Income"),
        tx(date(2026, 1, 10), "Groceries", "-45.50", "Food"),
        tx(date(2026, 1, 12), "Cafe", "-4.50", "Food"),
    ])["months"][0]
    assert month["income"] == Decimal("1000.00")
    assert month["expense"] == Decimal("50.00")
    assert month["net"] == Decimal("950.00")
    food = [c for c in month["categories"] if c["category"] == "Food"][0]
    assert food["total"] == Decimal("-50.00")


def test_summary_values_are_decimal_with_two_places():
    from ledger.report import summarise
    month = summarise([tx(date(2026, 1, 5), "A", "12.5", "X"), tx(date(2026, 1, 6), "B", "-3", "Y")])["months"][0]
    for key in ("income", "expense", "net"):
        assert isinstance(month[key], Decimal)
    assert (str(month["income"]), str(month["expense"]), str(month["net"])) == ("12.50", "3.00", "9.50")


def test_summary_round_half_up_on_half_cent():
    from ledger.report import summarise
    month = summarise([tx(date(2026, 1, 5), "A", "10.005"), tx(date(2026, 1, 6), "B", "-2.005")])["months"][0]
    assert str(month["income"]) == "10.01"
    assert str(month["expense"]) == "2.01"
    assert str(month["net"]) == "8.00"


def test_summary_months_sorted_ascending_empty_months_absent():
    from ledger.report import summarise
    months = summarise([
        tx(date(2026, 3, 1), "A", "1"),
        tx(date(2025, 12, 31), "B", "1"),
        tx(date(2026, 1, 15), "C", "1"),
        tx(date(2026, 3, 9), "D", "1"),
    ])["months"]
    assert [m["month"] for m in months] == ["2025-12", "2026-01", "2026-03"]


def test_summary_categories_sorted_total_desc_then_name():
    from ledger.report import summarise
    cats = summarise([
        tx(date(2026, 1, 1), "a", "-10.00", "Beta"),
        tx(date(2026, 1, 2), "b", "-10.00", "Alpha"),
        tx(date(2026, 1, 3), "c", "5.00", "Gamma"),
        tx(date(2026, 1, 4), "d", "-20.00", "Delta"),
    ])["months"][0]["categories"]
    assert [(c["category"], c["total"]) for c in cats] == [
        ("Gamma", Decimal("5.00")),
        ("Alpha", Decimal("-10.00")),
        ("Beta", Decimal("-10.00")),
        ("Delta", Decimal("-20.00")),
    ]


def test_render_empty_summary_text():
    from ledger.report import render_text
    assert render_text({"months": []}) in ("no transactions", "no transactions\n")


TWO_MONTH = [
    tx(date(2026, 1, 5), "Salary", "1000.00", "Income"),
    tx(date(2026, 1, 10), "Groceries", "-45.50", "Food"),
    tx(date(2026, 1, 12), "Cafe", "-4.50", "Food"),
    tx(date(2026, 2, 1), "Rent", "-800.00", "Housing"),
    tx(date(2026, 2, 3), "Refund", "20.00", "Uncategorised"),
]

TWO_MONTH_TEXT = (
    "== 2026-01 ==\n"
    "income  1000.00\n"
    "expense 50.00\n"
    "net     950.00\n"
    "  Income: 1000.00\n"
    "  Food: -50.00\n"
    "\n"
    "== 2026-02 ==\n"
    "income  20.00\n"
    "expense 800.00\n"
    "net     -780.00\n"
    "  Uncategorised: 20.00\n"
    "  Housing: -800.00"
)


def test_render_exact_two_month_sample():
    from ledger.report import render_text, summarise
    out = render_text(summarise(TWO_MONTH))
    assert out in (TWO_MONTH_TEXT, TWO_MONTH_TEXT + "\n")


# ---------------------------------------------------------------- T4 cli.py

CLI_CSV = HEADER + (
    "2026-01-05,Salary,1000.00\n"
    "2026-01-10,Groceries,-45.50\n"
    "2026-01-12,Cafe Groceries,-4.50\n"
    "2026-02-01,Rent,(800.00)\n"
    "2026-02-03,Refund,20.00\n"
)
CLI_RULES = [
    {"match": "salary", "category": "Income"},
    {"match": "groceries", "category": "Food"},
    {"match": "rent", "category": "Housing"},
]


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "ledger.cli", *map(str, args)],
                          cwd=WORK, capture_output=True, text=True, encoding="utf-8", timeout=60)


def cli_files(tmp_path):
    return write_csv(tmp_path, CLI_CSV), write_rules(tmp_path, CLI_RULES)


def test_cli_text_output_exit_0(tmp_path):
    csv_path, rules_path = cli_files(tmp_path)
    r = run_cli("summarize", csv_path, "--rules", rules_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip("\n") == TWO_MONTH_TEXT


def test_cli_json_renders_decimals_as_strings(tmp_path):
    csv_path, rules_path = cli_files(tmp_path)
    r = run_cli("summarize", csv_path, "--rules", rules_path, "--json")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    jan, feb = data["months"]
    assert (jan["month"], jan["income"], jan["expense"], jan["net"]) == ("2026-01", "1000.00", "50.00", "950.00")
    assert feb["net"] == "-780.00"
    assert jan["categories"] == [{"category": "Income", "total": "1000.00"}, {"category": "Food", "total": "-50.00"}]


def test_cli_missing_arguments_exit_2_usage(tmp_path):
    csv_path, _ = cli_files(tmp_path)
    for args in ((), ("summarize", csv_path)):
        r = run_cli(*args)
        assert r.returncode == 2, args
        assert r.stderr.lstrip().startswith("usage:"), r.stderr


def test_cli_parse_error_exit_1(tmp_path):
    csv_path = write_csv(tmp_path, HEADER + "2026-01-05,Shop,-1.00\nnot-a-date,Bad,-2.00\n")
    rules_path = write_rules(tmp_path, CLI_RULES)
    r = run_cli("summarize", csv_path, "--rules", rules_path)
    assert r.returncode == 1
    assert r.stderr.lstrip().startswith("error:"), r.stderr
    assert mentions(r.stderr, 3)


def test_cli_rules_error_exit_1(tmp_path):
    csv_path = write_csv(tmp_path, CLI_CSV)
    rules_path = write_rules(tmp_path, [{"match": "a", "category": "A"}, {"category": "B"}])
    r = run_cli("summarize", csv_path, "--rules", rules_path)
    assert r.returncode == 1
    assert r.stderr.lstrip().startswith("error:"), r.stderr
    assert mentions(r.stderr, 1)


def test_cli_missing_csv_file_exit_1_names_path(tmp_path):
    rules_path = write_rules(tmp_path, CLI_RULES)
    r = run_cli("summarize", tmp_path / "nope-missing.csv", "--rules", rules_path)
    assert r.returncode == 1
    assert r.stderr.lstrip().startswith("error:"), r.stderr
    assert "nope-missing.csv" in r.stderr


def test_cli_missing_rules_file_exit_1_names_path(tmp_path):
    csv_path = write_csv(tmp_path, CLI_CSV)
    r = run_cli("summarize", csv_path, "--rules", tmp_path / "absent-rules.json")
    assert r.returncode == 1
    assert r.stderr.lstrip().startswith("error:"), r.stderr
    assert "absent-rules.json" in r.stderr
