# Lakeflow — SAS Migration Pipeline (Bronze→Silver→Gold)

> **SAS Migration Architecture.** This spec defines a **Spark Declarative Pipeline (SDP)** that replaces legacy SAS batch processing. The `sas2databricks` accelerator parsed SAS business rules, extracted macro variables, and migrated PROC SQL transformations to DLT Python. Bronze→Silver→Gold layers replace SAS LIBNAME → DATA steps → PROC SQL workflows.

---

## SAS Migration Context

**Legacy SAS Architecture:**
- **Source**: SAS/ACCESS connecting to policy systems, claims databases
- **Processing**: SAS Enterprise Guide with PROC SQL, DATA steps, macro variables
- **Business Rules**: Stored in `.sas` files and SAS stored processes
- **Output**: SAS datasets consumed by SAS Visual Analytics

**Databricks Architecture (This Pipeline):**
- **Source**: Auto Loader / Lakeflow Connect → Bronze tables
- **Processing**: Spark Declarative Pipelines (DLT) with data quality expectations
- **Business Rules**: Extracted to DLT code + Metric Views
- **Output**: Delta tables consumed by AI/BI dashboards + Genie

---

## Shared Context

**Catalog/Schema:** `na-dbxtraining.hls_sas_dbx_claims`

**Affected Batch** (from SAS macro `%let affected_batch = 'AC-2026-Q1';`):
- Batch ID: `AC-2026-Q1`
- Model: AquaClean DW-9500 Series dishwasher
- Plant: Rockford, IL
- Issue: Defective inlet valve seals causing water leaks
- Units: ~12,000 distributed (IL, IN, OH, MI, WI)

**SAS Business Rules Migrated:**
```sas
/* Original SAS macros */
%let baseline_claims = 2500000;
%let spike_threshold = 1.25;
%let affected_batch = 'AC-2026-Q1';
```

**Databricks Equivalent:**
- Defined as DLT pipeline configuration variables
- Enforced in silver layer transformations
- Exposed as Metric View measures

---

## A. Data Generation (Synthetic)

**Skill**: `databricks-synthetic-data-gen`

Generate raw source data simulating SAS exports:

### Tables to Generate:
1. **raw_policyholders** (~100K) - Policy master file (SAS dataset: `SOURCE.POLICIES`)
2. **raw_appliances** (~10) - Appliance reference data (SAS dataset: `REFDATA.APPLIANCES`)
3. **raw_appliance_batches** (~500) - Manufacturing batches (SAS dataset: `REFDATA.BATCHES`)
4. **raw_claims** (~15K total: 14,660 normal + 340 affected) - Claims transactions (SAS dataset: `SOURCE.CLAIMS`)

Write these to `na-dbxtraining.demo_bravo_insurance_claims` schema (temporary holding area for migration).

### Data Shaping Rules:

**Baselines:**
- Normal weekly claims: $2.5M (~90 water damage claims/week)
- Spike at peak: $3.1M (~190 water damage claims, +25% overall)
- Current (decaying): $2.7M

**Temporal Pattern:**
- Spike peak: 3 weeks ago
- Build-up: 6-8 weeks ago
- Decay: last 2 weeks
- Peak must be in the PAST (not at chart edge)

**Geographic Skew (Affected Batch):**
- Normal distribution: IL 12% / TX 10% / CA 10% / FL 9% / etc.
- Affected batch: IL 30% / IN 20% / OH 18% / MI 15% / WI 12%
- Within IL: Chicago dominates (largest bubble on map)

**Affected Batch Characteristics:**
- 340 claims, all `claim_type = 'water_damage'`
- Descriptions contain: "water pooling", "slow leak", "dishwasher leak"
- All reference `appliance_batch_id = 'AC-2026-Q1'`

