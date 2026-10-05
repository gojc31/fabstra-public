import csv
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from ledger.models import Transaction

_AMOUNT = re.compile(r"^(-)?\s*([$£])?\s*(\()?\s*([0-9][0-9,]*(?:\.[0-9]+)?|\.[0-9]+)\s*(\))?$")


class ParseError(ValueError):
    pass


def _parse_date(text: str, line: int) -> date:
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}" if fmt == "%Y-%m-%d" else r"\d{2}/\d{2}/\d{4}", text):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                break
    raise ParseError(f"line {line}: bad date {text!r}")


def _parse_amount(text: str, line: int) -> Decimal:
    m = _AMOUNT.match(text.strip())
    if not m or bool(m.group(3)) != bool(m.group(5)) or (m.group(1) and m.group(3)):
        raise ParseError(f"line {line}: bad amount {text!r}")
    try:
        value = Decimal(m.group(4).replace(",", ""))
    except InvalidOperation:
        raise ParseError(f"line {line}: bad amount {text!r}") from None
    return -value if (m.group(1) or m.group(3)) else value


def parse_csv(path) -> list[Transaction]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return []
        names = [h.strip().lower() for h in header]
        try:
            idx = {k: names.index(k) for k in ("date", "description", "amount")}
        except ValueError as e:
            raise ParseError(f"line 1: missing column ({e})") from None
        out, seen = [], set()
        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue
            line = reader.line_num
            try:
                d_raw, desc_raw, amt_raw = (row[idx[k]] for k in ("date", "description", "amount"))
            except IndexError:
                raise ParseError(f"line {line}: too few columns") from None
            tx = Transaction(
                _parse_date(d_raw, line),
                " ".join(desc_raw.split()),
                _parse_amount(amt_raw, line),
            )
            key = (tx.date, tx.description, tx.amount)
            if key in seen:
                continue
            seen.add(key)
            out.append(tx)
        return out
