# Evidence audit (Stage 1)

**As of:** 2026-11-04.

**Evidence limit:** This Claude session's network policy blocks every Malaysian and
Singaporean news and government host. In-session evidence therefore comes from
web-search result snippets, not from reading the pages. The source register marks
this as `access_method = search-snippet`, and no such source is rated above
*medium* confidence. The `stage1-pipeline` GitHub Actions workflow probes each
register URL and records whether the claimed figures appear on the live page
(`data/manifests/source-probe.csv`). Confidence is upgraded only from that probe or
from a direct read.

Status labels follow the project rule: **existing**, **official**, **inferred**,
**concept**.

## 1. Known (with status)

| Item | Value | Status | Sources |
|---|---|---|---|
| RTS Link opening | Target **February 2027**, moved from January 2027 on 2026-10-02 for safety certification and approvals. Exact date and fares not announced. | official (target) | SRC-006 |
| RTS capacity | 10,000 passengers per hour per direction (pphpd) | official | SRC-003, SRC-004, SRC-017 |
| RTS opening ridership forecast | ~40,000 per day | official | SRC-003 |
| RTS border model | Co-located CIQ, cleared once at the departure station | official | SRC-004, SRC-022 |
| Bukit Chagar role | Main interchange between RTS and E-ART | official | SRC-017, SRC-009 |
| E-ART is the official system | Government agreed to implement it as JB's main congestion solution (Budget 2027, 2026-10-09). Federal funding confirmed in principle (2026-07). Cost ~RM10b. | official | SRC-013, SRC-014 |
| E-ART corridors named | Skudai, Tebrau, Iskandar Puteri | official | SRC-014, SRC-037 |
| E-ART reported lengths | Tebrau 14 km, Iskandar Puteri 14.78 km, Skudai 18.8 km | official (reported) | SRC-021 |
| Jurisdiction | E-ART is under Malaysian authority. Singapore coordinates on dispersal only. | official | SRC-017 |
| Woodlands Checkpoint volume | 327,000 travelers/day in 2024, up from 269,000 in 2023 | existing | SRC-012 |
| Open transit data | data.gov.my GTFS static (`mybas-johor`, `ktmb`) and myBAS vehicle positions | existing | SRC-001, SRC-002 |

## 2. Unknown (blocks or limits later stages)

| Unknown | Effect | Plan |
|---|---|---|
| **E-ART alignments and station locations**, unpublished | Every Stage 2 line and station is a **concept** | Hypotheses constrained by reported lengths, OSM road reserves, and interchange access. Labeled concept everywhere. |
| E-ART vehicle spec and capacity | Capacity spans 3,000–10,000+ pphpd | Low/base/high (A-012) |
| E-ART opening year | Letter of acceptance not confirmed. "4 years after deal" implies ~2030 at the earliest. | B and C are future-network concepts on 2027 land use (A-015, A-016) |
| RTS hours, headway, and fares | Affects off-peak access and demand | Reported values marked inferred (A-005–A-007) |
| Bukit Chagar internal layout: gate count, vertical circulation, exit widths | Stage 4 depends on it | Site check SC-1. Seek official station and ICQ documents. |
| RSNJ 2030 / RTJB 2035 gazette status and transit content | Land-use and road-reserve context | Read SRC-026 via the Actions probe. Search the PLANMalaysia@Johor portal. |
| Small-area population | DOSM public geography found so far is parliament/state seat level | Stage 3: disaggregation method decision (A-025) |
| Freshness of the myBAS GTFS | MobilityData lists service through 2026-09-20 (SRC-030), so the feed may be expired | Checked by test S0 in the workflow |
| Cross-border and private bus GTFS (e.g., Causeway Link) | Baseline likely under-counts bus service | SC-3. Report as a limitation. |
| Road traffic counts (RTVM) | Needed to test the 75% claim | RTVM is a **paid** publication. Not acquired (see decisions). |

## 3. Conflicting

