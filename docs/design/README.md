# Design system reference

The Stage 6 prototype uses the **Buruh Hybrid** design system
(https://claude.ai/artifact/QfaXT1CBxeh4uEySAYN9ge, owner: project owner).

- Access confirmed 2026-11-04: the README, `tokens.json`, and index were read through the Artifact tool.
- `buruh-hybrid-tokens.snapshot-2026-11-04.json` is a verbatim copy of `project/tokens.json`
  at version 1793027917-db48, kept so the prototype is reproducible. The live system wins
  if they differ; re-read it at the start of Stage 6.
- Key constraints for a transit prototype:
  - Square corners (`radius-none`).
  - Archivo plus IBM Plex Mono (Google Fonts).
  - `orange` is a fill only, never text on paper.
  - Use `accent-text` for orange text.
  - Light and dark themes.
  - Focus ring tokens.
- Gap for Stage 6: the system has no map, chart, or status-label palette. Stage 6 must
  extend it, for example by mapping the four status labels (existing, official, inferred,
  concept) to tokens that differ in lightness and line pattern, not hue alone. Any
  extension needs the owner's approval.