**Recall Notice Text** (on `raw_appliance_batches.recall_notice`):
> Product Safety Recall Notice PSR-2026-02-28. Product: AquaClean DW-9500 Series Dishwasher, Batch AC-2026-Q1 (manufactured Jan-Mar 2026, Rockford IL facility). Issue: defective inlet valve seal causing slow water leaks during wash cycles. Root cause: supplier batch of EPDM seals outside hardness spec (Shore A 68 vs required 75-80). Affected units: ~12,000 distributed across IL, IN, OH, MI, WI. Risk: property water damage from undetected leaks. Action: voluntary recall issued 2026-02-28; free replacement + installation offered to all registered owners.

---

## B. Spark Declarative Pipeline (SDP)

**Skill**: `databricks-pipelines`

**Important:** This pipeline uses the **modern SDP API** (`from pyspark import pipelines as dp`), not legacy DLT syntax (`import dlt`). See `specifications/SDP_MIGRATION.md` for migration details.

### Pipeline Options (Choose Your Migration Path)

We provide **THREE pipeline implementations** to match different SAS team skillsets:

| File | Approach | Best For |
|------|----------|----------|
| `claims_pipeline.py` | **Hybrid** (Python + SQL) | Bronze/Silver = Python, Gold = SQL. Balanced approach. |
| `claims_pipeline_sql.sql` | **Pure SQL** | Teams migrating PROC SQL-heavy SAS code, minimal Python. |
| *Future: streaming variant* | Advanced | Real-time ingestion (if needed later). |

**Recommendation for Demo:** Start with **Hybrid** (`claims_pipeline.py`) to show:
- Complex transformations → Python (when SQL gets messy)
- Simple aggregations → SQL (familiar to SAS PROC SQL teams)

Then mention the **Pure SQL** alternative exists for SQL-first shops.

---

### Pipeline Structure (Hybrid Approach)

**File**: `pipeline/claims_pipeline.py`

**Layers:**

#### 1. **Bronze** — Raw Ingestion
Replaces SAS LIBNAME + PROC IMPORT

Tables:
- `bronze_policyholders`
- `bronze_appliances`
- `bronze_appliance_batches`
- `bronze_claims`

**DLT Expectations** (replaces SAS data validation):
```python
@dlt.expect_all({
    "valid_claim_id": "claim_id IS NOT NULL",
    "valid_amount": "claim_amount_usd > 0",
    "valid_date": "claim_date IS NOT NULL"
})
```

**SAS Equivalent:**
```sas
data work.clean_claims;
    set source.claims;
    if claim_id = . then delete;
    if claim_amount <= 0 then delete;
    if claim_date = . then delete;
run;
```

#### 2. **Silver** — Business Rules & Enrichment
Replaces SAS DATA steps + PROC SQL joins

**Table**: `silver_claims_enriched`

**Business Rules Applied:**
1. **Affected Batch Flagging** (from SAS macro):
   ```python
   F.when(appliance_batch_id == "AC-2026-Q1", True).otherwise(False)
   ```

2. **Severity Classification** (from SAS CASE statement):
   ```python
   F.when((claim_type == "water_damage") & (claim_amount > 5000), "high")
    .when(claim_amount > 10000, "high")
    .when(claim_amount > 3000, "medium")
    .otherwise("low")
   ```

**Joins** (replaces SAS PROC SQL joins):
- Claims ← Policyholders (policy_id)
- Claims ← Appliances (appliance_id, LEFT)
- Claims ← Batches (appliance_batch_id, LEFT)

**SAS Equivalent:**
```sas
proc sql;
    create table work.claims_enriched as
    select c.*, p.*, a.*, b.*,
        case when b.batch_id = "&affected_batch" then 1 else 0 end as is_affected
    from claims c
    left join policies p on c.policy_id = p.policy_id
    left join appliances a on c.appliance_id = a.appliance_id
    left join batches b on c.batch_id = b.batch_id;
quit;
```

#### 3. **Gold** — Analytics Aggregations (SQL for Simplicity)
Replaces SAS PROC SUMMARY + PROC FREQ outputs

**Migration Note:** Gold layer uses **SQL syntax** to stay familiar to PROC SQL programmers.

Tables:
- `gold_claims` - Denormalized fact (for dashboard/Genie)
- `gold_daily_summary` - Daily rollup by state + claim_type
- `gold_weekly_summary` - Weekly rollup with baseline comparison
- `gold_affected_batch_analysis` - Affected batch deep-dive

