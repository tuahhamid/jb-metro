# Pre-publication security review

**Purpose:** check the repo before the owner makes it public and enables GitHub Pages
(owner decision, 2026-11-04).

**Reviewed:** commit `f91eeba` plus the changes in this commit. Every file version in all
7 commits of the full git history was scanned, not just the latest tree.

## Method (reproducible)

1. Exported each commit with `git archive`.
2. Scanned the exports with `detect-secrets 1.5.0` (`detect-secrets scan --all-files`).
3. Ran regex searches for:
   - GitHub tokens (`ghp_`, `gho_`, `ghs_`, `github_pat_`)
   - Anthropic and OpenAI-style keys
   - AWS keys (`AKIA…`), Google API keys (`AIza…`)
   - Mapbox tokens (`pk.eyJ`, `sk.eyJ`), Slack tokens
   - Private key blocks
   - `password=`, `secret=`, `api_key=`, `token=`, `Authorization:`, `Bearer`
4. Searched for email addresses, private IP ranges, local filesystem paths, and proxy settings.
5. Listed commit author and committer identities and all commit-message lines.
6. Reviewed both workflows for injection, permissions, and trigger risks.

## Findings

| # | Finding | Severity | Action |
|---|---|---|---|
| 1 | No credentials, API keys, tokens, or private keys in any file version | – | None |
| 2 | 16 detect-secrets "Hex High Entropy String" hits | False positive | They are SHA-256 checksums of downloaded files and a git commit SHA, used for provenance |
| 3 | API endpoints in code (`api.data.gov.my/...`) | None | Public, unauthenticated government open-data endpoints. No key exists to leak. |
| 4 | Workflows use only the built-in, short-lived `GITHUB_TOKEN`. No repository secrets are defined or referenced. | – | None |
| 5 | Commit identities are only `Claude <noreply@anthropic.com>` and `github-actions[bot]` | – | No personal email exposed |
| 6 | Commit messages contain a `Claude-Session:` link | Low (informational) | The link opens only for the owner's signed-in account; it is not a credential. Removing it would require rewriting history and force-pushing. Owner's choice; not recommended. |
| 7 | `vehicle_id` in vehicle-position data is the bus registration number | Low | Already published by the government feed and painted on public buses. No passenger or driver data. Kept as-is. |
| 8 | A workflow input was interpolated directly into a shell line (`refresh_osm`) | Low (boolean; only users with write access can dispatch) | **Fixed:** passed through `env:` instead |
| 9 | Third-party actions referenced by mutable tags (`@v4`) | Medium for public repos | **Fixed:** pinned to full commit SHAs with the version in a comment |
| 10 | `docs/design/` holds a snapshot of the owner's Buruh Hybrid design tokens; `docs/project-brief.md` includes the design-system artifact URL | Informational | Colors and type settings become public; the artifact itself stays private. **Owner confirmed 2026-11-04: acceptable.** |
| 11 | Data licenses | Compliance | OSM extract is ODbL (attribution + share-alike), data.gov.my is open data, news is metadata only. **Added** `data/LICENSES.md`. |

## Settings for the owner after switching to public

**Status 2026-11-04:** the repo is public. The owner reports applying settings 1–4. Optional #5 was not applied (owner decision).

All free for public repos. GitHub → repo **Settings**:

1. **Code security → Secret scanning: Enable**, and **Push protection: Enable**.
   This blocks future commits that contain a token.
2. **Code security → Dependabot alerts: Enable.**
3. **Actions → General:**
   - Set "Fork pull request workflows from outside collaborators" to *Require approval for all outside collaborators*.
   - Keep "Workflow permissions" at *Read repository contents* as the default. Our workflows request `contents: write` explicitly.
4. **Pages:** Source = *GitHub Actions* (a Stage 6 deploy workflow will be added). Nothing outside the built site gets served.
5. **Optional:** add a ruleset on `main` blocking force-pushes and deletion. **Owner decision 2026-11-04: not applied.** Accepted risk: anyone with write access can force-push. Write access is the owner only.

## Rules for later stages (keep the repo safe to stay public)

- The Stage 6 prototype must not use API keys. Use MapLibre GL JS with key-less tiles. If any service ever needs a key, it stays out of the repo and out of client code.
- Never commit `.env` files. Never add repository secrets without recording why in a handoff note.
- Re-run this scan before each stage handoff. The commands are under Method above.
- Scheduled workflows in public repos are paused by GitHub after 60 days without repository activity. Check `vp-collector` is still running if the project goes quiet.

## Re-scan before the Stage 2 handoff (2026-11-04)

**Scope:** every commit from `94af394` (Stage 1 handoff) to `bd46c24`, plus the working tree with the Stage 2 docs. Same method as above.

| Check | Result |
|---|---|
| detect-secrets 1.5.0 | Only "Hex High Entropy String" hits. All are SHA-256 file hashes in `data/manifests/*.json` or commit SHAs in `run_metadata.json` (false positives, as in finding 2). |
| Token and key regexes | No matches |
| Email addresses | Only `88237170+tuahhamid@users.noreply.github.com` (owner no-reply, per CLAUDE.md) and `noreply@anthropic.com` (Co-Authored-By trailer). No personal email. |
| Private IPs, local paths, `.env` files | None |
| Commit identities | Owner no-reply (5 commits); `github-actions[bot]` (3 commits) |
| New workflow `stage2-alignments.yml` | Actions pinned to the same commit SHAs as Stage 1. The `refresh_osm` input is passed via `env:`. Uses only `GITHUB_TOKEN` with `contents: write`, and no secrets. Push trigger covers `main` and `claude/**`; only users with write access can push. |
| Third-party data | DEM and JRC rasters are not committed (license and size); attribution is in `data/LICENSES.md`. Plan-list extract is matched status lines only. |
