# FabStra batch gate - many ready PRs in one repo

Reached from: phases.md Phase 4, "Batch gate", when 3 or more reviewed PRs or branches in one repo are waiting on JC's merge go at the same time. Below 3, each PR ships on its own through Phase 4.

A **batch** tests several ready PRs together on one local merge, so the gate runs once and production gets one push instead of one per PR. Every push and every merge into a real branch still needs JC's go (phases.md, Orchestrator rule 8). The batch only changes what that go covers.

## Steps

1. **Fresh base.** `git fetch`, then record the base SHA (`origin/<main branch>`) in RUN.md. A PR whose head does not contain that base leaves the batch and gets a fix delegation to merge the base. The gate must be local and isolated, as the smoke gate is (phases.md, Phase 2). A suite that reaches live services needs JC's go first, and so do its base runs.
2. **Held heads out.** Check every candidate against everything held (phases.md Phase 4, "Held heads": ancestry and files). A candidate that carries held work leaves the batch. A PR dropped later in this batch (steps 4 and 6) counts as held from then on, so a stacked head cannot bring it back in. A PR in an excluded category (money, auth, PII, permissions, migration, concurrency, a client-facing release) never joins a batch. It ships alone, on its own go.
3. **Freeze.** Write the batch list (PR, head SHA, order) in RUN.md. Nothing joins after this point. A PR that becomes ready later waits for the next batch.
4. **Merge train in a scratch worktree.** If `<scratch>/train` exists from an earlier round, remove it with `git worktree remove --force <scratch>/train`. Then `git worktree add --detach <scratch>/train <base SHA>` (client repos: the client's worktree folder, per CLAUDE.md). There, merge each frozen head SHA in order with `git merge --no-ff --no-edit <head SHA>`. A conflict aborts that merge only (`git merge --abort`), and the rest of the train continues:
   - If the PR merges cleanly on the base alone (`git merge-tree --write-tree <base SHA> <head SHA>` exits 0), it conflicts with an earlier PR in the train. It waits for the next batch, with no fix delegation.
   - Otherwise it gets a fix delegation to resolve against the base.

   The train is not pushed before step 8's go.
5. **Gate once.** In the train worktree, run the project's full gate through heavy.py (fanout.md). Add the tests of every caller of a shared function a PR changed (auth, billing, permissions, a shared helper: `rg` the name), and apply "Check what ran" (phases.md, Phase 2).
6. **Verdict per PR.** Place each red test with "Whose failure is it?" (phases.md, Phase 2), with the batch base as the base. When leaving one PR out of the train clears the failure, that PR drops and gets a fix delegation. Rebuild the train without it (step 4) and gate again. A failure that no single drop clears (two PRs that break only together) goes to JC with the PRs named. Re-runs, base checks and drops are not fix attempts. Fix delegations count toward the usual ceilings (the miss ladder, the review cap).
7. **Ask once.** One AskUserQuestion, listing:
   - the base SHA and the train head SHA
   - each PR's head SHA
   - the gate's `tree=` id and counts
   - every dropped PR, with its reason
   - how it will ship (step 8)

   JC's go covers exactly those heads on that base.
8. **Ship exactly what was tested.** On the go, `git fetch` again. If the base or any PR head moved from the frozen SHAs, the go is void: return to step 1. Otherwise push the train head with a plain push (`git push origin <train head SHA>:<main branch>`, never force). Git refuses it if the base moved in between, and the result is the tree the gate tested. The PRs then show as merged. If the project must merge through its host (a merge queue, squash merges, required checks), the ask names that path, and it is used only when it tests its own result before merging. Read the remote back to confirm, then remove the train worktree.

If a step fails, or the ship stops partway, `git fetch` and return to step 1 with the PRs that are left. A PR that drops twice goes to JC. When fewer than 3 PRs are left, each ships on its own through Phase 4.
