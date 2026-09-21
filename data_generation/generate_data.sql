-- Bravo Insurance Claims — SQL-native synthetic data generation
-- Simple demo: generates raw tables + gold tables directly via SQL

-- Time anchors
SET VAR NOW = CURRENT_TIMESTAMP();
SET VAR SPIKE_PEAK = NOW - INTERVAL 3 WEEKS;
SET VAR AFFECTED_BATCH_DATE = NOW - INTERVAL 36 WEEKS;
SET VAR AFFECTED_BATCH_ID = 'AC-2026-Q1';
SET VAR AFFECTED_MODEL = 'AquaClean DW-9500 Series';
SET VAR RECALL_NOTICE = 'Product Safety Recall Notice PSR-2026-02-28. Product: AquaClean DW-9500 Series Dishwasher, Batch AC-2026-Q1 (manufactured Jan-Mar 2026, Rockford IL facility). Issue: defective inlet valve seal causing slow water leaks during wash cycles. Root cause: supplier batch of EPDM seals outside hardness spec (Shore A 68 vs required 75-80). Affected units: ~12,000 distributed across IL, IN, OH, MI, WI. Risk: property water damage from undetected leaks. Action: voluntary recall issued 2026-02-28; free replacement + installation offered to all registered owners. Estimated field population: 8,500 installed units.';

-- 1. raw_appliances (10 rows — hand-curated)
CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_appliances (
  appliance_id STRING COMMENT 'Appliance PK',
  model_name STRING COMMENT 'Appliance model name',
  manufacturer STRING COMMENT 'Manufacturer name',
  category STRING COMMENT 'Appliance category',
  retail_price_usd DOUBLE COMMENT 'Retail price in USD',
  launch_year INT COMMENT 'Year launched'
) COMMENT 'Appliance catalog';

INSERT INTO na-dbxtraining.demo_bravo_insurance_claims.raw_appliances VALUES
  ('APP-000001', 'AquaClean DW-9500 Series', 'AquaClean', 'dishwasher', 850.0, 2025),
  ('APP-000002', 'AquaClean DW-8200', 'AquaClean', 'dishwasher', 720.0, 2024),
  ('APP-000003', 'AquaClean DW-7500', 'AquaClean', 'dishwasher', 650.0, 2023),
  ('APP-000004', 'WashMaster Pro 5000', 'WashMaster', 'washer', 1100.0, 2025),
  ('APP-000005', 'WashMaster Elite 4200', 'WashMaster', 'washer', 950.0, 2024),
  ('APP-000006', 'DryFast Turbo 9000', 'DryFast', 'dryer', 900.0, 2025),
  ('APP-000007', 'DryFast Eco 7500', 'DryFast', 'dryer', 750.0, 2024),
  ('APP-000008', 'ChillMax Ultra 800L', 'ChillMax', 'refrigerator', 2200.0, 2025),
  ('APP-000009', 'ChillMax Compact 500L', 'ChillMax', 'refrigerator', 1400.0, 2024),
  ('APP-000010', 'HotFlow Elite 50gal', 'HotFlow', 'water_heater', 1200.0, 2024);

