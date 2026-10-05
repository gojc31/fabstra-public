# Ledger: monthly summary CLI

Hi team - we export CSVs from a few different banks every month and want a small
command-line tool that reads one export, tags each transaction with a category from
a rules file, and prints a monthly summary. The skeleton is already in this repo:
`ledger/models.py` (the `Transaction` dataclass) is finished; `parse.py`, `rules.py`,
`report.py` and `cli.py` are stubs. Python 3.12, standard library only (pytest is
fine for tests). Please keep the function names and signatures below exactly as
written, because other scripts of ours import them.

There are four tasks. They build on each other in this order.

## T1 - parse.py: `parse_csv(path) -> list[Transaction]`

`path` is a `str` or a `pathlib.Path`.

- The CSV has a header row. Find the columns by header name, case-insensitive:
  `date`, `description`, `amount` (ignore spaces around a header name). Any extra
  columns are ignored. The column order may vary between banks.
- A UTF-8 BOM at the start of the file must be tolerated.
- Blank lines are skipped.
- Dates accept `YYYY-MM-DD` and `DD/MM/YYYY` (day first, so `03/04/2026` is 3 April
  2026). Any other format raises `ParseError`. Define `ParseError` in `parse.py` as a
  subclass of `ValueError`. Its message must contain the 1-based line number of the
  offending row in the file (line 1 is the header).
- Amounts: an optional leading currency symbol `$` or `£`; thousands separators
  (commas) are allowed, e.g. `$1,234.50`; `(45.00)` means negative 45.00; a leading
  `-` also means negative (`-45.00`). Parse to `Decimal`, never `float`. An amount
  that cannot be parsed raises `ParseError` with the line number, as for dates.
- The description is stripped of surrounding whitespace, and any run of internal
  whitespace collapses to one space (`"  Corner   Shop "` becomes `"Corner Shop"`).
- Duplicate rows - same date, same normalised description, same amount - keep the
  first occurrence and drop the rest.
- Rows are returned in file order (after de-duplication).

## T2 - rules.py: `load_rules(path) -> list[Rule]` and `categorise(tx, rules) -> Transaction`

`Rule` is whatever type you choose; callers only pass the list from `load_rules`
straight into `categorise`.

- The rules file is a JSON array of objects `{"match": "<substring>", "category": "<name>"}`.
  The array may be empty (`[]`), in which case nothing gets categorised.
- Matching is a case-insensitive substring test on the transaction description.
  The FIRST matching rule wins (file order). No match: the category stays
  `"Uncategorised"`.
- `categorise` returns a NEW `Transaction` (the dataclass is frozen) with the
  category set. It never mutates its input.
- A rule that is missing `match` or `category`, or whose value for either is not a
  string, raises `RulesError` (define it in `rules.py`, subclass of `ValueError`).
  The message names the rule's 0-based index in the array.

## T3 - report.py: `summarise(txs) -> dict` and `render_text(summary) -> str`

- `summarise` returns
  `{"months": [ {"month": "YYYY-MM", "income": Decimal, "expense": Decimal, "net": Decimal, "categories": [ {"category": str, "total": Decimal}, ... ]}, ... ]}`.
- `income` is the sum of the positive amounts; `expense` is the sum of the negative
  amounts expressed as a POSITIVE number; `net` = income - expense. All of these (and
  each category `total`) are `Decimal`, quantised to 2 places with `ROUND_HALF_UP`
  (so `10.005` becomes `10.01`).
- Months are sorted ascending. A month with no transactions does not appear.
- Within a month, categories are sorted by total descending, then by name ascending
  on a tie. A category's `total` is the signed sum of its amounts, so an expense
  category has a negative total.
- Empty input returns `{"months": []}`.
- `render_text` prints one block per month:

  ```
  == 2026-01 ==
  income  1000.00
  expense 50.00
  net     950.00
    Income: 1000.00
    Food: -50.00
  ```

  That is: a header line `== YYYY-MM ==`, then `income  <amount>`, `expense <amount>`,
  `net     <amount>` (labels padded to the same width exactly as shown), then one line
  per category `  <category>: <signed total>` (two leading spaces) in the summary's
  order. Amounts use two decimals, no currency symbol and no thousands separator;
  negative numbers carry a leading `-`, positive ones have no sign. Blocks are
  separated by exactly one blank line, and there is no trailing blank line (the
  returned string does not end with a newline). An empty summary renders exactly
  `no transactions`.

## T4 - cli.py: `main(argv=None) -> int`

- Usage: `python -m ledger.cli summarize <csv> --rules <rules.json> [--json]`.
  It parses the CSV, categorises every transaction with the rules, summarises, and
  prints. (You may add `ledger/__main__.py` so `python -m ledger` also works; not
  required.)
- `--json` prints `json.dumps(summary, indent=2)` with every Decimal rendered as a
  string (e.g. `"12.50"`). Without `--json` it prints `render_text(summary)`.
- Exit codes: `0` on success; `2` for wrong or missing arguments (message to stderr
  starting with `usage:`); `1` for a `ParseError` or `RulesError` (message to stderr
  starting with `error:` and containing the original error message).
- A missing CSV file or rules file exits `1` with a stderr message starting with
  `error:` that includes the path that was not found.

## Acceptance

Done means `python -m pytest -q` passes in the repo and every behaviour above holds;
the reviewers grade against these rules.
