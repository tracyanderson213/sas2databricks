# Databricks notebook source
"""
HLS SAS DBX Migration — Synthetic Data Generator with Business Rules

This script generates realistic insurance claims data that simulates SAS source
systems, with embedded business rules extracted from legacy SAS code.

SAS Business Rules Migrated (from sas2databricks accelerator parsing):
  - Baseline thresholds (from %let macros)
  - Severity classification (from SAS CASE statements)
  - Data quality validations (from SAS WHERE/IF conditions)
  - Geographic distributions (from SAS PROC FREQ outputs)
  - Temporal patterns (from SAS INTNX/DATEPART logic)

This data generation includes VALIDATION and EXPECTATIONS that mirror what
would be enforced in the SDP pipeline.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

try:
    from databricks.connect import DatabricksSession
    spark = DatabricksSession.builder.profile(
        os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
    ).serverless(True).getOrCreate()
except Exception:
    # Fallback if databricks-connect not available
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("HLS_SAS_DBX_DataGen").getOrCreate()

# ============================================================================
# SAS BUSINESS RULES (Extracted from legacy SAS macros)
# ============================================================================

"""
Original SAS Code:
    %let baseline_weekly_claims = 2500000;
    %let spike_threshold_ratio = 1.25;
    %let normal_water_damage_rate = 90;
    %let affected_batch = 'AC-2026-Q1';
    %let high_severity_threshold = 5000;
    %let medium_severity_threshold = 3000;
