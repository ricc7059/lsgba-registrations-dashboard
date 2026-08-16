# LSGBA Registrations Dashboard

Aggregate view of open LSGBA registrations, published at
https://ricc7059.github.io/lsgba-registrations-dashboard/

Rebuilt by the `/lsgba-registration-dashboard` Claude Code skill, which checks
each Enabled registration in SportsEngine and re-exports only the ones whose
entry count has moved.

**This repo is public and contains aggregate counts only.** Raw Quick Report
exports stay in `~/Downloads` and are blocked by `.gitignore`. A fail-closed
scan runs before every push.

Tests: `python3 -m unittest discover tests`

## The installed skill is a symlink

`~/.claude/skills/lsgba-registration-dashboard/SKILL.md` is a **symlink** to
`skill/SKILL.md` in this repo, so editing the repo copy updates the skill Claude
Code actually loads. Moving, renaming, or deleting this repo breaks the
installed skill; re-create the symlink if you relocate the checkout.
