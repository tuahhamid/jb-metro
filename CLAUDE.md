# Instructions for Claude sessions in this repo

## Commit author (owner preference, set 2026-11-04; applies to every session)

Commits must be authored as the repo owner, not as Claude. Before the first commit
in a session, run:

```bash
git config user.name "Tuah Hamid"
git config user.email "88237170+tuahhamid@users.noreply.github.com"
```

- Use only this GitHub no-reply address. Never use the owner's personal email in
  commits: this repo is public, and commit emails are visible to anyone.
- Keep crediting Claude with the `Co-Authored-By:` trailer at the end of each
  commit message, as the session's attribution instructions require.
- Do not rewrite or force-push earlier commits to change their author. Older commits
  stay authored as Claude, and docs and results reference their hashes.
- Commits made by GitHub Actions stay authored as `github-actions[bot]`.

## Project context

- Governing brief: `docs/project-brief.md`.
- Current state and next scope: the latest file in `docs/handoffs/`.
- Work in stages. Stop after each stage for the owner's review.
- The repo is public. Never commit keys, tokens, or `.env` files. Re-run the scan in
  `docs/security-review.md` before each handoff.
