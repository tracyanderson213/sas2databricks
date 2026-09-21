# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Upload Sample SAS Code
# MAGIC
# MAGIC **Purpose:** Upload real SAS examples to test the conversion process
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Run `01_setup_volumes.py` first
# MAGIC - ✅ Volume structure created
# MAGIC
# MAGIC **What this does:**
# MAGIC - Copies 3 sample SAS programs to input volume
# MAGIC - Creates config.yaml for each project
# MAGIC - Sets up test data references
# MAGIC
# MAGIC **Samples included:**
# MAGIC 1. **Simple SQL** - PROC SQL select (easy, HIGH confidence)
# MAGIC 2. **Format + DATA** - PROC FORMAT + DATA step (medium, HIGH confidence)
# MAGIC 3. **Business Logic** - DATA step with SELECT/WHEN (medium, HIGH confidence)
# MAGIC
# MAGIC **After this notebook:** Run `03_test_conversion.py`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample 1: Simple PROC SQL

# COMMAND ----------

# Create project folder
base_path = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input"
project_name = "test_simple_sql"
project_path = f"{base_path}/{project_name}"

dbutils.fs.mkdirs(f"{project_path}/sas")
print(f"✅ Created: {project_path}")

# SAS code - simple SELECT
sas_code_sql = """/* Simple PROC SQL Example
   Keywords: PROC SQL, SELECT
   Confidence: HIGH (deterministic conversion)
*/

proc sql;
    select Name, Age, Height, Weight
    from sashelp.class
    where Age >= 14
    order by Age desc;
quit;
"""

# Write SAS file
dbutils.fs.put(f"{project_path}/sas/simple_select.sas", sas_code_sql, overwrite=True)
print(f"✅ Uploaded: simple_select.sas")

# Create config.yaml
config_sql = """project_name: test_simple_sql
description: Simple PROC SQL select statement
sas_version: 9.4
execution_order:
  - simple_select.sas
target:
  pipeline_type: sdp
  medallion_layer: bronze
  compute: serverless
libname_mapping:
  sashelp:
    catalog: na-dbxtraining
    schema: reference_data
conversion:
  model: opus-4.8
  validate_output: true
  create_bundle: true
"""

dbutils.fs.put(f"{project_path}/config.yaml", config_sql, overwrite=True)
print(f"✅ Created: config.yaml")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample 2: PROC FORMAT + DATA Step

# COMMAND ----------

project_name = "test_format_data"
project_path = f"{base_path}/{project_name}"

dbutils.fs.mkdirs(f"{project_path}/sas")

# SAS code - format + data step
sas_code_format = """/* PROC FORMAT + DATA Step Example
   Keywords: PROC FORMAT, DATA STEP, FORMAT
   Confidence: HIGH (deterministic conversion)
*/

/* Define formats */
proc format;
    value cyl
    . = "N/A"
    4 = "4 Cylinders - Compact"
    6 = "6 Cylinders - Midsize"
    8 = "8 Cylinders - Performance"
    ;

    value msrp
    low-30000 = "Budget"
    30001-50000 = "Mid-Range"
    50001-100000 = "Premium"
    100001-high = "Luxury"
    ;
run;

/* Apply formats */
data work.cars_formatted;
    set sashelp.cars;
    keep Make Model MSRP Cylinders;
    format Cylinders cyl. MSRP msrp.;
run;
"""

dbutils.fs.put(f"{project_path}/sas/format_cars.sas", sas_code_format, overwrite=True)
print(f"✅ Uploaded: format_cars.sas")

config_format = """project_name: test_format_data
description: PROC FORMAT with DATA step application
sas_version: 9.4
execution_order:
  - format_cars.sas
target:
  pipeline_type: sdp
  medallion_layer: bronze
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
"""

dbutils.fs.put(f"{project_path}/config.yaml", config_format, overwrite=True)
print(f"✅ Created: config.yaml")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample 3: DATA Step with SELECT/WHEN

# COMMAND ----------

project_name = "test_select_when"
project_path = f"{base_path}/{project_name}"

dbutils.fs.mkdirs(f"{project_path}/sas")

# SAS code - SELECT/WHEN for business logic
sas_code_select = """/* DATA Step with SELECT/WHEN
   Keywords: DATA STEP, SELECT, WHEN, business logic
   Confidence: HIGH (deterministic conversion)

   Business rule: Map car manufacturers to countries
*/

data work.cars_with_country;
    set sashelp.cars(keep=Make Model Origin);
    length Origin_Country $25;

    /* Map manufacturer to country */
    select (Make);
        when ('Acura', 'Honda', 'Infiniti', 'Lexus', 'Mazda',
              'Mitsubishi', 'Nissan', 'Subaru', 'Toyota')
            Origin_Country = 'Japan';
        when ('Hyundai', 'Kia')
            Origin_Country = 'South Korea';
        when ('Audi', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Porsche')
            Origin_Country = 'Germany';
        when ('Jaguar', 'Land Rover', 'MINI')
            Origin_Country = 'England';
        when ('Saab', 'Volvo')
            Origin_Country = 'Sweden';
        when ('Buick', 'Cadillac', 'Chevrolet', 'Chrysler', 'Dodge',
              'Ford', 'GMC', 'Jeep', 'Lincoln', 'Pontiac')
            Origin_Country = 'United States';
        otherwise
            Origin_Country = '';
    end;

    rename Origin = Origin_Region;
run;
"""

dbutils.fs.put(f"{project_path}/sas/car_origin.sas", sas_code_select, overwrite=True)
print(f"✅ Uploaded: car_origin.sas")

config_select = """project_name: test_select_when
description: DATA step with SELECT/WHEN for business logic
sas_version: 9.4
execution_order:
  - car_origin.sas
target:
  pipeline_type: sdp
  medallion_layer: bronze
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
"""

dbutils.fs.put(f"{project_path}/config.yaml", config_select, overwrite=True)
print(f"✅ Created: config.yaml")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("="*80)
print("📤 SAMPLE SAS CODE UPLOADED SUCCESSFULLY!")
print("="*80)
print()
print("📁 Projects created:")
print()
print("1️⃣  test_simple_sql/")
print("    ├── sas/simple_select.sas")
print("    └── config.yaml")
print("    Type: PROC SQL")
print("    Complexity: Easy")
print("    Expected confidence: 100% HIGH")
print()
print("2️⃣  test_format_data/")
print("    ├── sas/format_cars.sas")
print("    └── config.yaml")
print("    Type: PROC FORMAT + DATA step")
print("    Complexity: Medium")
print("    Expected confidence: 100% HIGH")
print()
print("3️⃣  test_select_when/")
print("    ├── sas/car_origin.sas")
print("    └── config.yaml")
print("    Type: DATA step with SELECT/WHEN")
print("    Complexity: Medium")
print("    Expected confidence: 100% HIGH")
print()
print("="*80)
print()
print("📋 Next steps:")
print("  1. ✅ COMPLETED: Sample SAS code uploaded")
print("  2. ➡️  NEXT: Run notebook 03_test_conversion.py")
print()
print("="*80)

# COMMAND ----------

# Verify uploads
print("\n📂 Uploaded files:")
print("="*80)

projects = ["test_simple_sql", "test_format_data", "test_select_when"]
for project in projects:
    print(f"\n{project}:")
    try:
        files = dbutils.fs.ls(f"{base_path}/{project}/sas")
        for file in files:
            print(f"  ✅ {file.name}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
