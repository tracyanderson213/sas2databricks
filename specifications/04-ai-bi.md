# AI/BI — Dashboard + Genie

Tables and columns referenced here are defined in `01-lakeflow.md`. Widgets read the two `gold_*` tables directly; the batch's `recall_notice` is fetched on-demand from `raw_appliance_batches`.

> **Talking-track-only products mentioned in the README** — do **not** build resources for these:
> - **Databricks One** is a workspace-level surface, not a buildable artifact. Once the dashboard and Genie space exist, they show up there for users with the right entitlement. Nothing to provision.
> - **Genie Code** is the AI authoring assist *inside* the Genie/SQL editor — referenced in the README narrative, not a separate resource.
> - **Unity Catalog** is the global governance layer — already in place at the workspace level. Just ensure the catalog/schema/grants applied in `01-lakeflow.md` are in effect.
> - **Lakeflow Connect** is the ingest narrative — talk track only.

---

## A. Genie Space

**Skill to use**: `databricks-genie-agents` — read `SKILLS/databricks-genie-agents/SKILL.md` before implementing.

Create `Bravo Insurance Claims Analytics` Genie Space.

### Tables

`gold_daily_summary` (trends + KPIs), `gold_claims` (per-claim investigation — denormalized state/city/claim_type/appliance/batch + `is_affected_batch` flag), `raw_appliances` (appliance catalog), `raw_appliance_batches` (batch detail + `recall_notice`), `raw_policyholders` (state joins, policy type).

The recall notice text lives on `raw_appliance_batches.recall_notice`. When Sarah asks Genie *"why are claims spiking?"*, the final hop is `SELECT recall_notice FROM raw_appliance_batches WHERE appliance_batch_id = 'AC-2026-Q1'` — Genie quotes it back inline. One join from the batch found in step 3 to the explanation in step 5; no intermediate table needed.

### Self-sufficient room

Anyone opening the Genie room must understand the story without prior context. Wire all three:

- **Space `description`** (set via `PATCH /api/2.0/genie/spaces/<id>`): 1-3 sentences naming the event (what happened + headline number + cause + blast radius) and pointing to the suggested questions in order. Pulled from the README — don't restate it, lift it.
- **Story-context `text_instruction`** at the TOP of `instructions.text_instructions[]`: WHAT HAPPENED · WHAT TO HELP THE PERSONA DO · TONE. ~5-8 lines. The LLM honors this on every turn.
- **`sample_questions`** chips AND matching `example_question_sqls` walk the story arc end-to-end in the same order — see "Sample Questions" below.

### Instructions

```
You analyze Bravo Insurance claims data for Sarah (VP Claims Operations, non-technical).

BASELINES: Normal weekly claims ~$2.5M, normal water damage rate ~90 claims/week, anomaly threshold > 20%.

HEADLINE NUMBERS — answer from gold_daily_summary:
- "What's our weekly claims total?" → SUM(claim_amount_usd) — current month, by week
- "Claims trend this month?"        → SUM(claim_amount_usd) — current month
- "Claims by state?"                → SUM(claim_amount_usd) — group by state (from gold_claims, not daily summary)

INVESTIGATION FLOW for "Why are claims spiking?":
1. gold_daily_summary → SUM(claim_amount_usd) by week → spot the 25% spike (~$3.1M peak ~3 weeks ago, decaying but still above baseline at ~$2.7M)
2. gold_claims → GROUP BY claim_type ORDER BY COUNT(*) DESC → water_damage dominates the increase
3. gold_claims WHERE claim_type = 'water_damage' GROUP BY model_name ORDER BY COUNT(*) DESC → AquaClean DW-9500 Series is the outlier
4. gold_claims WHERE model_name LIKE '%AquaClean DW-9500%' GROUP BY appliance_batch_id ORDER BY COUNT(*) DESC → batch AC-2026-Q1 has ~340 claims, next batch has <20
5. gold_claims → claim_description WHERE appliance_batch_id = 'AC-2026-Q1' → water leak complaints ("water pooling", "slow leak", "water damage behind dishwasher")
6. raw_appliance_batches → SELECT recall_notice WHERE appliance_batch_id = 'AC-2026-Q1' → quote the defective seal / Rockford plant / recall issued note inline. THIS IS THE PUNCHLINE — surface it explicitly in the answer.

GEOGRAPHIC FOLLOW-UP (optional, after root cause):
- "Which states have the most affected claims?" → gold_claims WHERE is_affected_batch = TRUE, GROUP BY state, ORDER BY COUNT(*) DESC → IL / IN / OH / MI / WI lead (Midwest concentration).

CUSTOMER FEEDBACK (from affected batch): "water pooling under dishwasher" / "slow leak from dishwasher" / "kitchen floor water damage" / "discovered water damage behind dishwasher"
```

