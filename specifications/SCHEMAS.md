# HLS SAS DBX Migration — Data Schemas

Complete schema reference for all tables in the claims analytics pipeline.

## Schema Hierarchy

```
na-dbxtraining.demo_bravo_insurance_claims     # Source data (raw landing)
  ├── raw_policyholders
  ├── raw_appliances
  ├── raw_appliance_batches
  └── raw_claims

na-dbxtraining.hls_sas_dbx_claims              # Pipeline output (Bronze→Silver→Gold)
  ├── bronze_policyholders
  ├── bronze_appliances
  ├── bronze_appliance_batches
  ├── bronze_claims
  ├── silver_claims_enriched
  ├── gold_claims
  ├── gold_daily_summary
  ├── gold_weekly_summary
  ├── gold_affected_batch_analysis
  ├── mv_claims_performance (Metric View)
  └── mv_affected_batch_metrics (Metric View)
```

---

## Source Tables (Raw Landing Zone)

### 1. `raw_policyholders`

**Purpose:** Policy master file (replaces SAS: SOURCE.POLICIES)

| Column | Type | Description | SAS Equivalent |
|--------|------|-------------|----------------|
| `policy_id` | STRING | Primary key (POL-XXXXXX) | policy_id |
| `policyholder_name` | STRING | Policyholder full name | policyholder_name |
| `email` | STRING | Contact email | email |
| `state` | STRING | Two-letter state code (IL, TX, CA, etc.) | state |
| `city` | STRING | City name | city |
| `policyholder_lat` | DOUBLE | Latitude (for geographic viz) | latitude |
| `policyholder_lng` | DOUBLE | Longitude (for geographic viz) | longitude |
| `policy_type` | STRING | 'homeowners', 'renters', 'condo' | policy_type |
| `coverage_limit_usd` | DOUBLE | Coverage amount ($50K-$500K) | coverage_limit |
| `effective_date` | STRING | Policy start date (YYYY-MM-DD) | effective_date |

**Row Count:** ~100,000

**SAS Business Rules:**
- `coverage_limit_usd >= 50000 AND <= 500000`
- `policy_type IN ('homeowners', 'renters', 'condo')`

---

### 2. `raw_appliances`

**Purpose:** Appliance reference catalog (replaces SAS: REFDATA.APPLIANCES)

| Column | Type | Description | SAS Equivalent |
|--------|------|-------------|----------------|
| `appliance_id` | STRING | Primary key (APP-XXXXXX) | appliance_id |
| `model_name` | STRING | Product name (e.g., "AquaClean DW-9500 Series") | model_name |
| `manufacturer` | STRING | Brand name | manufacturer |
| `category` | STRING | 'dishwasher', 'washer', 'dryer', etc. | category |
| `retail_price_usd` | DOUBLE | MSRP | retail_price |
| `launch_year` | INT | Year introduced (2020-2026) | launch_year |

**Row Count:** ~10

**Key Record:**
- `appliance_id = 'APP-000001'`
- `model_name = 'AquaClean DW-9500 Series'` ← **Affected model**

---

### 3. `raw_appliance_batches`

**Purpose:** Manufacturing batch tracking (replaces SAS: REFDATA.BATCHES)

| Column | Type | Description | SAS Equivalent |
|--------|------|-------------|----------------|
| `appliance_batch_id` | STRING | Primary key (AC-2026-Q1, etc.) | batch_id |
| `appliance_id` | STRING | Foreign key → raw_appliances | appliance_id |
| `manufacture_date` | STRING | Production date (YYYY-MM-DD) | manufacture_date |
| `plant_location` | STRING | Factory location | plant_location |
| `units_produced` | INT | Batch size | units_produced |
| `status` | STRING | 'active', 'on_hold', 'recalled' | status |
| `recall_notice` | STRING | Text of recall (NULL for normal batches) | recall_notice |

**Row Count:** ~500

**Key Record:**
- `appliance_batch_id = 'AC-2026-Q1'` ← **Affected batch**
- `status = 'recalled'`
- `recall_notice = "Product Safety Recall Notice PSR-2026-02-28. Product: AquaClean DW-9500 Series..."` (full text)

