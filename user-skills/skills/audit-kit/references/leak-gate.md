# Leak gate

Runs before any push to a public or shared repo, mirror or gist. A hit blocks
the push until the source is fixed. The gate is never bypassed; a true false
positive goes on a written allowlist with its reason.

## Steps

1. **Write the denylist** to a file kept OUTSIDE the repo being published
   (the list itself names the people and clients it protects): client and
   company names, colleagues' and clients' names, personal and work email
   addresses, account logins, private repo names, internal hostnames.
2. **Run the scanner** from this skill's folder:
   `python scripts/leak_scan.py <repo> --deny <denylist-file> [--allow <allowlist-file>] [--skip DIR]`.
   It walks every file except `.git` (`node_modules` and caches included; binary files (NUL bytes) and links to folders are listed, not scanned)
   and flags denylist terms (in file paths too), email addresses, absolute
   home paths (`C:\Users\<name>`, `/Users/<name>`, `/home/<name>`), and
   common secret formats. `--skip DIR` (repeatable) is for explicit
   exclusions; every skip is printed. Exit 0 = PASS, exit 1 = hits printed as
   `file:line`, secret values masked, exit 2 = usage error, exit 3 =
   INCOMPLETE (files or folders it could not read, listed). INCOMPLETE
   blocks the push like a hit: fix access to what it lists, or scan again,
   until the result is PASS.
3. **Fix every hit at its source**, re-run until PASS. For a generated
   export, fix the generator or its scrub table, not the output, or the next
   export brings the hit back.
4. **Check the history, not just the tree.** A repo whose earlier commits
   held a leak still leaks: scan `git log -p` too (`git log -p | python
   scripts/leak_scan.py - --deny ... [--allow ...]`). In this mode the scanner
   takes file names from the `git log -p` diff headers, so file-scoped
   allowlist entries apply here too. A leak in history means rewriting it
   (one clean commit or a filter tool), with a bundle backup of the old
   history first (`git bundle create <backup>.bundle --all`) - that is a
   force-push, so it needs the user's explicit yes.
5. **Commit identity.** Check `git config user.name` / `user.email` in the
   repo before committing: a global work identity on a personal public repo
   is itself a leak. Use the account's noreply address
   (`<id>+<login>@users.noreply.github.com`) for public commits.
6. **Push.** GitHub push protection may still block a key-shaped test
   fixture; replace it with an obviously fake value rather than bypassing.

## Allowlist format

One entry per line, tab-separated: `relative/path<TAB>exact snippet<TAB>reason`.
The scanner reports unused entries so stale ones can be pruned.
