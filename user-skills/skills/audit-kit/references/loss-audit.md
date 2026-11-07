# Loss audit

Proves a fix pass that moved, trimmed or deleted content lost nothing the
user would miss. Runs after every such pass, before it is reported done.

## Steps

1. **Back up sources AND destinations before the pass.** Zip or copy every
   file the pass edits and every file content moves into (status files,
   logs, the linked memory file). Without the destination backup,
   "append-only" cannot be proven afterwards. A file that is committed and
   clean in git (`git status --porcelain <path>` prints nothing) can rely on
   its history as the backup: note `git rev-parse HEAD` before the pass, and
   `git show <that commit>:<path>` recovers it. A file that is uncommitted or
   untracked gets a real copy.
2. **List candidate losses.** Diff each backup against the current file and
   list every removed fact: names, numbers, dates, paths, rules, decisions.
3. **Judge each candidate by meaning.** For each, search the destination and
   the rest of the same file for the fact in any wording, then read the
   surrounding paragraph. String search alone is mostly noise: in one past
   audit 29 of 31 flagged candidates were false positives - the fact
   survived reworded (a rounded figure had become the exact one, a
   `DO-NOT-MODIFY` tag had become "Do not modify"). Done when every
   candidate is marked PRESERVED (quote where), DROPPED ON PURPOSE (stale,
   wrong, or approved for deletion), or LOST.
4. **Restore every LOST fact** from the backup to its rightful home, then
   re-run step 3 for it.
5. **Report** PASS (nothing lost), PASS WITH NOTES (dropped on purpose,
   listed), or FAIL (lost and not restored, listed).

A reviewer reporting a loss gets the same step 3 before anything is changed:
read the destination paragraph first; acting on a string-search miss adds a
duplicate that then has to be removed.
