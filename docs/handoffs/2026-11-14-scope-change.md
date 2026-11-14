# Decision: scope change to the JB Metro Explorer

**Date:** 2026-11-14
**Decided by:** the owner, in a brainstorming session with Claude
**Design:** `docs/superpowers/specs/2026-11-14-jb-metro-explorer-design.md`

The brief (`docs/project-brief.md`) is not edited. Per its rules, scope changes are recorded here.

## Decisions

| # | Decision | Owner's words / basis |
|---|---|---|
| 1 | The goal is now an interactive storytelling explorer (map + 3D) in the style of the Sydney Metro West site, not an evidence-first access study. | "get to the 3D models that mimic the Sydney Metro West as fast as possible"; "dont care much about engineering certainty, focus more on bridging tech, story-telling via interactive map and 3D models" |
| 2 | Stages 3–5 are **paused**, not dropped. The Stage 3 scope in `stage-2.md` stays valid if the study resumes. | Owner picked "pause" |
| 3 | Lines: JB E-ART first, then Mutiara Line (Penang) and MRT3 Circle Line (Klang Valley). | Owner named all three; JB first |
| 4 | Copy the Sydney Metro West *flow* (intro → tour → 3D places), not its brand. No renders. | "yes copy flow"; "no renders, you can be creative" |
| 5 | Lines must be track-like: 150 m minimum curve radius (100 m flagged exception), 160 m straight at each station. | Owner approved "option 1 and these numbers" |
| 6 | Tebrau drops the Desa Tebrau detour (Stage 2 T1 stations 14–15) and runs straight on Federal Route 3 to Ulu Tiram. | "just go straight, find possible stations until we terminate at Ulu Tiram" |
| 7 | Photos from Wikimedia Commons with credit; our own 3D snapshots as fallback. | "follow your suggestions" |
| 8 | Stage 2 handoff decision 5 (vehicle-position collector) is closed: the collector's schedule is turned off, because it only fed the paused validation work. | Follows from decision 2 *(Claude's proposal in the session)* |

## What stays true

- All JB E-ART geometry is still `concept`. No official alignment has been published.
- The Stage 2 record (`data/concept/`, `results/stage2/`) is not overwritten. Explorer geometry is kept separately.
- $0, web-only, public repo, no keys, Buruh Hybrid design system.
