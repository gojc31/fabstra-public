from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_CENT, rounding=ROUND_HALF_UP)


def summarise(txs) -> dict:
    by_month = defaultdict(list)
    for tx in txs:
        by_month[tx.date.strftime("%Y-%m")].append(tx)
    months = []
    for month in sorted(by_month):
        items = by_month[month]
        income = _q(sum((t.amount for t in items if t.amount > 0), Decimal(0)))
        expense = _q(-sum((t.amount for t in items if t.amount < 0), Decimal(0)))
        cats = defaultdict(lambda: Decimal(0))
        for t in items:
            cats[t.category] += t.amount
        categories = [{"category": c, "total": _q(v)} for c, v in cats.items()]
        categories.sort(key=lambda c: (-c["total"], c["category"]))
        months.append({
            "month": month,
            "income": income,
            "expense": expense,
            "net": _q(income - expense),
            "categories": categories,
        })
    return {"months": months}


def render_text(summary) -> str:
    months = summary.get("months") or []
    if not months:
        return "no transactions"
    blocks = []
    for m in months:
        lines = [
            f"== {m['month']} ==",
            f"income  {m['income']:.2f}",
            f"expense {m['expense']:.2f}",
            f"net     {m['net']:.2f}",
        ]
        lines += [f"  {c['category']}: {c['total']:.2f}" for c in m["categories"]]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