**Weekly Summary with Baseline Logic (SQL):**
```sql
WITH weekly_agg AS (
    SELECT
        DATE_TRUNC('week', claim_date) AS week,
        COUNT(*) AS claim_count,
        SUM(claim_amount_usd) AS weekly_claims
    FROM LIVE.silver_claims_enriched
    GROUP BY week
)
SELECT
    week,
    claim_count,
    weekly_claims,
    weekly_claims / 2500000 AS ratio,  -- SAS baseline
    CASE
        WHEN weekly_claims / 2500000 > 1.25 THEN 'ALERT'  -- SAS spike threshold
        ELSE 'NORMAL'
    END AS status
FROM weekly_agg
ORDER BY week
```

**SAS Equivalent:**
```sas
%let baseline = 2500000;
%let spike_threshold = 1.25;

proc summary data=work.claims nway;
    class week;
    var claim_amount;
    output out=work.weekly sum=weekly_claims;
run;

data analytics.weekly_summary;
    set work.weekly;
    ratio = weekly_claims / &baseline;
    if ratio > &spike_threshold then status = 'ALERT';
    else status = 'NORMAL';
run;
```

**Why SQL for Gold Layer?**
- Syntax nearly identical to PROC SQL (minimal retraining)
- Aggregations are straightforward (no complex UDFs needed)
- Easier for SAS teams to review and maintain

---

## C. Metric Views (Governed Business Rules)

**Skill**: `databricks-metric-views`

**File**: `pipeline/metric_views.sql`

Metric Views replace SAS macro variables and stored calculations with governed, reusable KPIs:

### 1. `mv_claims_performance`
Replaces SAS `%claims_metrics` macro

**Measures:**
- `total_claims_usd` - Sum of claims
- `claim_count` - Number of claims
- `baseline_ratio` - Claims / $2.5M baseline
- `spike_alert` - Binary flag when ratio > 1.25

**Usage in Genie:**
```sql
SELECT
  DATE_TRUNC('week', date) AS week,
  MEASURE(total_claims_usd),
  MEASURE(baseline_ratio)
FROM mv_claims_performance
GROUP BY week;
```

### 2. `mv_affected_batch_metrics`
Replaces SAS `%batch_metrics` stored process

**Measures:**
- `affected_claim_count` - Claims from AC-2026-Q1
- `affected_claims_usd` - Total payout
- `affected_pct` - % of total claims

---

## D. Pipeline Deployment

**Configuration**: `pipeline/pipeline_config.yml`

**Create Pipeline:**
```bash
databricks pipelines create --json @pipeline/pipeline_config.yml
```

**Run Pipeline:**
```bash
databricks pipelines start-update <pipeline_id> --full-refresh
```

**Monitor:**
```bash
databricks pipelines get <pipeline_id>
```

---

## E. Validation

**After pipeline completes**, validate:

### 1. Row Counts
```sql
SELECT 'bronze_claims', COUNT(*) FROM hls_sas_dbx_claims.bronze_claims
UNION ALL
SELECT 'silver_claims_enriched', COUNT(*) FROM hls_sas_dbx_claims.silver_claims_enriched
UNION ALL
SELECT 'gold_claims', COUNT(*) FROM hls_sas_dbx_claims.gold_claims
UNION ALL
SELECT 'gold_affected_batch', COUNT(*) FROM hls_sas_dbx_claims.gold_affected_batch_analysis;
```

Expected: ~15K rows in claims tables

### 2. Affected Batch
```sql
SELECT
  COUNT(*) as affected_claims,
  SUM(claim_amount_usd) as total_amount
FROM hls_sas_dbx_claims.gold_claims
WHERE is_affected_batch = TRUE;
```

Expected: 340 claims, ~$2-3M total

### 3. Weekly Spike
```sql
SELECT week, weekly_claims, status
FROM hls_sas_dbx_claims.gold_weekly_summary
WHERE status = 'ALERT'
ORDER BY week DESC
LIMIT 5;
```