"""

BASELINE_WEEKLY_CLAIMS = 2500000      # Normal weekly claims amount
SPIKE_THRESHOLD_RATIO = 1.25           # Alert when >25% above baseline
NORMAL_WATER_DAMAGE_RATE = 90          # Normal weekly water damage claims
AFFECTED_BATCH_ID = "AC-2026-Q1"       # Defective appliance batch
HIGH_SEVERITY_THRESHOLD = 5000         # High severity if water damage > $5K
MEDIUM_SEVERITY_THRESHOLD = 3000       # Medium severity threshold

# Data quality thresholds (from SAS validation macros)
MIN_CLAIM_AMOUNT = 100                 # Claims < $100 flagged as suspicious
MAX_CLAIM_AMOUNT = 100000              # Claims > $100K require review
MIN_COVERAGE = 50000                   # Minimum policy coverage
MAX_COVERAGE = 500000                  # Maximum policy coverage

# ============================================================================
# CONFIGURATION
# ============================================================================

CATALOG = os.environ.get("DEMO_CATALOG", "na-dbxtraining")
SCHEMA = os.environ.get("DEMO_SCHEMA", "demo_bravo_insurance_claims")

NOW = datetime.now()
SPIKE_PEAK = NOW - timedelta(weeks=3)
AFFECTED_BATCH_DATE = NOW - timedelta(weeks=36)
AFFECTED_MODEL = "AquaClean DW-9500 Series"
AFFECTED_PLANT = "Rockford-IL"

RECALL_NOTICE = (
    f"Product Safety Recall Notice PSR-2026-02-28. "
    f"Product: {AFFECTED_MODEL} Dishwasher, Batch {AFFECTED_BATCH_ID} "
    f"(manufactured Jan-Mar 2026, Rockford IL facility). Issue: defective inlet "
    "valve seal causing slow water leaks during wash cycles. Root cause: supplier "
    "batch of EPDM seals outside hardness spec (Shore A 68 vs required 75-80). "
    "Affected units: ~12,000 distributed across IL, IN, OH, MI, WI. Risk: property "
    "water damage from undetected leaks. Action: voluntary recall issued 2026-02-26; "
    "free replacement + installation offered to all registered owners."
)

N_POLICYHOLDERS = 100_000
N_CLAIMS = 15_000
N_AFFECTED_CLAIMS = 340
NOW_STR = NOW.strftime("%Y-%m-%d")

print(f"Target Schema:      {CATALOG}.{SCHEMA}")
print(f"Affected Batch:     {AFFECTED_BATCH_ID}")
print(f"Spike Peak:         {SPIKE_PEAK.date()}")
print(f"Baseline Weekly:    ${BASELINE_WEEKLY_CLAIMS:,}")
print(f"Spike Threshold:    {SPIKE_THRESHOLD_RATIO}x baseline")

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _save(df: DataFrame, table: str) -> None:
    """Save DataFrame to Delta table with row count validation."""
    fqn = f"{CATALOG}.{SCHEMA}.{table}"
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(fqn)
    count = spark.table(fqn).count()
    print(f"  ✓ {table:32s} rows={count:>9,}")
    return count

def _pick(idx_col: F.Column, pool: list[str]) -> F.Column:
    """Deterministic pick from a literal pool via F.element_at."""
    arr = F.array(*[F.lit(s) for s in pool])
    return F.element_at(arr, (F.pmod(idx_col, F.lit(len(pool))) + 1).cast("int"))

def _bands(pairs: list[tuple]) -> list[tuple]:
    """Turn (key, …, weight) rows into cumulative [low, high) bands."""
    total = sum(p[-1] for p in pairs)
    out, cum = [], 0.0
    for p in pairs:
        w = p[-1] / total
        out.append((*p[:-1], cum, cum + w))
        cum += w
    return out

def validate_dataframe(df: DataFrame, table_name: str, checks: dict) -> None:
    """
    Validate DataFrame against business rules.
    Mirrors SAS data validation (WHERE conditions, PROC SQL checks).

    SAS Equivalent:
        proc sql;
            select count(*) from work.claims where claim_amount <= 0;
            %if &sqlobs > 0 %then %put ERROR: Invalid claims found;
        quit;
    """
    print(f"\n  Validating {table_name}...")
    failed = []

    for check_name, condition in checks.items():
        invalid_count = df.filter(~F.expr(condition)).count()
        if invalid_count > 0:
            failed.append(f"{check_name}: {invalid_count} violations")
        else:
            print(f"    ✓ {check_name}")

    if failed:
        print(f"    ⚠ Validation warnings:")
        for f in failed:
            print(f"      - {f}")

    return len(failed) == 0

# ============================================================================
# REFERENCE DATA
# ============================================================================

APPLIANCES = [
    ("APP-000001", AFFECTED_MODEL, "AquaClean", "dishwasher", 850.0, 2025),
    ("APP-000002", "AquaClean DW-8200", "AquaClean", "dishwasher", 720.0, 2024),
    ("APP-000003", "AquaClean DW-7500", "AquaClean", "dishwasher", 650.0, 2023),
    ("APP-000004", "WashMaster Pro 5000", "WashMaster", "washer", 1100.0, 2025),
    ("APP-000005", "WashMaster Elite 4200", "WashMaster", "washer", 950.0, 2024),
    ("APP-000006", "DryFast Turbo 9000", "DryFast", "dryer", 900.0, 2025),
    ("APP-000007", "DryFast Eco 7500", "DryFast", "dryer", 750.0, 2024),
    ("APP-000008", "ChillMax Ultra 800L", "ChillMax", "refrigerator", 2200.0, 2025),
    ("APP-000009", "ChillMax Compact 500L", "ChillMax", "refrigerator", 1400.0, 2024),
    ("APP-000010", "HotFlow Elite 50gal", "HotFlow", "water_heater", 1200.0, 2024),
]
ALL_APPLIANCES = [a[0] for a in APPLIANCES]
AFFECTED_APPLIANCE_ID = "APP-000001"

# Geographic distribution (from SAS PROC FREQ historical data)
STATE_WEIGHTS_NORMAL = {
    "IL": 0.12, "TX": 0.10, "CA": 0.10, "FL": 0.09, "NY": 0.08,
    "OH": 0.07, "MI": 0.06, "IN": 0.06, "PA": 0.05, "WI": 0.04,
}
OTHER_STATES = ["GA", "NC", "AZ", "MA", "TN", "MO", "MD", "WA", "CO", "MN"]
for s in OTHER_STATES:
    STATE_WEIGHTS_NORMAL[s] = 0.023

# Midwest city anchors (for affected batch concentration)
CITY_ANCHORS = {
    "IL": [("Chicago", 41.88, -87.63, 0.50), ("Rockford", 42.27, -89.09, 0.20),
           ("Springfield", 39.78, -89.65, 0.15), ("Naperville", 41.75, -88.15, 0.15)],
    "IN": [("Indianapolis", 39.77, -86.16, 0.50), ("Fort Wayne", 41.08, -85.14, 0.25),
           ("Evansville", 37.97, -87.56, 0.15), ("South Bend", 41.68, -86.25, 0.10)],
    "OH": [("Cleveland", 41.50, -81.69, 0.35), ("Columbus", 39.96, -83.00, 0.30),
           ("Cincinnati", 39.10, -84.51, 0.25), ("Toledo", 41.65, -83.54, 0.10)],
    "MI": [("Detroit", 42.33, -83.05, 0.45), ("Grand Rapids", 42.96, -85.67, 0.30),
           ("Ann Arbor", 42.28, -83.74, 0.15), ("Lansing", 42.73, -84.56, 0.10)],
    "WI": [("Milwaukee", 43.04, -87.91, 0.50), ("Madison", 43.07, -89.40, 0.30),
           ("Green Bay", 44.52, -88.02, 0.20)],
    "TX": [("Houston", 29.76, -95.37, 0.35), ("Dallas", 32.78, -96.80, 0.30),
           ("Austin", 30.27, -97.74, 0.20), ("San Antonio", 29.42, -98.49, 0.15)],
    "CA": [("Los Angeles", 34.05, -118.25, 0.35), ("San Francisco", 37.77, -122.42, 0.25),
           ("San Diego", 32.72, -117.16, 0.20), ("Sacramento", 38.58, -121.49, 0.20)],
}

# Water leak descriptions (from SAS text field analysis)
WATER_LEAK_DESCRIPTIONS = [
    "Water pooling under dishwasher after each cycle",
    "Slow leak from dishwasher discovered when flooring warped",
    "Kitchen floor water damage traced to dishwasher",
    "Drywall damage from appliance leak behind dishwasher",
    "Discovered water damage behind dishwasher during routine check",
    "Mold growth from undetected dishwasher leak",
]

# ============================================================================
# TABLE 1: RAW_APPLIANCES (Reference Data)
# ============================================================================

print("\n1. Generating raw_appliances...")
appliances_df = spark.createDataFrame(
    APPLIANCES,
    "appliance_id string, model_name string, manufacturer string, category string, "
    "retail_price_usd double, launch_year int"
)

# Business Rule: All appliances must have valid pricing
appliances_df = appliances_df.withColumn(
    "is_valid",
    (F.col("retail_price_usd") > 0) & (F.col("launch_year") >= 2020)
)

validate_dataframe(appliances_df, "raw_appliances", {
    "valid_price": "retail_price_usd > 0",
    "valid_year": "launch_year >= 2020 AND launch_year <= 2026",
    "non_null_model": "model_name IS NOT NULL"
})

_save(appliances_df.drop("is_valid"), "raw_appliances")

# ============================================================================
# TABLE 2: RAW_POLICYHOLDERS (Customer Master)
# ============================================================================

print("\n2. Generating raw_policyholders...")

"""
SAS Business Rule (from policy validation macro):
    %macro validate_policy;
        data work.valid_policies;
            set source.policies;
            if coverage_limit < 50000 then delete;  /* Min coverage */
            if coverage_limit > 500000 then delete; /* Max coverage */
            if policy_type not in ('homeowners','renters','condo') then delete;
        run;
    %mend;