| Topic | Conflict | Handling |
|---|---|---|
| RTS opening | January 2027 (minister, April–August 2026) vs. December 2026 (older reports) vs. **February 2027** (joint statement, 2026-10-02) | Use February 2027 as the latest official target. Re-check monthly. |
| RTS ridership | 40,000/day vs. 35% × 350,000 = 122,500/day | **Bounded**, see §4 |
| E-ART capacity | 3,000–5,000 (typical ART; expert); ~4,800 (240 pax × 20 trains/h); 5,000–12,000 (explainer, car-count dependent); 10,000 "design" (press) | Low 3,000 / base 5,000 / high 10,000 (A-012). 12,000 excluded until a vehicle spec exists. |
| E-ART station count | 32 vs. 35 vs. 39 (one source: 19 Tebrau, 13 Skudai, 7 Iskandar Puteri) | Not used as an input. Stage 2 derives spacing from access logic. |
| E-ART status | "approved" (May 2026 reports), "approval in principle" (company), "terms under negotiation" (July 2026), "government agreed to implement" (Budget, October 2026) | Status = official commitment. No signed concession or alignment confirmed. |
| Tebrau priority | Official: Tebrau first, "75% of vehicles". Experts (2026-10-30): Skudai–Tampoi–Larkin **and** Tebrau–Pandan, with Iskandar Puteri **not** named. | The 75% figure is a claim to test (V10). Scope question raised for the owner. |
| "LRT" vs. E-ART | Concept maps and enthusiasts call it LRT | Use "E-ART" for the official system. Use "LRT-style concept" only for our hypotheses. |

## 4. RTS ridership conflict: bounded

Reproducible with `python pipeline/analysis/rts_ridership_bounds.py` (output:
`results/stage1/rts_ridership_bounds.json`). This is arithmetic on stated inputs, not a forecast.

1. **They are different quantities.** 40,000/day is MRT Corp's opening-period
   forecast. 122,500/day is a 2022 statement of the share of pre-pandemic Causeway
   travelers the line could absorb. The 350,000 base was pre-pandemic; Woodlands
   averaged 327,000/day in 2024. The two figures are 12% and 37% of 2024
   Woodlands volume, respectively.
2. **Capacity check.** 10,000 pphpd matches the reported 3.6-minute headway × ~600
   passengers per train (16.7 trains/h × 600 = 10,000).
3. **Peaking check.** Assume the peak-direction peak hour is 5% / 6.5% / 10% of two-way
   daily ridership (A-010, inferred: tidal cross-border commuting).
   - 40,000/day loads the peak direction at 2,000 / 2,600 / 4,000 pphpd, or **20–40% of capacity**.
   - 122,500/day loads it at 6,125 / 7,963 / 12,250 pphpd, or **61–123% of capacity**.
4. **Ceilings.** A flat 18-hour ceiling is 360,000/day, but that ignores peaking. The
   practical ceiling, where the peak hour saturates, is about **100,000–200,000/day**
   (base ~154,000).

**Bound used until Stage 5 freezes a dated prediction (A-011, inferred):**
- 2027 planning range: low 25,000, base 40,000, high 80,000 per day.
- 122,500 is the mature, capacity-constrained upper case.

**Consequence for the core question:** peak flow at Bukit Chagar is capped by line
capacity (10,000 pphpd) whichever daily figure is right. Stage 4 therefore tests the
interchange at the design capacity as well as at the daily-ridership-derived flows.
The evening peak (Singapore to JB arrivals dispersing into JB) matters most for
whether E-ART helps.

## 5. The 75% claim: status

- **Source:** Johor/federal officials, as reported (SRC-007, SRC-008). No data source
  or count location has been published.
- **Plausibility note, not a test:** "75% of vehicles entering and leaving Johor
  Bahru" depends entirely on how the cordon is drawn. Jalan Tebrau and the Tebrau
  Highway carry traffic toward Pasir Gudang, Kota Tinggi, and the North–South
  Expressway via Pandan. The Skudai Highway (Federal Route 1) is also a major
  approach; one secondary estimate puts it at ~184,000 vehicles/day. A single corridor
  carrying 75% of a city-wide cordon would be unusual. That is a reason to test the
  claim, not a finding.
- **Test:** V10 in `docs/validation-plan.md`. If no independent count data is
  obtained, the claim will be reported as **UNTESTED**.

## 6. Stage 1 pipeline proof

See `results/stage1/` and the handoff note `docs/handoffs/stage-1.md`
for the actual run outcome. Results are reported only from the committed run outputs.