---

### 4. `raw_claims`

**Purpose:** Claims transactions (replaces SAS: SOURCE.CLAIMS)

| Column | Type | Description | SAS Equivalent |
|--------|------|-------------|----------------|
| `claim_id` | STRING | Primary key (CLM-YYYYMMDD-HASH) | claim_id |
| `policy_id` | STRING | Foreign key → raw_policyholders | policy_id |
| `appliance_id` | STRING | Foreign key → raw_appliances (NULL if not appliance-related) | appliance_id |
| `appliance_batch_id` | STRING | Foreign key → raw_appliance_batches (NULL if not appliance) | batch_id |
| `claim_date` | STRING | Claim filed timestamp (YYYY-MM-DD HH:MM:SS) | claim_date |
| `claim_type` | STRING | 'water_damage', 'fire', 'theft', 'wind', 'other' | claim_type |
| `claim_amount_usd` | DOUBLE | Payout amount ($100-$100K) | claim_amount |
| `claim_description` | STRING | Incident description | claim_description |
| `severity` | STRING | 'low', 'medium', 'high' (from SAS CASE logic) | severity |
| `state` | STRING | State where claim occurred | state |

**Row Count:** ~15,000 (14,660 normal + 340 affected batch)

**SAS Business Rules (embedded in generation):**
```sas
/* Severity classification */
if claim_type = 'water_damage' and claim_amount > 5000 then severity = 'high';
else if claim_amount > 10000 then severity = 'high';
else if claim_amount > 3000 then severity = 'medium';
else severity = 'low';
```

**Affected Batch Pattern:**
- 340 claims with `appliance_batch_id = 'AC-2026-Q1'`
- All have `claim_type = 'water_damage'`
- Descriptions: "Water pooling under dishwasher...", "Slow leak discovered...", etc.

---

## Pipeline Tables (Bronze Layer)

Bronze tables are **identical copies** of raw tables with DLT expectations applied.

### `bronze_policyholders`
Same schema as `raw_policyholders` + DLT expectations.

### `bronze_appliances`
Same schema as `raw_appliances`.

### `bronze_appliance_batches`
Same schema as `raw_appliance_batches`.

### `bronze_claims`
Same schema as `raw_claims` + DLT expectations:
- `valid_claim_id`: claim_id IS NOT NULL
- `valid_amount`: claim_amount_usd > 0
- `valid_date`: claim_date IS NOT NULL

---

## Pipeline Tables (Silver Layer)

### `silver_claims_enriched`

**Purpose:** Fully denormalized claims with all joins and business rules applied.

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| **Claim Fields** |||
| `claim_id` | STRING | Claim ID | bronze_claims |
| `policy_id` | STRING | Policy ID | bronze_claims |
| `appliance_id` | STRING | Appliance ID | bronze_claims |
| `appliance_batch_id` | STRING | Batch ID | bronze_claims |
| `claim_date` | STRING | Claim timestamp | bronze_claims |
| `claim_type` | STRING | Type | bronze_claims |
| `claim_amount_usd` | DOUBLE | Amount | bronze_claims |
| `claim_description` | STRING | Description | bronze_claims |
| **Policyholder Fields** |||
| `policyholder_name` | STRING | Name | bronze_policyholders |
| `state` | STRING | State | bronze_policyholders |
| `city` | STRING | City | bronze_policyholders |
| `policyholder_lat` | DOUBLE | Latitude | bronze_policyholders |
| `policyholder_lng` | DOUBLE | Longitude | bronze_policyholders |
| `policy_type` | STRING | Policy type | bronze_policyholders |
| `coverage_limit_usd` | DOUBLE | Coverage limit | bronze_policyholders |
| **Appliance Fields** |||
| `model_name` | STRING | Appliance model | bronze_appliances |
| `manufacturer` | STRING | Brand | bronze_appliances |
| `category` | STRING | Category | bronze_appliances |
| **Batch Fields** |||
| `plant_location` | STRING | Manufacturing plant | bronze_appliance_batches |
| `batch_status` | STRING | Batch status | bronze_appliance_batches |
| **Business Rules (Derived)** |||
| `is_affected_batch` | BOOLEAN | TRUE if batch = AC-2026-Q1 | **SAS macro** |
| `severity` | STRING | 'low'/'medium'/'high' from SAS CASE | **SAS CASE** |