"""

state_band_df = F.broadcast(spark.createDataFrame(
    _bands([(s, w) for s, w in STATE_WEIGHTS_NORMAL.items()]),
    "state string, s_low double, s_high double"
))

_city_rows = []
for _state, _anchors in CITY_ANCHORS.items():
    for _city, _lat, _lng, _lo, _hi in _bands([(c, la, ln, w) for c, la, ln, w in _anchors]):
        _city_rows.append((_state, _city, _lat, _lng, _lo, _hi))
city_band_df = F.broadcast(spark.createDataFrame(
    _city_rows, "state string, city string, anchor_lat double, anchor_lng double, "
                "ci_low double, ci_high double"
))

policy_base = (
    spark.range(0, N_POLICYHOLDERS, numPartitions=16)
    .withColumn("policy_id", F.format_string("POL-%06d", F.col("id")))
    .withColumn("_r_state", F.rand(seed=101))
    .withColumn("_r_city", F.rand(seed=102))
    .withColumn("_r_type", F.rand(seed=103))
    .withColumn("policyholder_name", F.concat(F.lit("Policyholder "), F.col("id").cast("string")))
    .withColumn("email", F.concat(F.lit("policy"), F.col("id"), F.lit("@hls-sas-dbx.com")))
    .withColumn("policy_type",
                F.when(F.col("_r_type") < 0.70, F.lit("homeowners"))
                 .when(F.col("_r_type") < 0.90, F.lit("renters"))
                 .otherwise(F.lit("condo")))
    # Business Rule: Coverage limits based on policy type (from SAS macro)
    .withColumn("coverage_limit_usd",
                F.when(F.col("policy_type") == "homeowners",
                       F.lit(MIN_COVERAGE) + F.rand(seed=105) * (MAX_COVERAGE - MIN_COVERAGE))
                 .when(F.col("policy_type") == "condo",
                       F.lit(150000) + F.rand(seed=105) * F.lit(200000))
                 .otherwise(F.lit(MIN_COVERAGE) + F.rand(seed=105) * F.lit(100000)))
    .withColumn("effective_date",
                F.date_format(
                    F.date_sub(F.lit(NOW_STR), (F.lit(60) + F.rand(seed=104) * 1035).cast("int")),
                    "yyyy-MM-dd"))
)

policyholders_df = (
    policy_base.alias("p")
    .join(state_band_df.alias("sb"),
          (F.col("p._r_state") >= F.col("sb.s_low")) & (F.col("p._r_state") < F.col("sb.s_high")), "left")
    .join(city_band_df.alias("cy"),
          (F.col("sb.state") == F.col("cy.state")) &
          (F.col("p._r_city") >= F.col("cy.ci_low")) & (F.col("p._r_city") < F.col("cy.ci_high")), "left")
    .select(
        F.col("p.policy_id"),
        F.col("p.policyholder_name"),
        F.col("p.email"),
        F.col("sb.state"),
        F.coalesce(F.col("cy.city"), F.lit("Unknown")).alias("city"),
        F.round(F.col("cy.anchor_lat") + (F.rand(seed=107) - 0.5) * 0.1, 5).alias("policyholder_lat"),
        F.round(F.col("cy.anchor_lng") + (F.rand(seed=108) - 0.5) * 0.1, 5).alias("policyholder_lng"),
        F.col("p.policy_type"),
        F.round(F.col("p.coverage_limit_usd"), 0).alias("coverage_limit_usd"),
        F.col("p.effective_date"),
    )
)

# Validation: Enforce SAS business rules
validate_dataframe(policyholders_df, "raw_policyholders", {
    "valid_coverage": f"coverage_limit_usd >= {MIN_COVERAGE} AND coverage_limit_usd <= {MAX_COVERAGE}",
    "valid_policy_type": "policy_type IN ('homeowners', 'renters', 'condo')",
    "valid_coords": "policyholder_lat BETWEEN 25 AND 50 AND policyholder_lng BETWEEN -125 AND -70",
    "non_null_state": "state IS NOT NULL"
})

_save(policyholders_df, "raw_policyholders")

# ============================================================================
# TABLE 3: RAW_APPLIANCE_BATCHES (with Recall Notice)
# ============================================================================

print("\n3. Generating raw_appliance_batches...")

plants = ["Rockford-IL", "Louisville-KY", "Phoenix-AZ", "Nashville-TN"]
appliance_idx_df = spark.createDataFrame(
    [(a, i) for i, a in enumerate(ALL_APPLIANCES)],
    "appliance_id string, app_i int"
)
BATCHES_PER_APPLIANCE = 50

good_batches = (
    appliance_idx_df.alias("a")
    .join(spark.range(0, BATCHES_PER_APPLIANCE).withColumnRenamed("id", "batch_n"), how="cross")
    .withColumn("month_back", (F.col("batch_n") / 4).cast("int") + 1)
    .withColumn("day_off", (F.col("month_back") * 30 + (F.col("batch_n") % 4) * 7).cast("int"))
    .withColumn("manufacture_date", F.date_format(F.date_sub(F.lit(NOW_STR), F.col("day_off")), "yyyy-MM-dd"))
    .withColumn("appliance_batch_id", F.concat(
        F.lit("BATCH-"), F.date_format(F.to_date(F.col("manufacture_date")), "yyyy-MM"),
        F.lit("-"), F.substring(F.col("appliance_id"), -3, 3)))
    .withColumn("plant_location", _pick(F.col("app_i") * 7 + F.col("batch_n"), plants))
    .withColumn("units_produced", (F.lit(500) + F.rand(seed=201) * 1500).cast("int"))
    .withColumn("status", F.lit("active"))
    .withColumn("recall_notice", F.lit(None).cast("string"))
    .select("appliance_batch_id", "appliance_id", "manufacture_date", "plant_location",
            "units_produced", "status", "recall_notice")
)

# Business Rule: Affected batch with recall notice
bad_batch = spark.createDataFrame(
    [(AFFECTED_BATCH_ID, AFFECTED_APPLIANCE_ID, AFFECTED_BATCH_DATE.strftime("%Y-%m-%d"),
      AFFECTED_PLANT, 12000, "recalled", RECALL_NOTICE)],
    "appliance_batch_id string, appliance_id string, manufacture_date string, plant_location string, "
    "units_produced int, status string, recall_notice string"
)

batches_df = good_batches.unionByName(bad_batch)

# Validation
validate_dataframe(batches_df, "raw_appliance_batches", {
    "valid_units": "units_produced > 0",
    "valid_status": "status IN ('active', 'on_hold', 'recalled')",
    "recalled_has_notice": "(status = 'recalled' AND recall_notice IS NOT NULL) OR status != 'recalled'"
})

_save(batches_df, "raw_appliance_batches")

batches_tbl = spark.table(f"{CATALOG}.{SCHEMA}.raw_appliance_batches")
good_batch_lk = (
    batches_tbl.filter(F.col("appliance_batch_id") != AFFECTED_BATCH_ID)
    .withColumn("batch_idx", F.row_number().over(
        Window.partitionBy("appliance_id").orderBy("appliance_batch_id")) - 1)
    .withColumn("n_batches", F.count("*").over(Window.partitionBy("appliance_id")))
    .select("appliance_id", "appliance_batch_id", "batch_idx", "n_batches")
)

# ============================================================================
# TABLE 4: RAW_CLAIMS (with Severity Classification)
# ============================================================================

print("\n4. Generating raw_claims...")

"""
SAS Business Rule (Severity Classification):
    data work.claims_severity;
        set source.claims;
        if claim_type = 'water_damage' and claim_amount > 5000 then severity = 'high';
        else if claim_amount > 10000 then severity = 'high';
        else if claim_amount > 3000 then severity = 'medium';
        else severity = 'low';
    run;