-- 2. raw_policyholders (100K rows)
CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_policyholders
COMMENT 'Policyholder profiles'
AS
WITH numbers AS (
  SELECT id FROM RANGE(0, 100000)
),
states AS (
  SELECT
    id,
    CASE
      WHEN rand() < 0.12 THEN 'IL'
      WHEN rand() < 0.22 THEN 'TX'
      WHEN rand() < 0.32 THEN 'CA'
      WHEN rand() < 0.41 THEN 'FL'
      WHEN rand() < 0.49 THEN 'NY'
      WHEN rand() < 0.56 THEN 'OH'
      WHEN rand() < 0.62 THEN 'MI'
      WHEN rand() < 0.68 THEN 'IN'
      WHEN rand() < 0.73 THEN 'PA'
      WHEN rand() < 0.77 THEN 'WI'
      ELSE element_at(array('GA','NC','AZ','MA','TN','MO','MD','WA','CO','MN'),
                      cast(floor(rand() * 10) + 1 as int))
    END AS state
  FROM numbers
)
SELECT
  concat('POL-', lpad(cast(id as string), 6, '0')) AS policy_id,
  concat('Policyholder ', cast(id as string)) AS policyholder_name,
  concat('policyholder', cast(id as string), '@example.com') AS email,
  state,
  CASE
    WHEN state = 'IL' THEN element_at(array('Chicago','Rockford','Springfield','Naperville'),
                                      cast(floor(rand() * 4) + 1 as int))
    WHEN state = 'IN' THEN element_at(array('Indianapolis','Fort Wayne','Evansville','South Bend'),
                                      cast(floor(rand() * 4) + 1 as int))
    WHEN state = 'OH' THEN element_at(array('Cleveland','Columbus','Cincinnati','Toledo'),
                                      cast(floor(rand() * 4) + 1 as int))
    WHEN state = 'MI' THEN element_at(array('Detroit','Grand Rapids','Ann Arbor','Lansing'),
                                      cast(floor(rand() * 4) + 1 as int))
    WHEN state = 'WI' THEN element_at(array('Milwaukee','Madison','Green Bay'),
                                      cast(floor(rand() * 3) + 1 as int))
    WHEN state = 'TX' THEN element_at(array('Houston','Dallas','Austin','San Antonio'),
                                      cast(floor(rand() * 4) + 1 as int))
    ELSE 'City'
  END AS city,
  CASE
    WHEN state = 'IL' THEN 41.88 + (rand() - 0.5) * 0.5
    WHEN state = 'IN' THEN 39.77 + (rand() - 0.5) * 0.5
    WHEN state = 'OH' THEN 41.50 + (rand() - 0.5) * 0.5
    WHEN state = 'MI' THEN 42.33 + (rand() - 0.5) * 0.5
    WHEN state = 'WI' THEN 43.04 + (rand() - 0.5) * 0.5
    WHEN state = 'TX' THEN 29.76 + (rand() - 0.5) * 2.0
    WHEN state = 'CA' THEN 34.05 + (rand() - 0.5) * 3.0
    WHEN state = 'FL' THEN 25.76 + (rand() - 0.5) * 3.0
    WHEN state = 'NY' THEN 40.71 + (rand() - 0.5) * 1.0
    ELSE 39.0 + (rand() - 0.5) * 5.0
  END AS policyholder_lat,
  CASE
    WHEN state = 'IL' THEN -87.63 + (rand() - 0.5) * 0.5
    WHEN state = 'IN' THEN -86.16 + (rand() - 0.5) * 0.5
    WHEN state = 'OH' THEN -81.69 + (rand() - 0.5) * 1.0
    WHEN state = 'MI' THEN -83.05 + (rand() - 0.5) * 0.5
    WHEN state = 'WI' THEN -87.91 + (rand() - 0.5) * 0.5
    WHEN state = 'TX' THEN -95.37 + (rand() - 0.5) * 5.0
    WHEN state = 'CA' THEN -118.25 + (rand() - 0.5) * 5.0
    WHEN state = 'FL' THEN -80.19 + (rand() - 0.5) * 5.0
    WHEN state = 'NY' THEN -74.01 + (rand() - 0.5) * 2.0
    ELSE -90.0 + (rand() - 0.5) * 20.0
  END AS policyholder_lng,
  CASE
    WHEN rand() < 0.70 THEN 'homeowners'
    WHEN rand() < 0.90 THEN 'renters'
    ELSE 'condo'
  END AS policy_type,
  CASE
    WHEN rand() < 0.70 THEN 200000 + floor(rand() * 300000)
    WHEN rand() < 0.90 THEN 50000 + floor(rand() * 100000)
    ELSE 150000 + floor(rand() * 200000)
  END AS coverage_limit_usd,
  date_sub(current_date(), cast(60 + floor(rand() * 1035) as int)) AS effective_date
FROM states;