**DLT Expectations:**
- `positive_amount`: claim_amount_usd > 0 (DROP ROW)
- `valid_policy`: policy_id IS NOT NULL (DROP ROW)

**SAS Equivalent:**
```sas
proc sql;
  create table work.claims_enriched as
  select c.*, p.*, a.*, b.*,
    case when b.batch_id = "&affected_batch" then 1 else 0 end as is_affected_batch
  from claims c
  left join policies p on c.policy_id = p.policy_id
  left join appliances a on c.appliance_id = a.appliance_id
  left join batches b on c.batch_id = b.batch_id;
quit;
```

---

## Pipeline Tables (Gold Layer)

### `gold_claims`

**Purpose:** Denormalized fact table for analytics (passthrough from Silver).

**Schema:** Identical to `silver_claims_enriched`.

**SAS Equivalent:**
```sas
data analytics.claims_fact;
  set work.claims_enriched;
run;
```

---

### `gold_daily_summary`

**Purpose:** Daily aggregations by state and claim type.

| Column | Type | Description |
|--------|------|-------------|
| `date` | DATE | Calendar date |
| `state` | STRING | State code |
| `claim_type` | STRING | Claim type |
| `claim_count` | BIGINT | Number of claims |
| `claim_amount_usd` | DOUBLE | Total payout |

**SAS Equivalent:**
```sas
proc summary data=work.claims_enriched nway;
  class claim_date state claim_type;
  var claim_amount_usd;
  output out=analytics.daily_summary n=claim_count sum=claim_amount_usd;
run;
```

---

### `gold_weekly_summary`

**Purpose:** Weekly rollup with baseline comparison.

| Column | Type | Description |
|--------|------|-------------|
| `week` | TIMESTAMP | Week start (Monday) |
| `claim_count` | BIGINT | Claims filed |
| `weekly_claims` | DOUBLE | Total payout |
| `ratio` | DOUBLE | weekly_claims / 2,500,000 (baseline) |
| `vs_baseline_pct` | DOUBLE | (ratio - 1) * 100 |
| `status` | STRING | 'ALERT' if ratio > 1.25, else 'NORMAL' |

**Key Business Logic:**
- Baseline: $2,500,000 (from SAS macro `%let baseline_claims = 2500000;`)
- Spike threshold: 1.25 (from SAS macro `%let spike_threshold = 1.25;`)

**SAS Equivalent:**
```sas
%let baseline = 2500000;
%let spike_threshold = 1.25;

proc sql;
  create table analytics.weekly_claims as
  select
    intnx('week', claim_date, 0) as week,
    sum(claim_amount_usd) as weekly_claims,
    calculated weekly_claims / &baseline as ratio,
    case when calculated ratio > &spike_threshold then 'ALERT' else 'NORMAL' end as status
  from work.claims_enriched
  group by calculated week;
quit;
```

---

### `gold_affected_batch_analysis`

**Purpose:** Deep-dive on affected batch AC-2026-Q1.

| Column | Type | Description |
|--------|------|-------------|
| `state` | STRING | State code |
| `claim_type` | STRING | Claim type |
| `model_name` | STRING | Appliance model |
| `plant_location` | STRING | Manufacturing plant |
| `claim_count` | BIGINT | Claims from batch |
| `total_amount` | DOUBLE | Total payout |
| `avg_amount` | DOUBLE | Average claim |
| `first_claim_date` | STRING | Earliest claim |
| `last_claim_date` | STRING | Latest claim |
| `pct_of_total` | DOUBLE | % of all affected claims |

**Filter:** `is_affected_batch = TRUE`

**SAS Equivalent:**
```sas
%macro batch_analysis(batch_id=);
  proc freq data=work.claims_enriched;
    where appliance_batch_id = "&batch_id";
    tables state * claim_type / out=analytics.batch_analysis;
  run;
%mend;
%batch_analysis(batch_id=AC-2026-Q1);
```