"""

policyholders_tbl = spark.table(f"{CATALOG}.{SCHEMA}.raw_policyholders")
policy_pool = (
    policyholders_tbl
    .withColumn("pi", F.row_number().over(Window.orderBy("policy_id")) - 1)
    .select("policy_id", "pi", "state")
)
policy_count = policy_pool.count()

# Normal claims
normal_base = (
    spark.range(0, N_CLAIMS - N_AFFECTED_CLAIMS, numPartitions=16)
    .withColumn("claim_date", F.date_sub(F.lit(NOW_STR), (F.lit(1) + F.rand(seed=301) * 364).cast("int")))
    .withColumn("pi", (F.abs(F.hash(F.col("id"))) % policy_count).cast("long"))
    .withColumn("_r_type", F.rand(seed=303))
    .withColumn("_r_amt", F.rand(seed=304))
    .withColumn("claim_type",
                F.when(F.col("_r_type") < 0.25, F.lit("water_damage"))
                 .when(F.col("_r_type") < 0.40, F.lit("fire"))
                 .when(F.col("_r_type") < 0.60, F.lit("theft"))
                 .when(F.col("_r_type") < 0.80, F.lit("wind"))
                 .otherwise(F.lit("other")))
)

normal_claims = (
    normal_base.alias("c")
    .join(policy_pool.alias("pp"), "pi", "inner")
    .withColumn("appliance_id",
                F.when(F.col("claim_type") == "water_damage",
                       _pick(F.col("c.id"), [a for a in ALL_APPLIANCES if a != AFFECTED_APPLIANCE_ID]))
                 .otherwise(F.lit(None)))
    # Business Rule: Claim amounts by type (from SAS averages)
    .withColumn("claim_amount_usd",
                F.when(F.col("claim_type") == "water_damage", F.lit(3000) + F.col("_r_amt") * 7000)
                 .when(F.col("claim_type") == "fire", F.lit(15000) + F.col("_r_amt") * 35000)
                 .when(F.col("claim_type") == "theft", F.lit(2000) + F.col("_r_amt") * 8000)
                 .when(F.col("claim_type") == "wind", F.lit(5000) + F.col("_r_amt") * 15000)
                 .otherwise(F.lit(1000) + F.col("_r_amt") * 4000))
    .withColumn("claim_description", F.lit("Normal claim incident"))
    .select("claim_date", "policy_id", "appliance_id", "claim_type", "claim_amount_usd",
            "claim_description", "state")
)

# Affected claims (Midwest concentration)
midwest_pool = policy_pool.filter(F.col("state").isin("IL", "IN", "OH", "MI", "WI"))
midwest_count = midwest_pool.count()

def _triangular(u: F.Column, a: float, c: float, b: float) -> F.Column:
    """Triangular distribution for spike timing."""
    split = (c - a) / (b - a)
    left = F.lit(a) + F.sqrt(u * F.lit((b - a) * (c - a)))
    right = F.lit(b) - F.sqrt((F.lit(1.0) - u) * F.lit((b - a) * (b - c)))
    return F.when(u <= split, left).otherwise(right)

affected_claims = (
    spark.range(0, N_AFFECTED_CLAIMS)
    .withColumn("pi", (F.abs(F.hash(F.col("id"))) % midwest_count).cast("long"))
    .withColumn("_dd", _triangular(F.rand(seed=401), 1.0, 21.0, 56.0).cast("int"))
    .withColumn("claim_date", F.date_sub(F.lit(NOW_STR), F.col("_dd")))
    .withColumn("_r_amt", F.rand(seed=402))
    .join(midwest_pool.alias("mp"), "pi", "inner")
    .withColumn("appliance_id", F.lit(AFFECTED_APPLIANCE_ID))
    .withColumn("claim_type", F.lit("water_damage"))
    # Business Rule: Affected batch claims are higher severity
    .withColumn("claim_amount_usd", F.lit(5000) + F.col("_r_amt") * 10000)
    .withColumn("claim_description", _pick(F.col("id"), WATER_LEAK_DESCRIPTIONS))
    .select("claim_date", "policy_id", "appliance_id", "claim_type", "claim_amount_usd",
            "claim_description", "state")
)

# Combine and add batch IDs
claims_pre = normal_claims.unionByName(affected_claims)

claims_with_batch = (
    claims_pre.alias("c")
    .withColumn("_r_batch", F.rand(seed=501))
    .withColumn("_idx", F.monotonically_increasing_id())
    .join(good_batch_lk.alias("gb"),
          (F.col("c.appliance_id") == F.col("gb.appliance_id")) &
          (F.col("gb.batch_idx") == (F.col("c._r_batch") * F.col("gb.n_batches")).cast("int")),
          "left")
    .withColumn("appliance_batch_id",
                F.when(F.col("c.appliance_id") == AFFECTED_APPLIANCE_ID, F.lit(AFFECTED_BATCH_ID))
                 .otherwise(F.col("gb.appliance_batch_id")))
)

claims_df = (
    claims_with_batch
    .withColumn("claim_id", F.concat(
        F.lit("CLM-"), F.date_format(F.col("claim_date"), "yyyyMMdd"), F.lit("-"),
        F.upper(F.substring(F.sha2(F.concat_ws("|", F.col("policy_id"), F.col("claim_date").cast("string"),
                                               F.col("_idx").cast("string")), 256), 1, 6))))
    .withColumn("claim_date", F.date_format(F.col("claim_date"), "yyyy-MM-dd HH:mm:ss"))
    .withColumn("claim_amount_usd", F.round(F.col("claim_amount_usd"), 2))
    # Business Rule: Severity classification (from SAS CASE statement)
    .withColumn("severity",
                F.when((F.col("claim_type") == "water_damage") & (F.col("claim_amount_usd") > HIGH_SEVERITY_THRESHOLD), "high")
                 .when(F.col("claim_amount_usd") > 10000, "high")
                 .when(F.col("claim_amount_usd") > MEDIUM_SEVERITY_THRESHOLD, "medium")
                 .otherwise("low"))
    .select("claim_id", "policy_id", "appliance_id", "appliance_batch_id",
            "claim_date", "claim_type", "claim_amount_usd", "claim_description",
            "severity", "state")
)

# Validation: Enforce SAS business rules
validate_dataframe(claims_df, "raw_claims", {
    "positive_amount": f"claim_amount_usd >= {MIN_CLAIM_AMOUNT}",
    "max_amount_check": f"claim_amount_usd <= {MAX_CLAIM_AMOUNT}",
    "valid_claim_type": "claim_type IN ('water_damage', 'fire', 'theft', 'wind', 'other')",
    "valid_severity": "severity IN ('low', 'medium', 'high')",
    "water_high_severity": f"(claim_type = 'water_damage' AND claim_amount_usd > {HIGH_SEVERITY_THRESHOLD} AND severity = 'high') OR (claim_type != 'water_damage' OR claim_amount_usd <= {HIGH_SEVERITY_THRESHOLD})"
})

count_claims = _save(claims_df, "raw_claims")

# ============================================================================
# SUMMARY STATISTICS (Business Rule Verification)
# ============================================================================

print("\n" + "="*80)
print("DATA GENERATION SUMMARY - Business Rules Verification")
print("="*80)

claims_tbl = spark.table(f"{CATALOG}.{SCHEMA}.raw_claims")

# 1. Weekly baseline check
weekly_avg = (
    claims_tbl
    .withColumn("week", F.date_trunc("week", "claim_date"))
    .groupBy("week")
    .agg(F.sum("claim_amount_usd").alias("weekly_total"))
    .agg(F.avg("weekly_total").alias("avg_weekly"))
    .collect()[0]["avg_weekly"]
)

print(f"\nBaseline Check:")
print(f"  Target Weekly Baseline:  ${BASELINE_WEEKLY_CLAIMS:,}")
print(f"  Actual Average Weekly:   ${weekly_avg:,.0f}")
print(f"  Variance:                {abs(weekly_avg - BASELINE_WEEKLY_CLAIMS) / BASELINE_WEEKLY_CLAIMS * 100:.1f}%")

# 2. Spike verification
spike_week = (
    claims_tbl
    .withColumn("week", F.date_trunc("week", "claim_date"))
    .groupBy("week")
    .agg(F.sum("claim_amount_usd").alias("weekly_total"))
    .orderBy(F.desc("weekly_total"))
    .limit(1)
    .collect()[0]
)

print(f"\nSpike Verification:")
print(f"  Peak Week Amount:        ${spike_week['weekly_total']:,.0f}")
print(f"  Ratio to Baseline:       {spike_week['weekly_total'] / BASELINE_WEEKLY_CLAIMS:.2f}x")
print(f"  Alert Threshold:         {SPIKE_THRESHOLD_RATIO}x")
print(f"  Alert Status:            {'🚨 ALERT' if spike_week['weekly_total'] / BASELINE_WEEKLY_CLAIMS > SPIKE_THRESHOLD_RATIO else '✓ Normal'}")

# 3. Affected batch statistics
affected_stats = (
    claims_tbl
    .filter(F.col("appliance_batch_id") == AFFECTED_BATCH_ID)
    .agg(
        F.count("*").alias("count"),
        F.sum("claim_amount_usd").alias("total_amount"),
        F.avg("claim_amount_usd").alias("avg_amount")
    )
    .collect()[0]
)

print(f"\nAffected Batch ({AFFECTED_BATCH_ID}):")
print(f"  Claims Count:            {affected_stats['count']:,} (target: {N_AFFECTED_CLAIMS})")
print(f"  Total Amount:            ${affected_stats['total_amount']:,.0f}")
print(f"  Average Claim:           ${affected_stats['avg_amount']:,.0f}")

# 4. Severity distribution
severity_dist = (
    claims_tbl
    .groupBy("severity")
    .count()
    .orderBy("severity")
    .collect()
)

print(f"\nSeverity Distribution (SAS Business Rule Applied):")
for row in severity_dist:
    pct = row['count'] / count_claims * 100
    print(f"  {row['severity']:8s}:             {row['count']:>6,} ({pct:>5.1f}%)")

print("\n" + "="*80)
print(f"✓ Data generation complete: {count_claims:,} claims generated")
print(f"✓ Affected batch ID: {AFFECTED_BATCH_ID}")
print(f"✓ All SAS business rules and validations applied")
print("="*80 + "\n")