-- 3. raw_appliance_batches (501 rows — 500 good + 1 bad)
CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_appliance_batches
COMMENT 'Appliance manufacturing batches'
AS
WITH good_batches AS (
  SELECT
    concat('BATCH-', date_format(manufacture_date, 'yyyy-MM'), '-',
           substring(appliance_id, -3, 3)) AS appliance_batch_id,
    appliance_id,
    manufacture_date,
    CASE
      WHEN hash(appliance_id, batch_n) % 4 = 0 THEN 'Rockford-IL'
      WHEN hash(appliance_id, batch_n) % 4 = 1 THEN 'Louisville-KY'
      WHEN hash(appliance_id, batch_n) % 4 = 2 THEN 'Phoenix-AZ'
      ELSE 'Nashville-TN'
    END AS plant_location,
    cast(500 + floor(rand() * 1500) as int) AS units_produced,
    'active' AS status,
    cast(null as string) AS recall_notice
  FROM (
    SELECT
      appliance_id,
      batch_n,
      date_sub(current_date(), cast((batch_n / 4 + 1) * 30 + (batch_n % 4) * 7 as int)) AS manufacture_date
    FROM na-dbxtraining.demo_bravo_insurance_claims.raw_appliances
    CROSS JOIN (SELECT id AS batch_n FROM RANGE(0, 50))
  )
)
SELECT * FROM good_batches
UNION ALL
SELECT
  'AC-2026-Q1' AS appliance_batch_id,
  'APP-000001' AS appliance_id,
  date_sub(current_date(), 252) AS manufacture_date,
  'Rockford-IL' AS plant_location,
  12000 AS units_produced,
  'recalled' AS status,
  'Product Safety Recall Notice PSR-2026-02-28. Product: AquaClean DW-9500 Series Dishwasher, Batch AC-2026-Q1 (manufactured Jan-Mar 2026, Rockford IL facility). Issue: defective inlet valve seal causing slow water leaks during wash cycles. Root cause: supplier batch of EPDM seals outside hardness spec (Shore A 68 vs required 75-80). Affected units: ~12,000 distributed across IL, IN, OH, MI, WI. Risk: property water damage from undetected leaks. Action: voluntary recall issued 2026-02-28; free replacement + installation offered to all registered owners. Estimated field population: 8,500 installed units.' AS recall_notice;

-- 4. raw_claims (15K rows — 14,660 normal + 340 affected)
CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_claims
COMMENT 'Insurance claims'
AS
WITH normal_claims AS (
  SELECT
    concat('CLM-', date_format(claim_date, 'yyyyMMdd'), '-',
           upper(substring(sha2(concat(cast(id as string), cast(rand() as string)), 256), 1, 6))) AS claim_id,
    concat('POL-', lpad(cast(floor(rand() * 100000) as string), 6, '0')) AS policy_id,
    CASE
      WHEN claim_type = 'water_damage' AND rand() < 0.80 THEN
        element_at(array('APP-000002','APP-000003','APP-000004','APP-000010'),
                  cast(floor(rand() * 4) + 1 as int))
      ELSE null
    END AS appliance_id,
    null AS appliance_batch_id,  -- Will be filled via join
    claim_date,
    claim_type,
    CASE
      WHEN claim_type = 'water_damage' THEN 3000 + floor(rand() * 7000)
      WHEN claim_type = 'fire' THEN 15000 + floor(rand() * 35000)
      WHEN claim_type = 'theft' THEN 2000 + floor(rand() * 8000)
      WHEN claim_type = 'wind' THEN 5000 + floor(rand() * 15000)
      ELSE 1000 + floor(rand() * 4000)
    END AS claim_amount_usd,
    CASE
      WHEN claim_type = 'water_damage' THEN 'Water damage from plumbing or appliance'
      WHEN claim_type = 'fire' THEN element_at(array('Kitchen fire from stove','Electrical fire in garage','Candle fire in bedroom'),
                                               cast(floor(rand() * 3) + 1 as int))
      WHEN claim_type = 'theft' THEN element_at(array('Burglary - electronics stolen','Package theft from porch','Vehicle theft from driveway'),
                                                cast(floor(rand() * 3) + 1 as int))
      WHEN claim_type = 'wind' THEN element_at(array('Roof damage from windstorm','Tree fell on house during storm','Fence damaged by high winds'),
                                               cast(floor(rand() * 3) + 1 as int))
      ELSE element_at(array('Plumbing leak in bathroom','HVAC system failure','Garage door damage'),
                     cast(floor(rand() * 3) + 1 as int))
    END AS claim_description,
    state
  FROM (
    SELECT
      id,
      date_sub(current_date(), cast(1 + floor(rand() * 364) as int)) AS claim_date,
      CASE
        WHEN rand() < 0.25 THEN 'water_damage'
        WHEN rand() < 0.40 THEN 'fire'
        WHEN rand() < 0.60 THEN 'theft'
        WHEN rand() < 0.80 THEN 'wind'
        ELSE 'other'
      END AS claim_type,
      element_at(array('IL','TX','CA','FL','NY','OH','MI','IN','PA','WI'),
                cast(floor(rand() * 10) + 1 as int)) AS state
    FROM RANGE(0, 14660)
  )
),
affected_claims AS (
  SELECT
    concat('CLM-', date_format(claim_date, 'yyyyMMdd'), '-',
           upper(substring(sha2(concat(cast(id as string), 'affected'), 256), 1, 6))) AS claim_id,
    concat('POL-', lpad(cast(floor(rand() * 20000) as string), 6, '0')) AS policy_id,
    'APP-000001' AS appliance_id,
    'AC-2026-Q1' AS appliance_batch_id,
    claim_date,
    'water_damage' AS claim_type,
    cast(5000 + floor(rand() * 10000) as double) AS claim_amount_usd,
    element_at(array(
      'Water pooling under dishwasher after each cycle',
      'Slow leak from dishwasher discovered when flooring warped',
      'Kitchen floor water damage traced to dishwasher',
      'Drywall damage from appliance leak behind dishwasher',
      'Discovered water damage behind dishwasher during routine check',
      'Mold growth from undetected dishwasher leak',
      'Cabinet water damage from slow dishwasher leak',
      'Dishwasher inlet valve leaking onto kitchen floor'
    ), cast(floor(rand() * 8) + 1 as int)) AS claim_description,
    element_at(array('IL','IN','OH','MI','WI'), cast(floor(rand() * 5) + 1 as int)) AS state
  FROM (
    SELECT
      id,
      -- Triangular distribution peaking 21 days ago
      date_sub(current_date(),
        cast(CASE
          WHEN rand() < 0.5 THEN 1 + sqrt(rand() * 20 * 55)
          ELSE 56 - sqrt((1 - rand()) * 35 * 56)
        END as int)
      ) AS claim_date
    FROM RANGE(0, 340)
  )
)
SELECT * FROM normal_claims
UNION ALL
SELECT * FROM affected_claims;

