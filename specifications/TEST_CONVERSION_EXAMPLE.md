# Test Conversion Example — Ready to Run

## 🎯 Goal
Test the sas2databricks conversion process with a real SAS example.

We'll use: **"Create new column with SELECT statement"** — a DATA step that maps car manufacturers to countries.

---

## 📋 Preparation Checklist

Before starting, ensure:
- [ ] Volume structure created (`/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/`)
- [ ] `sas2databricks` installed: `%pip install sas2databricks`
- [ ] Reference data exists: `sashelp.cars` → `na-dbxtraining.reference_data.cars`

---

## 📝 Step 1: Prepare SAS Input File

**Create:** `/Volumes/.../input/test_car_origin/sas/car_origin.sas`

```sas
/************************************************************************************************
 CREATE NEW COLUMN WITH THE SELECT STATEMENT
     Map car manufacturers to their country of origin.
     Keywords: DATA STEP, SELECT, calculated columns
************************************************************************************************/

data work.cars_orig_country;                                         
    set sashelp.cars(keep=Make Model Origin);                        
    length Origin_Country $25;                                       
    select (Make);                                                   
        when ('Acura', 'Honda', 'Infiniti', 'Isuzu', 'Lexus', 'Mazda', 'Mitsubishi', 'Nissan', 'Scion', 'Subaru', 'Suzuki', 'Toyota') 
            Origin_Country = 'Japan'; 
        when ('Hyundai', 'Kia') 
            Origin_Country = 'South Korea';
        when ('Audi', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Porsche')  
            Origin_Country = 'Germany';
        when ('Jaguar', 'Land Rover', 'MINI') 
            Origin_Country = 'England';
        when ('Saab', 'Volvo') 
            Origin_Country = 'Sweden';
        when ('Buick', 'Cadillac', 'Chevrolet', 'Chrysler', 'Dodge', 'Ford', 'GMC', 'Hummer', 'Jeep', 'Lincoln', 'Mercury', 'Oldsmobile', 'Pontiac', 'Saturn') 
            Origin_Country = 'United States of America';
        otherwise Origin_Country = '';
    end; 
    rename Origin = Origin_Region; 
run;
```

---

## 📝 Step 2: Create Project Manifest

**Create:** `/Volumes/.../input/test_car_origin/config.yaml`

```yaml
project_name: test_car_origin
description: Test SAS SELECT statement conversion to Databricks
sas_version: 9.4
execution_order:
  - car_origin.sas

target:
  pipeline_type: sdp
  medallion_layer: bronze
  schedule: on_demand
  compute: serverless

libname_mapping:
  sashelp:
    catalog: na-dbxtraining
    schema: reference_data
  work:
    catalog: na-dbxtraining
    schema: temp_workspace

conversion:
  model: opus-4.8
  validate_output: true
  create_bundle: true
```

---

## 📝 Step 3: Upload Files to Volume

**Databricks Notebook:**

```python
# Upload SAS file
sas_code = """
data work.cars_orig_country;                                         
    set sashelp.cars(keep=Make Model Origin);                        
    length Origin_Country $25;                                       
    select (Make);                                                   
        when ('Acura', 'Honda', 'Infiniti', 'Isuzu', 'Lexus', 'Mazda', 'Mitsubishi', 'Nissan', 'Scion', 'Subaru', 'Suzuki', 'Toyota') 
            Origin_Country = 'Japan'; 
        when ('Hyundai', 'Kia') 
            Origin_Country = 'South Korea';
        when ('Audi', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Porsche')  
            Origin_Country = 'Germany';
        when ('Jaguar', 'Land Rover', 'MINI') 
            Origin_Country = 'England';
        when ('Saab', 'Volvo') 
            Origin_Country = 'Sweden';
        when ('Buick', 'Cadillac', 'Chevrolet', 'Chrysler', 'Dodge', 'Ford', 'GMC', 'Hummer', 'Jeep', 'Lincoln', 'Mercury', 'Oldsmobile', 'Pontiac', 'Saturn') 
            Origin_Country = 'United States of America';
        otherwise Origin_Country = '';
    end; 
    rename Origin = Origin_Region; 
run;
"""

# Create folder structure
base_path = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input/test_car_origin"
dbutils.fs.mkdirs(f"{base_path}/sas")

# Write SAS file
dbutils.fs.put(f"{base_path}/sas/car_origin.sas", sas_code, overwrite=True)

# Write config
config_yaml = """project_name: test_car_origin
description: Test SAS SELECT statement conversion
sas_version: 9.4
execution_order:
  - car_origin.sas
target:
  pipeline_type: sdp
  medallion_layer: bronze
conversion:
  model: opus-4.8
  validate_output: true
  create_bundle: true
libname_mapping:
  sashelp:
    catalog: na-dbxtraining
    schema: reference_data
  work:
    catalog: na-dbxtraining
    schema: temp_workspace
"""

dbutils.fs.put(f"{base_path}/config.yaml", config_yaml, overwrite=True)

print("✅ Files uploaded successfully")
print(f"📂 Location: {base_path}")
```

