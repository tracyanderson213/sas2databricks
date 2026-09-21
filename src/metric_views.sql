-- ============================================================================
-- HLS SAS DBX Migration — Metric Views
-- Replaces: SAS macro variables, stored business rules, reusable calculations
-- ============================================================================

-- Metric View 1: Claims Performance Metrics
-- Replaces SAS macro: %claims_metrics with reusable KPI definitions
CREATE OR REPLACE METRIC VIEW na-dbxtraining.hls_sas_dbx_claims.mv_claims_performance
COMMENT 'Governed claims KPIs. Replaces SAS %claims_metrics macro variables.'
AS
SELECT
  date,
  state,
  claim_type,
  -- Base measures (from SAS macro definitions)
  MEASURE(
    SUM(claim_amount_usd),
    'Total Claims $',
    'Sum of all claim amounts in USD',
    'currency'
  ) AS total_claims_usd,

  MEASURE(
    COUNT(*),
    'Claim Count',
    'Number of claims filed',
    'number'
  ) AS claim_count,

  MEASURE(
    AVG(claim_amount_usd),
    'Avg Claim Amount',
    'Average claim payout amount',
    'currency'
  ) AS avg_claim_amount,

  -- Derived metrics (from SAS calculations)
  MEASURE(
    SUM(claim_amount_usd) / 2500000,
    'Baseline Ratio',
    'Claims amount as ratio of $2.5M baseline (from SAS %let baseline_claims)',
    'ratio'
  ) AS baseline_ratio,

  MEASURE(
    CASE
      WHEN SUM(claim_amount_usd) / 2500000 > 1.25 THEN 1
      ELSE 0
    END,
    'Spike Alert',
    'Binary alert when claims exceed baseline by 25% (from SAS %let spike_threshold)',
    'number'
  ) AS spike_alert

FROM na-dbxtraining.hls_sas_dbx_claims.gold_daily_summary
GROUP BY date, state, claim_type;

-- Metric View 2: Affected Batch Metrics
-- Replaces SAS stored process: %batch_metrics
CREATE OR REPLACE METRIC VIEW na-dbxtraining.hls_sas_dbx_claims.mv_affected_batch_metrics
COMMENT 'Metrics specific to affected appliance batch AC-2026-Q1. Replaces SAS %batch_metrics stored process.'
AS
SELECT
  state,
  model_name,
  -- Affected batch measures
  MEASURE(
    SUM(CASE WHEN is_affected_batch THEN 1 ELSE 0 END),
    'Affected Claims',
    'Claims from defective batch AC-2026-Q1',
    'number'
  ) AS affected_claim_count,

  MEASURE(
    SUM(CASE WHEN is_affected_batch THEN claim_amount_usd ELSE 0 END),
    'Affected Claims $',
    'Total payout for affected batch',
    'currency'
  ) AS affected_claims_usd,

  MEASURE(
    SUM(CASE WHEN is_affected_batch THEN claim_amount_usd ELSE 0 END) / SUM(claim_amount_usd),
    'Affected Pct',
    'Percentage of total claims from affected batch',
    'percent'
  ) AS affected_pct,

  -- Comparison metrics
  MEASURE(
    SUM(CASE WHEN NOT is_affected_batch THEN 1 ELSE 0 END),
    'Normal Claims',
    'Claims from normal batches',
    'number'
  ) AS normal_claim_count,

  MEASURE(
    AVG(CASE WHEN is_affected_batch THEN claim_amount_usd END),
    'Avg Affected Claim',
    'Average payout for affected batch claims',
    'currency'
  ) AS avg_affected_claim

FROM na-dbxtraining.hls_sas_dbx_claims.gold_claims
GROUP BY state, model_name;

-- Example Queries Using Metric Views
-- These replace SAS PROC SQL queries with governed metrics

-- Query 1: Weekly trend with baseline comparison (replaces SAS weekly_trend.sas)
/*
SAS equivalent:
proc sql;
  select
    intnx('week', date, 0) as week,
    sum(claim_amount) as total,
    calculated total / &baseline as ratio
  from analytics.claims
  group by calculated week;
quit;

Databricks with Metric View:
*/
SELECT
  DATE_TRUNC('week', date) AS week,
  MEASURE(total_claims_usd) AS total_claims,
  MEASURE(baseline_ratio) AS vs_baseline,
  MEASURE(spike_alert) AS alert_flag
FROM na-dbxtraining.hls_sas_dbx_claims.mv_claims_performance
GROUP BY week
ORDER BY week;

-- Query 2: Affected batch analysis by state (replaces SAS batch_summary.sas)
/*
SAS equivalent:
%macro batch_summary;
  proc means data=analytics.claims;
    where batch_id = "&affected_batch";
    class state;
    var claim_amount;
    output out=work.batch_summary sum=total_claims;
  run;
%mend;

Databricks with Metric View:
*/
SELECT
  state,
  MEASURE(affected_claim_count) AS affected_claims,
  MEASURE(affected_claims_usd) AS affected_amount,
  MEASURE(affected_pct) AS pct_of_total
FROM na-dbxtraining.hls_sas_dbx_claims.mv_affected_batch_metrics
WHERE MEASURE(affected_claim_count) > 0
ORDER BY MEASURE(affected_claims_usd) DESC;
