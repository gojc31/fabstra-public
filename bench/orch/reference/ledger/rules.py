import json
from dataclasses import dataclass, replace

from ledger.models import Transaction


class RulesError(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    match: str
    category: str


def load_rules(path) -> list[Rule]:
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise RulesError("rules file must be a JSON array")
    rules = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise RulesError(f"rule {i}: not an object")
        for key in ("match", "category"):
            if key not in item:
                raise RulesError(f"rule {i}: missing {key!r}")
            if not isinstance(item[key], str):
                raise RulesError(f"rule {i}: {key!r} must be a string")
        rules.append(Rule(item["match"], item["category"]))
    return rules


def categorise(tx: Transaction, rules) -> Transaction:
    desc = tx.description.lower()
    for rule in rules:
        if rule.match.lower() in desc:
            return replace(tx, category=rule.category)
    return replace(tx, category="Uncategorised")