---

## 📝 Step 4: Run Conversion

**Databricks Notebook:**

```python
# Install sas2databricks (if not already installed)
%pip install sas2databricks

# Run conversion
from sas2databricks import migrate_project

result = migrate_project(
    sas_project_dir="/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input/test_car_origin",
    output_dir="/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/test_car_origin",
    target="sdp",
    model="opus-4.8",
    bundle=True,
    html_report=True
)

print(result)
```

**Expected output:**
```
✅ Conversion complete!
📊 Summary:
  - Files processed: 1
  - High confidence: 85%
  - Medium confidence: 15%
  - Low confidence: 0%
  
📁 Output location: /Volumes/.../staging/test_car_origin/
📄 Review: CONVERSION_REPORT.html
```

---

## 📝 Step 5: Review Output

**Check what was generated:**

```python
# List output files
display(dbutils.fs.ls("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/test_car_origin"))
```

**Expected structure:**
```
staging/test_car_origin/
├── CONVERSION_REPORT.html        ← Open this first!
├── sdp/
│   └── car_origin.py
├── pyspark/
│   └── car_origin.py
├── validation/
│   └── data_parity_check.py
├── databricks.yml
└── src/
    └── car_origin.py
```

---

## 📝 Step 6: Review Converted Code

**Read the converted SDP pipeline:**

```python
with open("/Volumes/.../staging/test_car_origin/sdp/car_origin.py", "r") as f:
    print(f.read())
```

**Expected output (auto-generated):**

```python
# Auto-generated by sas2databricks
# Source: car_origin.sas
# Timestamp: 2026-09-16
# Conversion confidence: HIGH

from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.table(name="bronze_cars")
@dp.comment("Source data from sashelp.cars. SAS line 2")
def bronze_cars():
    """
    SAS: set sashelp.cars(keep=Make Model Origin);
    """
    return spark.read.table("`na-dbxtraining`.reference_data.cars")\
        .select("Make", "Model", "Origin")

@dp.table(name="cars_orig_country")
@dp.comment("Map car manufacturers to countries using SELECT statement. SAS lines 2-20")
def cars_orig_country():
    """
    Original SAS:
    DATA step with SELECT/WHEN for multi-value mapping
    
    Conversion method: Deterministic (SELECT → F.when)
    Confidence: HIGH
    """
    df = spark.read.table("bronze_cars")
    
    # SAS: length Origin_Country $25;
    # Create Origin_Country column with CASE logic
    df = df.withColumn(
        "Origin_Country",
        F.when(F.col("Make").isin([
            'Acura', 'Honda', 'Infiniti', 'Isuzu', 'Lexus', 
            'Mazda', 'Mitsubishi', 'Nissan', 'Scion', 'Subaru', 
            'Suzuki', 'Toyota'
        ]), "Japan")
        .when(F.col("Make").isin(['Hyundai', 'Kia']), "South Korea")
        .when(F.col("Make").isin([
            'Audi', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Porsche'
        ]), "Germany")
        .when(F.col("Make").isin(['Jaguar', 'Land Rover', 'MINI']), "England")
        .when(F.col("Make").isin(['Saab', 'Volvo']), "Sweden")
        .when(F.col("Make").isin([
            'Buick', 'Cadillac', 'Chevrolet', 'Chrysler', 'Dodge', 
            'Ford', 'GMC', 'Hummer', 'Jeep', 'Lincoln', 'Mercury', 
            'Oldsmobile', 'Pontiac', 'Saturn'
        ]), "United States of America")
        .otherwise("")  # SAS: otherwise Origin_Country = '';
    )
    
    # SAS: rename Origin = Origin_Region;
    df = df.withColumnRenamed("Origin", "Origin_Region")
    
    return df.select("Make", "Model", "Origin_Region", "Origin_Country")
```

---

## 📝 Step 7: Review Conversion Report

**Open in browser:**
```
/Volumes/.../staging/test_car_origin/CONVERSION_REPORT.html
```

**What it shows:**

| Line | SAS Code | Databricks Code | Confidence | Notes |
|------|----------|-----------------|------------|-------|
| 2 | `set sashelp.cars(keep=...)` | `spark.read.table(...).select(...)` | ✅ HIGH | Deterministic |
| 3 | `length Origin_Country $25;` | `withColumn()` with string type | ✅ HIGH | Type inference |
| 4-19 | `select (Make); when (...) ... end;` | `F.when().isin(...)` chain | ✅ HIGH | SELECT → CASE |
| 20 | `otherwise Origin_Country = '';` | `.otherwise("")` | ✅ HIGH | Default value |
| 21 | `rename Origin = Origin_Region;` | `.withColumnRenamed()` | ✅ HIGH | Column rename |