Expected: ALERT status ~3 weeks ago, decaying

### 4. Metric Views
```sql
SELECT
  DATE_TRUNC('week', date) AS week,
  MEASURE(total_claims_usd) AS claims,
  MEASURE(spike_alert) AS alert
FROM hls_sas_dbx_claims.mv_claims_performance
WHERE date >= CURRENT_DATE() - INTERVAL 8 WEEKS
GROUP BY week
ORDER BY week;
```

Expected: Spike alert = 1 for weeks 3-4 ago

---

## F. Update resources.json

After successful pipeline creation:

```json
{
  "created_resources": {
    "catalog": "na-dbxtraining",
    "schema": "hls_sas_dbx_claims",
    "pipeline_id": "<pipeline_id_from_create>",
    "metric_view_name": "hls_sas_dbx_claims.mv_claims_performance"
  }
}
```

---

## G. Alternative: Pure SQL Pipeline

**File**: `pipeline/claims_pipeline_sql.sql`

For teams that want **zero Python**, we provide a complete SQL-only implementation that produces **identical outputs**.

**When to Use:**
- SAS codebase is 80%+ PROC SQL (minimal DATA steps)
- Team has strong SQL skills but limited Python experience
- Want minimal syntax changes from SAS → Databricks

**Key Differences:**
```sql
-- SQL Pipeline (claims_pipeline_sql.sql)
CREATE OR REFRESH STREAMING TABLE silver_claims_enriched (
  CONSTRAINT positive_amount EXPECT (claim_amount_usd > 0) ON VIOLATION DROP ROW
)
AS
SELECT
    c.*,
    p.state,
    CASE
        WHEN c.appliance_batch_id = 'AC-2026-Q1' THEN TRUE
        ELSE FALSE
    END AS is_affected_batch
FROM STREAM(LIVE.bronze_claims) c
LEFT JOIN STREAM(LIVE.bronze_policyholders) p ON c.policy_id = p.policy_id;
```

vs

```python
# Python Pipeline (claims_pipeline.py)
@dlt.table(name="silver_claims_enriched")
@dlt.expect_or_drop("positive_amount", "claim_amount_usd > 0")
def silver_claims_enriched():
    bronze_claims = dlt.read("bronze_claims")
    bronze_policies = dlt.read("bronze_policyholders")
    return (
        bronze_claims
        .join(bronze_policies, "policy_id", "left")
        .withColumn("is_affected_batch",
            F.when(bronze_claims.appliance_batch_id == "AC-2026-Q1", True)
             .otherwise(False))
    )
```

Both produce the same Delta table. Choose based on team skillset.

---

## SAS Migration Summary

| SAS Component | Databricks Equivalent | Python Syntax | SQL Syntax |
|---------------|----------------------|---------------|------------|
| LIBNAME statements | Auto Loader / Lakeflow Connect | `spark.readStream` | `STREAMING TABLE` |
| DATA steps | DLT transformations | `@dlt.table` + Python | `CREATE LIVE TABLE` + SQL |
| PROC SQL joins | Joins | `.join()` | `LEFT JOIN` |
| Macro variables | Pipeline config + Metric Views | `F.lit(BASELINE)` | Literal `2500000` |
| PROC SUMMARY | DLT aggregations | `.groupBy().agg()` | `GROUP BY` + `SUM()` |
| Data validation | DLT expectations | `@dlt.expect_or_drop` | `CONSTRAINT ... EXPECT` |
| Stored processes | Metric View measures | N/A (language-agnostic) | N/A (language-agnostic) |
| SAS datasets | Delta tables | All layers | All layers |

**Talking Points:**
- **10x faster**: Spark vs SAS batch processing
- **Incremental**: Auto Loader vs full SAS table scans
- **Governed**: Metric Views vs scattered macro definitions
- **Natural language**: Genie vs writing SAS PROC SQL
- **Unified platform**: One lakehouse vs SAS + BI + ML silos
- **Flexible migration**: Choose Python, SQL, or both — same Delta output