-- 5. gold_claims (denormalized fact table)
CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.gold_claims
COMMENT 'Denormalized per-claim fact for dashboard + Genie'
AS
SELECT
  c.claim_id,
  c.policy_id,
  p.policyholder_name,
  cast(c.claim_date as timestamp) AS claim_date,
  c.claim_type,
  c.claim_amount_usd,
  c.claim_description,
  c.state,
  p.city,
  p.policyholder_lat,
  p.policyholder_lng,
  p.policy_type,
  c.appliance_id,
  a.model_name,
  a.manufacturer,
  a.category,
  c.appliance_batch_id,
  b.plant_location,
  CASE WHEN c.appliance_batch_id = 'AC-2026-Q1' THEN true ELSE false END AS is_affected_batch
FROM na-dbxtraining.demo_bravo_insurance_claims.raw_claims c
JOIN na-dbxtraining.demo_bravo_insurance_claims.raw_policyholders p ON c.policy_id = p.policy_id
LEFT JOIN na-dbxtraining.demo_bravo_insurance_claims.raw_appliances a ON c.appliance_id = a.appliance_id
LEFT JOIN na-dbxtraining.demo_bravo_insurance_claims.raw_appliance_batches b
  ON c.appliance_batch_id = b.appliance_batch_id;

-- 6. gold_daily_summary (daily rollup)
CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.gold_daily_summary
COMMENT 'Daily rollup per (date, state, claim_type)'
AS
SELECT
  cast(claim_date as date) AS date,
  state,
  claim_type,
  count(*) AS claim_count,
  sum(claim_amount_usd) AS claim_amount_usd
FROM na-dbxtraining.demo_bravo_insurance_claims.gold_claims
GROUP BY 1, 2, 3;

-- 7. Add constraints for lineage
ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_policyholders ALTER COLUMN policy_id SET NOT NULL;
ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_policyholders ADD CONSTRAINT raw_policyholders_pk PRIMARY KEY (policy_id);

ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_appliances ALTER COLUMN appliance_id SET NOT NULL;
ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_appliances ADD CONSTRAINT raw_appliances_pk PRIMARY KEY (appliance_id);

ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_claims ALTER COLUMN claim_id SET NOT NULL;
ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_claims ADD CONSTRAINT raw_claims_pk PRIMARY KEY (claim_id);
ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_claims ADD CONSTRAINT raw_claims_policy_id_fk
  FOREIGN KEY (policy_id) REFERENCES na-dbxtraining.demo_bravo_insurance_claims.raw_policyholders NOT ENFORCED RELY;

ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.gold_claims ALTER COLUMN claim_id SET NOT NULL;
ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.gold_claims ADD CONSTRAINT gold_claims_pk PRIMARY KEY (claim_id);
ALTER TABLE na-dbxtraining.demo_bravo_insurance_claims.gold_claims ADD CONSTRAINT gold_claims_policy_id_fk
  FOREIGN KEY (policy_id) REFERENCES na-dbxtraining.demo_bravo_insurance_claims.raw_policyholders NOT ENFORCED RELY;

SELECT 'Data generation complete!' AS status;