**Result:** ✅ **100% HIGH confidence** — Ready to deploy!

---

## 📝 Step 8: Test the Pipeline

**Create and run the SDP pipeline:**

```python
# Copy converted code to workspace
dbutils.fs.cp(
    "/Volumes/.../staging/test_car_origin/sdp/car_origin.py",
    "/Workspace/Users/your.name@company.com/test_car_origin.py"
)

# Or run directly (if pipeline supports volume paths)
# The converted code is ready to deploy via DAB
```

**Manual test (quick validation):**

```python
# Run the conversion logic directly
from pyspark.sql import functions as F

df = spark.read.table("`na-dbxtraining`.reference_data.cars")\
    .select("Make", "Model", "Origin")

df = df.withColumn(
    "Origin_Country",
    F.when(F.col("Make").isin([
        'Acura', 'Honda', 'Infiniti', 'Isuzu', 'Lexus', 
        'Mazda', 'Mitsubishi', 'Nissan', 'Scion', 'Subaru', 
        'Suzuki', 'Toyota'
    ]), "Japan")
    .when(F.col("Make").isin(['Hyundai', 'Kia']), "South Korea")
    .when(F.col("Make").isin([
        'Audi', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Porsche'
    ]), "Germany")
    .when(F.col("Make").isin(['Jaguar', 'Land Rover', 'MINI']), "England")
    .when(F.col("Make").isin(['Saab', 'Volvo']), "Sweden")
    .when(F.col("Make").isin([
        'Buick', 'Cadillac', 'Chevrolet', 'Chrysler', 'Dodge', 
        'Ford', 'GMC', 'Hummer', 'Jeep', 'Lincoln', 'Mercury', 
        'Oldsmobile', 'Pontiac', 'Saturn'
    ]), "United States of America")
    .otherwise("")
).withColumnRenamed("Origin", "Origin_Region")

display(df)
```

**Expected result:**
```
+----------+-------+--------------+---------------------------+
|Make      |Model  |Origin_Region |Origin_Country             |
+----------+-------+--------------+---------------------------+
|Acura     |MDX    |Asia          |Japan                      |
|Audi      |A4     |Europe        |Germany                    |
|BMW       |X5     |Europe        |Germany                    |
|Chevrolet |Tahoe  |USA           |United States of America   |
|Honda     |Accord |Asia          |Japan                      |
...
```

---

## 📝 Step 9: Run Validation

**Execute the auto-generated validation notebook:**

```python
%run /Volumes/.../staging/test_car_origin/validation/data_parity_check.py
```

**What it checks:**
1. ✅ Row count matches (should be same as source)
2. ✅ No NULL values in Origin_Country where Make exists
3. ✅ Country mappings are correct (spot check 10 random makes)
4. ✅ Schema matches expectations

**Expected output:**
```
✅ Validation PASSED
  - Row count: 428 (matches source)
  - Schema: 4 columns
  - Data quality: 100% valid
  - Spot check: All 10 samples correct
```

---

## 📝 Step 10: Approve & Deploy

**Move to approved folder:**

```python
# If validation passed, move to approved
dbutils.fs.mv(
    "/Volumes/.../staging/test_car_origin",
    "/Volumes/.../approved/test_car_origin"
)
```

**Deploy via DAB:**

```bash
# SSH into Databricks or use VS Code
cd /Volumes/.../approved/test_car_origin
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run test_car_origin_pipeline -t dev
```

---

## ✅ Success Criteria

You know it worked when:
- [ ] CONVERSION_REPORT.html shows ≥95% HIGH confidence
- [ ] Converted Python code is readable and correct
- [ ] Validation notebook passes all checks
- [ ] Manual test query returns expected data
- [ ] Pipeline deploys without errors
- [ ] Pipeline runs successfully in Databricks

---

## 🎯 What This Proves

This test demonstrates:
1. ✅ **Volume-based workflow** works end-to-end
2. ✅ **sas2databricks converter** handles DATA steps correctly
3. ✅ **SELECT/WHEN → F.when().isin()** conversion is accurate
4. ✅ **Validation framework** catches issues
5. ✅ **DAB deployment** streamlines production rollout

---

## 🚀 Next Steps

After successfully testing this example:

**Option A: Test more complex examples**
- PROC FORMAT with ranges
- PROC SQL with joins
- Macros with control flow

**Option B: Convert real SAS code**
- Load your actual SAS programs
- Follow same workflow
- Scale to production

**Option C: Fix the current claims pipeline**
- Apply what we learned
- Fix backtick issue
- Complete deployment

**What would you like to do next?**
