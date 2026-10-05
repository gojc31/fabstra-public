# The repo copies of these skills carry an unsubstituted skills-dir placeholder,
# and two of them ship a tests/test_guard.py next to a guard.py, which collide
# in one pytest run. Run their tests in the installed copies (see SETUP.md,
# scripts/install-user-skills.*), not from this repo.
collect_ignore_glob = ["skills/*"]