### Sample Questions — story-arc walk

Ship the **full 6-question arc as chips** (`config.sample_questions`) so the user can pick any beat, but curate **only 3 as `instructions.example_question_sqls`** — the load-bearing ones where the SQL Genie picks matters. The other 3 chip-only questions Genie composes from scratch each time, which is fine (single-table aggregations Genie handles well unaided). Less curated SQL means cleaner room instructions and less drift when the schema evolves.

Chips (all 6, in arc order):
1. **Headline** — "What's our weekly claims total this month, and how does it compare to baseline?"
2. **Drill to claim type** — "Why are claims spiking? Trace it to the claim type and appliance model."
3. **Drill to batch + recall story** — "Which appliance batch is driving the spike, and what does the recall notice say?"
4. **Customer descriptions** — "What are claimants reporting? Show recent affected-batch claim descriptions."
5. **Blast radius** — "Where are the affected claims? Group by state."
6. **Recovery** — "Are claims recovering? Show the trend and what's expected next."

Curated SQLs (3 — the ones where Genie shouldn't have to guess):
- **Headline** — weekly SUM(claim_amount_usd) from `gold_daily_summary`, last 8 weeks, with baseline comparison.
- **Drill to batch + recall story** — CTE finds the top batch for AquaClean DW-9500, JOINs `raw_appliance_batches` to quote `recall_notice` — the punchline. This SQL is load-bearing because it crosses 2 tables for a join Genie would otherwise miss.
- **Recovery** — last 6 weeks of SUM(claim_amount_usd) showing the decay from peak.

### Validation

- "What's our weekly claims total this month?" → answered from `gold_daily_summary`: `SUM(claim_amount_usd)` by week for the current month, with a baseline comparison.
- "Why are claims spiking?" → walks to the 25% spike → water damage dominates → AquaClean DW-9500 Series is the outlier → batch AC-2026-Q1 has ~340 claims → water leak descriptions → **quotes the recall_notice text inline** (defective inlet valve seal / Rockford / recall issued). All six beats present.
- "What are claimants reporting?" → surfaces *"water pooling"*, *"slow leak"*, *"water damage"*.
- "Which states have the most affected claims?" → IL is the largest, then IN / OH / MI.

Add `genie_space_id` to `resources.json`.

---

## B. Dashboard

**Skill to use**: `databricks-aibi-dashboards` — read `SKILLS/databricks-aibi-dashboards/SKILL.md` before implementing. The skill owns the JSON shape, encoding rules, and grid math; this spec is story-level (WHAT, not HOW).

Create `Bravo Insurance Claims Dashboard`. Save locally as `PROJECT/dashboard.json`. Link the Genie space from section A.

Reminder: set `--dataset-catalog` and `--dataset-schema` when running `databricks lakeview create` and `databricks lakeview update` (update strips them otherwise).

### Why this dashboard works (design principles)

A great Databricks dashboard reads in 5 seconds and supports a deep-dive in 30. This one earns its keep on:

- **Two pages, one story**: page 1 is the glance — *"something happened, here's the shape and forecast"*. Page 2 is the deep-dive — *"here's exactly which claim types, appliance models, batches, states, and descriptions"*. Claims managers land on page 1 daily; analysts open page 2 for investigation.
- **Four datasets, kept lean**: one daily aggregate (`ds_daily` → KPIs + donut + policy volume area), one row-level fact (`ds_claims` → map, state splits, descriptions), one forecast TVF (`ds_forecast`, separate because `AI_FORECAST` can't share), one pre-bucketized sankey source (`ds_sankey_flow` — top-10 appliance models + top-10 batches, long tails bucketed in-SQL). Cross-widget click-filtering works inside each dataset — keeping `ds_claims` shared across 6 widgets is what makes the Investigation page interactive.
- **KPI sparklines carry the story at a glance**: each counter uses the `period` encoding so a tiny weekly trend renders behind the headline number. The Claims counter shows the spike-then-decay shape even before the eye drops to the forecast.
- **A map is the visual hook**: bubble map on Operations page, full width — instantly readable, beats any table for *"where are the affected policyholders?"*.
- **One AI showcase per page**: Operations gets `AI_FORECAST` (showing AI-native analytics inside a dashboard).
- **Clean theme — no borders, white canvas, blue palette**: `widgetBorderColor` matches `widgetBackgroundColor` so widgets float on the canvas; left-aligned widget headers; one cohesive cool palette. The result reads as "modern analytics product", not "default template".
- **Self-sufficient pages**: Row 1 of every page is a markdown `text` widget that names the event (what / when / cause / blast radius) and tells the reader what to look at on this page (which widget answers which question, what shape they should expect to see, how to drill). A user opening this dashboard cold should know the story in 5 seconds. Lift the situation from the README — don't repeat the full narrative, just the dashboard-relevant tour.

### Theme

```
canvasBackgroundColor: #F5F7FB (light, blue-tinted neutral) / #0F1419 (dark)
widgetBackgroundColor: #FFFFFF (light) / #161B22 (dark)
widgetBorderColor:     same as widgetBackgroundColor (= no visible border)
fontColor:             #1F2530 (light) / #E8ECF0 (dark)
selectionColor:        #4F7CE3 (light) / #8ACAFF (dark)
visualizationColors:   ["#094074","#3C6997","#5ADBFF","#FFDD4A","#FE9000"]
widgetHeaderAlignment: LEFT
```

5-stop palette progresses cool → warm: deep navy → steel blue → sky cyan → soft yellow → vivid orange. Position 0 (`#094074` navy) is the visual anchor — used for the largest claim type (water damage in this demo) and KPI sparklines.

**Semantic colors (literal-hex pinned everywhere, NEVER `themeColorType: position N`):**
- **Affected batch / incident annotation** → `#FFDD4A` soft yellow.
- **Normal claims / baseline** → `#3C6997` steel blue.

**Claim type color pins (literal-hex on every widget colored by `claim_type`)** — Lakeview cycles the palette by SQL-result order, which differs across widgets reading different datasets. Pinning each claim type guarantees the same color across donut + stacked bar:

| Claim Type | Hex |
|---|---|
| water_damage | `#094074` (the affected type — anchor) |
| fire | `#3C6997` |
| theft | `#5ADBFF` |
| wind | `#FFDD4A` |
| other | `#FE9000` |

### Datasets (4 total)

| Name | Source | Powers |
|---|---|---|
| `ds_daily` | daily grain from `gold_daily_summary`: date, state, claim_type, claim counts, claim $ | 4 KPI counters + claim type donut + weekly-policies area chart (policy count derived from claim-to-policy ratio assumption) |
| `ds_claims` | row-level from `gold_claims`, plus a derived `source` ("Affected batch" / "Normal claims" from `is_affected_batch`) | Bubble map, claims-by-state bar, affected-vs-normal split bars (state + claim type), city table, descriptions table |
| `ds_forecast` | weekly claim actuals + an `AI_FORECAST` band, over a 180-day trailing window, floored at 0 (no negative claims) | Forecast-line widget. The 180-day window is forecast **input** shape, not display windowing — so the global Date filter must not touch this dataset. |
| `ds_sankey_flow` | claim_type → model → batch claim counts from `gold_claims`, top-10 models + top-10 batches, long tails bucketed as "Other …" | Sankey widget on the Investigation page |

**No date clamps inside `ds_daily` / `ds_claims` / `ds_sankey_flow`** — the global Date Range filter is the single source of windowing; a clamp in the dataset would narrow what the filter can select. `ds_forecast` is the exception: its 180-day window is forecast input, not display filtering.

### Global filters (left panel — `PAGE_TYPE_GLOBAL_FILTERS`)

| Filter | Column | Datasets | Default |
|---|---|---|---|
| Date Range | `date` (ds_daily) / `claim_date` (ds_claims) | ds_daily, ds_claims, ds_sankey_flow | All (no clamp) |
| State | `state` | ds_daily, ds_claims, ds_sankey_flow | All |
| Claim Type | `claim_type` | ds_daily, ds_claims, ds_sankey_flow | All |
| Source | `source` ("Affected batch" / "Normal claims" — derived column on ds_claims) | ds_claims | All |

`ds_forecast` must stay **unfiltered** by all four filters — `AI_FORECAST` needs its stable trailing window.

### Page 1 — Operations (the glance)

Layout is a 12-column grid; widgets list their `(x, y, width, height)`.

| Row (y) | x | w | h | Widget |
|---|---|---|---|---|
| 0  | 0 | 12 | 3 | `title` (markdown) |
| 3  | 0 |  3 | 3 | `kpi_claims` |
| 3  | 3 |  3 | 3 | `kpi_claim_count` |
| 3  | 6 |  3 | 3 | `kpi_water_damage` |
| 3  | 9 |  3 | 3 | `kpi_policies` |
| 6  | 0 | 12 | 5 | `trend_chart` (forecast-line) |
| 11 | 0 |  7 | 6 | `policies_area` |
| 11 | 7 |  5 | 7 | `state_chart_claims` |
| 17 | 0 |  7 | 6 | `claims_map` (bubble map) |
| 18 | 7 |  5 | 5 | `claim_type_donut` |

**`title` — markdown widget**. Self-sufficient page header so a cold reader knows what they're looking at. ~5 lines covering: what happened (claims spiked 25% three weeks ago) · cause (the affected batch AC-2026-Q1 + Rockford plant + defective seal) · blast radius (340 claims, Midwest-skewed) · what to see on this page (KPI sparklines carry the spike-then-decay shape, forecast marks the batch manufacture date with a vertical bar, donut shows water damage dominates, map lights Midwest). Lift the substance from the README — don't repeat it verbatim.

**4 × `counter`** — `kpi_claims`, `kpi_claim_count`, `kpi_water_damage`, `kpi_policies`. Source: `ds_daily`. Pin `value.color` to the primary literal-hex (`#094074`) for the spike-anchor tiles.

- **Claims $** · `SUM(claim_amount_usd)` · `number-currency` USD compact, `decimalPlaces: max 1` · color `#094074` · *the spike's headline number.*
- **Claim Count** · `SUM(claim_count)` · number compact · color `#094074`.
- **Water Damage $** · `SUM(claim_amount_usd) WHERE claim_type = 'water_damage'` · `number-currency` USD compact · color `#094074` · *isolates the affected claim type.*
- **Active Policies** · `COUNT(DISTINCT policy_id)` (estimate or assumed stable) · number compact · color `#094074` · *paired with Claims — "this is a claims-rate problem, not a policy-growth problem".*

**`trend_chart` — `forecast-line` "Weekly claims — actuals + forecast"** (12-wide). Source: `ds_forecast`. x = `week` (temporal); y `claims` = actuals (solid); y `claims_forecast` / `claims_upper` / `claims_lower` = forecast band (dashed); y format `number-currency` USD compact. Bridging row repeating last actual as `claims_forecast` so the band doesn't disconnect at the seam.

- **Vertical-line annotation** on `AFFECTED_BATCH_DATE`, label format `"Appliance batch issue: AC-2026-Q1 distributed"` (short, executive-readable). No explicit `color` so the marker inherits the theme neutral — label carries the meaning. Same date as the affected batch's `recall_notice` — they MUST match.
- **Frame description** (renders below the title): *"Claims spiked 3 weeks ago, decaying back toward baseline. Vertical bar = the day the affected batch was distributed to Midwest markets."* Self-explains the chart.
- *Baseline ticks flat → annotation bar drops in (the batch distributed) → ~28w later the line spikes to ~$3.1M → decays toward baseline → continues as dashed band 4w ahead. Cause → effect → what's next, in one chart.*

**`policies_area` (7-wide) + `state_chart_claims` (5-wide) — side by side**

- **`area` · "Weekly active policies by state (top 5)"** (left, 7-wide) · `ds_daily` · x = `weekly(date)`, y = assumed stable policy count per state, color = `state`. **Only IL is pinned** (`#FE9000`); other states fall through to default palette positions. The IL line is the visual anchor (largest state by affected claims), so a literal pin keeps it warm-orange. Frame description: *"Policy counts stay stable — the business is fine, only claims spiked."* *Counter-argument widget — proves the policy line isn't disturbed.*
- **`bar` horizontal stacked · "Claims by state"** (right, 5-wide) · `ds_claims` · y = `state`, x = `SUM(claim_amount_usd)`, **color = `claim_type` with the same 5-stop literal-hex pins as the donut** (water_damage→`#094074`, fire→`#3C6997`, theft→`#5ADBFF`, wind→`#FFDD4A`, other→`#FE9000`). *IL leads, then IN / OH / MI / WI — and the deep-navy water damage slice dominates every affected-state stack.*

**`claims_map` (7-wide) + `claim_type_donut` (5-wide) — side by side**

- **`symbol-map` · "Affected policyholders — bubble map"** (left, 7-wide). Source: `ds_claims` (no widget-level filter). Encoding `coordinates: { latitude: policyholder_lat, longitude: policyholder_lng }`. Group implicit by `(city, state)`, size = `COUNT(DISTINCT claim_id)`, color = `SUM(claim_amount_usd)`, tooltip city + count + claims $. `mark.opacity: 1` (solid). `colorRamp.scheme: "YlOrRd"`. *Midwest lights up: Chicago dominates deep red (~80+ affected claims), then Indianapolis / Cleveland / Detroit cluster.*
- **`pie` (donut) · "Claims by type"** (right, 5-wide) · `ds_daily` · slices = `claim_type`, angle = `SUM(claim_amount_usd)`, color via literal-hex claim type pins (above) · *one slice dwarfs the rest — water damage in deep navy.*

### Page 2 — Investigation (the deep-dive)

Same 12-column grid as Page 1.

| Row (y) | x | w | h | Widget |
|---|---|---|---|---|
|  0 | 0 | 12 | 4 | `claims_title` (markdown) |
|  4 | 0 | 12 | 8 | `claim_type_model_batch_sankey` |
| 12 | 0 | 12 | 1 | `sec_compare` (markdown: `## Affected batch vs normal claims`) |
| 13 | 0 |  6 | 6 | `state_split_chart` |
| 13 | 6 |  6 | 6 | `claim_type_split_chart` |
| 19 | 0 | 12 | 1 | `sec_geography` (markdown: `## Geography & descriptions`) |
| 20 | 0 |  6 | 5 | `city_table` |
| 20 | 6 |  6 | 5 | `affected_claims_table` |
| 25 | 0 | 12 | 6 | `descriptions_table` |

**`claims_title` — markdown widget (12-wide)**. Same pattern as Page 1's title: self-sufficient, ~5 lines. Frames the deep-dive: same data split by the dimensions that matter · the chain that emerges (water damage → AquaClean DW-9500 → one batch AC-2026-Q1 → Midwest dominance → water leak descriptions) · interaction hint: "click any 'Affected batch' bar to filter every other widget on the page".

**`claim_type_model_batch_sankey` — `sankey` "Claims flow — Claim Type → Appliance Model → Batch"** (12-wide). Source: `ds_sankey_flow`. `value = claim_amount_usd`, `stages = [claim_type, model_name, appliance_batch_id]`. Frame description: *"Water damage claims converge on AquaClean DW-9500, all from batch AC-2026-Q1."*

**`sec_compare` — section heading (12-wide, h=1)**: markdown `## Affected batch vs normal claims`.

**`state_split_chart` (6-wide) + `claim_type_split_chart` (6-wide) — side by side**. Both color by `source` with literal-hex pins (`Affected batch` → `#FFDD4A` soft yellow, `Normal claims` → `#3C6997` steel blue).

- **`bar` grouped · "Claims by state: affected batch vs normal"** (left) · `ds_claims` · x = `state`, y = `SUM(claim_amount_usd)`, color = `source` · *every Midwest state: yellow bar towers over steel blue — spike is the one batch in the Midwest, not a portfolio-wide trend.*
- **`bar` horizontal grouped · "Claim types: affected batch vs normal"** (right) · `ds_claims` · y = `claim_type`, x = `COUNT(claim_id)`, color = `source` · *`water_damage` is ~all yellow; the other types ~all steel blue — a product problem on this batch.*

**`sec_geography` — section heading (12-wide, h=1)**: markdown `## Geography & descriptions`.

**`city_table` (6-wide) + `affected_claims_table` (6-wide) — side by side**

- **`table` · "Claims by city"** (left) · `ds_claims` · columns `city`, `state`, `COUNT(DISTINCT claim_id)` AS `Claims`, `SUM(claim_amount_usd)` AS `Claim $`, sort `Claims` DESC · *Chicago on top, then Indianapolis / Cleveland / Detroit — same cluster as the map, ranked with claim $.*
- **`table` · "Affected batch claims summary"** (right) · `ds_claims WHERE is_affected_batch` · columns `state`, `COUNT(claim_id)` AS `Claims`, `AVG(claim_amount_usd)` AS `Avg $` · *IL / IN / OH / MI / WI dominate.*

**`descriptions_table` — `table` "Claim descriptions"** (12-wide, bottom). Source: `ds_claims`. Columns: `claim_date` (Date), `model_name` (Appliance), `state`, `city`, `claim_amount_usd` (Claim $), `claim_description` (Description, wrap). Frame description: *"Filter by Source='Affected batch' to surface the bad-batch complaints."*

- *Water leak complaints — "water pooling", "slow leak", "water damage behind dishwasher" — cluster when filtered. The raw descriptions close the arc with verbatim evidence. Full-width because the Description column needs the horizontal room to read.*

### Validation

Open the published dashboard and confirm the story reads at a glance: the claim spike stands out, the affected batch/appliance model dominates the investigation widgets, the map lights up Midwest (Chicago largest), and the global filters update every widget. Add `dashboard_id` to `resources.json`.