---

## Metric Views (Governed KPIs)

### `mv_claims_performance`

**Purpose:** Governed metrics replacing SAS macro variables.

**Dimensions:**
- `date` (DATE)
- `state` (STRING)
- `claim_type` (STRING)

**Measures:**

| Measure | Type | Definition | SAS Macro |
|---------|------|------------|-----------|
| `total_claims_usd` | CURRENCY | SUM(claim_amount_usd) | N/A |
| `claim_count` | NUMBER | COUNT(*) | N/A |
| `avg_claim_amount` | CURRENCY | AVG(claim_amount_usd) | N/A |
| `baseline_ratio` | RATIO | total / 2,500,000 | `%let baseline_claims` |
| `spike_alert` | NUMBER | 1 if ratio > 1.25, else 0 | `%let spike_threshold` |

**Source Table:** `gold_daily_summary`

**Usage:**
```sql
SELECT
  DATE_TRUNC('week', date) AS week,
  MEASURE(total_claims_usd),
  MEASURE(baseline_ratio)
FROM na-dbxtraining.hls_sas_dbx_claims.mv_claims_performance
GROUP BY week;
```

---

### `mv_affected_batch_metrics`

**Purpose:** Affected batch-specific metrics.

**Dimensions:**
- `state` (STRING)
- `model_name` (STRING)

**Measures:**

| Measure | Type | Definition |
|---------|------|------------|
| `affected_claim_count` | NUMBER | COUNT(*) WHERE is_affected_batch |
| `affected_claims_usd` | CURRENCY | SUM(amount) WHERE is_affected_batch |
| `affected_pct` | PERCENT | affected / total |
| `normal_claim_count` | NUMBER | COUNT(*) WHERE NOT is_affected_batch |
| `avg_affected_claim` | CURRENCY | AVG(amount) WHERE is_affected_batch |

**Source Table:** `gold_claims`

---

## Data Volumes

| Table | Rows | Notes |
|-------|------|-------|
| `raw_policyholders` | ~100,000 | Policy master |
| `raw_appliances` | ~10 | Reference catalog |
| `raw_appliance_batches` | ~500 | 1 recalled, rest active |
| `raw_claims` | ~15,000 | 340 affected batch |
| `silver_claims_enriched` | ~15,000 | After joins + validation |
| `gold_daily_summary` | ~500-1000 | 6 months × states × types |
| `gold_weekly_summary` | ~26 | 6 months of weeks |
| `gold_affected_batch_analysis` | ~20 | State × claim_type for affected |

---

## Key Relationships

```
raw_policyholders (1) ←─┐
                         │
raw_appliances (1) ←──┐  │
                      │  │
raw_appliance_batches (1) ─┼─→ raw_claims (∞)
                      │  │
                      └──┘
```

**Foreign Keys:**
- `raw_claims.policy_id` → `raw_policyholders.policy_id` (required)
- `raw_claims.appliance_id` → `raw_appliances.appliance_id` (optional)
- `raw_claims.appliance_batch_id` → `raw_appliance_batches.appliance_batch_id` (optional)
- `raw_appliance_batches.appliance_id` → `raw_appliances.appliance_id` (required)

---

## Sample Queries

### Check affected batch claims
```sql
SELECT
  state,
  COUNT(*) as claims,
  SUM(claim_amount_usd) as total_amount
FROM na-dbxtraining.demo_bravo_insurance_claims.raw_claims
WHERE appliance_batch_id = 'AC-2026-Q1'
GROUP BY state
ORDER BY total_amount DESC;
```

### Weekly spike validation
```sql
SELECT
  week,
  weekly_claims,
  ratio,
  status
FROM na-dbxtraining.hls_sas_dbx_claims.gold_weekly_summary
WHERE status = 'ALERT'
ORDER BY week DESC;
```

### Severity distribution
```sql
SELECT
  severity,
  COUNT(*) as count,
  AVG(claim_amount_usd) as avg_amount
FROM na-dbxtraining.demo_bravo_insurance_claims.raw_claims
GROUP BY severity
ORDER BY severity;
```
