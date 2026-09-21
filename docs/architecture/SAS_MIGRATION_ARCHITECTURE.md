# SAS to Databricks Migration Architecture

**Separation of Concerns: Ingestion vs. Transformation**

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SOURCE SYSTEMS                              │
├─────────────────────────────────────────────────────────────────────┤
│  • SQL Server (Adventure Works)                                     │
│  • Oracle (Enterprise Data Warehouse)                               │
│  • CSV Files (Partner Feeds)                                        │
│  • APIs (Real-time data)                                            │
│  • SAS Datasets (Legacy files)                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER (NOT SAS)                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Lakeflow Connect │  │   Auto Loader    │  │   ADF/Fivetran  │  │
│  │                  │  │                  │  │                 │  │
│  │ • SQL Server CDC │  │ • CSV ingestion  │  │ • Oracle sync   │  │
│  │ • MySQL CDC      │  │ • JSON parsing   │  │ • API polling   │  │
│  │ • PostgreSQL     │  │ • Parquet files  │  │ • SaaS apps     │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │           BRONZE LAYER (Delta Tables)                         │ │
│  │  • Raw data with audit columns                                │ │
│  │  • Schema: sas_{developer_id}_bronze                          │ │
│  │  • Delta format (ACID, CDC, time travel)                      │ │
│  │  • Examples: customer, salesorderheader, claims               │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              TRANSFORMATION LAYER (CONVERTED SAS)                   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │    Spark Declarative Pipelines (SDP)                          │ │
│  │    • Python code converted from SAS                           │ │
│  │    • Business logic: MERGE, RETAIN, IF/THEN/ELSE             │ │
│  │    • Reads FROM Bronze                                        │ │
│  │    • Writes TO Silver/Gold                                    │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │           SILVER LAYER (Views/Tables)                         │ │
│  │  • Business logic transformations                             │ │
│  │  • Schema: sas_{developer_id}_silver                          │ │
│  │  • Primarily views (storage optimization)                     │ │
│  │  • Examples: customer_enriched, claims_adjudicated            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │           GOLD LAYER (Analytics Tables)                       │ │
│  │  • Aggregated metrics and KPIs                                │ │
│  │  • Schema: sas_{developer_id}_gold                            │ │
│  │  • Materialized tables (fast queries)                         │ │
│  │  • Examples: customer_summary, sales_statistics               │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     CONSUMPTION LAYER                               │
├─────────────────────────────────────────────────────────────────────┤
│  • AI/BI Dashboards                                                 │
│  • Genie Spaces (Natural Language Analytics)                        │
│  • Power BI / Tableau                                               │
│  • ML Models                                                        │
│  • APIs / Applications                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Principles

### 1. **Separation of Concerns**

**Ingestion ≠ Transformation**

| Layer | Responsibility | Technology |
|-------|---------------|------------|
| **Ingestion** | Get data into Databricks | Lakeflow Connect, Auto Loader, ADF |
| **Transformation** | Apply business logic | SDP (Converted SAS code) |

**Why separate?**
- ✅ **Single responsibility** — Ingestion does extraction, SDP does logic
- ✅ **Technology choice** — Best tool for each job
- ✅ **Reusability** — Bronze data can feed multiple pipelines
- ✅ **Testing** — Test ingestion and transformation independently
- ✅ **Scaling** — Scale ingestion and transformation separately

### 2. **SDP Assumes Bronze Exists**

**The converted SAS code:**
- ✅ Reads FROM Bronze tables (assumes they exist)
- ✅ Applies business logic (SAS transformations)
- ✅ Writes TO Silver/Gold

**The converted SAS code does NOT:**
- ❌ Connect directly to SQL Server
- ❌ Parse CSV files
- ❌ Call APIs
- ❌ Handle ingestion

**Why?** Because production SAS works the same way:
```sas
/* SAS reads from staged data, not live sources */
LIBNAME staging "/data/landing/";

DATA work.customers;
    SET staging.customer;  /* Assumes data is landed */
RUN;
```

### 3. **Ingestion Layer Owns Bronze**

**Responsibilities:**
- Extract from source systems
- Handle schema evolution
- Manage CDC (Change Data Capture)
- Write to Delta format
- Add audit metadata

**Technologies:**

| Source | Best Ingestion Tool |
|--------|---------------------|
| SQL Server / MySQL / PostgreSQL | **Lakeflow Connect** (CDC-ready) |
| CSV / JSON / Parquet files | **Auto Loader** (incremental, schema inference) |
| Oracle / SAP / Salesforce | **ADF, Fivetran, or Airbyte** |
| APIs / Webhooks | **Custom Python + Jobs** |
| SAS datasets (legacy) | **Auto Loader** (read as binary, convert) |

---

## Adventure Works Example

### **Current Architecture:**

```
┌──────────────────────────────────────────────────────────────────┐
│ SQL Server                                                       │
│  └─ Sales.Customer (19,820 rows)                                │
│  └─ Sales.SalesOrderHeader (31,465 rows)                        │
└──────────────────────────────────────────────────────────────────┘
                    │
                    │ Lakeflow Connect
                    │ (Ingestion Layer)
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│ Bronze Layer (Delta Tables)                                      │
│  └─ sas_tanderson_bronze.customer (Delta)                       │
│  └─ sas_tanderson_bronze.salesorderheader (Delta)               │
└──────────────────────────────────────────────────────────────────┘
                    │
                    │ SDP (sales_summary.sas converted)
                    │ (Transformation Layer)
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│ Silver Layer (Views)                                             │
│  └─ sas_tanderson_silver.customers (filtered, enriched)         │
│  └─ sas_tanderson_silver.orders (calculated fields)             │
│  └─ sas_tanderson_silver.customer_metrics (joined, aggregated)  │
└──────────────────────────────────────────────────────────────────┘
                    │
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│ Gold Layer (Tables)                                              │
│  └─ sas_tanderson_gold.customer_summary (analytics-ready)       │
│  └─ sas_tanderson_gold.sales_statistics (KPIs)                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Migration Patterns

### **Pattern 1: Database Sources**

```
Source: SQL Server, Oracle, MySQL, PostgreSQL

Step 1: Create Lakeflow Connect pipeline
  databricks bundle run -t dev adventureworks_ingestion

Step 2: Verify Bronze tables exist
  SELECT COUNT(*) FROM sas_tanderson_bronze.customer;

Step 3: Run converted SAS pipeline
  databricks bundle run -t dev sales_summary_pipeline
```

### **Pattern 2: File Sources**

```
Source: CSV, JSON, Parquet files in cloud storage

Step 1: Set up Auto Loader
  @dlt.table(name="bronze.customer")
  def bronze_customer():
      return spark.readStream \
          .format("cloudFiles") \
          .option("cloudFiles.format", "csv") \
          .option("cloudFiles.schemaLocation", "/schema/customer") \
          .load("/raw/customer/*.csv")

Step 2: Run converted SAS pipeline
  (Reads from bronze.customer)
```

### **Pattern 3: External ETL (ADF, Fivetran)**

```
Source: Various (Oracle, SAP, Salesforce)

Step 1: ADF/Fivetran writes to Bronze
  Destination: bronze.customer (Delta table)

Step 2: Run converted SAS pipeline
  (Reads from bronze.customer)
```

---

## What the Converter Handles

### **✅ In Scope (Transformation Layer):**
- SAS business logic → Python/SQL
- MERGE → JOIN conversion
- RETAIN → Window functions
- IF/THEN/ELSE → CASE statements
- PROC SQL → Spark SQL
- Medallion architecture (Bronze → Silver → Gold)
- Data quality expectations

### **❌ Out of Scope (Ingestion Layer):**
- Connecting to source databases
- Parsing CSV/JSON files
- CDC setup
- Schema evolution handling
- Network connectivity
- Authentication/credentials

**Why?** These are handled by specialized ingestion tools (Lakeflow Connect, Auto Loader, ADF).

---

## Deployment Architecture

### **Component Separation:**

```
1. Ingestion Pipeline (Lakeflow Connect)
   └─ Config: lakeflow_connect_adventureworks.yml
   └─ Schedule: Hourly/Daily
   └─ Outputs: Bronze tables

2. Transformation Pipeline (Converted SAS)
   └─ Config: sales_summary_pipeline.yml
   └─ Schedule: After ingestion completes
   └─ Inputs: Bronze tables
   └─ Outputs: Silver/Gold tables

3. Orchestration (Optional)
   └─ Databricks Jobs or ADF
   └─ Dependency: Ingestion → Transformation
```

### **Scheduling:**

```yaml
# Option 1: Sequential Jobs
jobs:
  ingest_then_transform:
    tasks:
      - task_key: ingest
        pipeline_task:
          pipeline_id: ${resources.pipelines.adventureworks_ingestion.id}
      
      - task_key: transform
        depends_on:
          - task_key: ingest
        pipeline_task:
          pipeline_id: ${resources.pipelines.sales_summary.id}

# Option 2: Separate Schedules
# - Ingestion: Runs hourly (8am-8pm)
# - Transformation: Runs 15 minutes after ingestion completes
```

---

## Best Practices

### ✅ **DO:**
1. **Separate ingestion from transformation**
   - Different technologies
   - Different schedules
   - Different owners (Data Engineering vs. Analytics)

2. **Use Bronze as the contract**
   - Well-defined schemas
   - Stable table names
   - Documented audit columns

3. **Let ingestion tools do what they do best**
   - Lakeflow Connect for databases (CDC, schema evolution)
   - Auto Loader for files (incremental, schema inference)
   - Don't reinvent in SAS/SDP

4. **Test independently**
   - Test ingestion: "Does data land correctly?"
   - Test transformation: "Does business logic work?"

### ❌ **DON'T:**
1. **Mix ingestion and transformation in one pipeline**
   - Makes both harder to test
   - Couples unrelated concerns
   - Reduces reusability

2. **Put database connections in SAS/SDP code**
   - Violates separation of concerns
   - Hard to manage credentials
   - Tight coupling to source systems

3. **Assume SAS converter handles ingestion**
   - It doesn't (by design)
   - Ingestion is a separate layer

---

## Summary

**Key Principle:**
```
Ingestion (Lakeflow/Auto Loader/ADF) → Bronze → SDP (Converted SAS) → Silver/Gold
```

**Responsibilities:**
- **Ingestion Layer:** Get data into Bronze (Delta tables)
- **Transformation Layer:** Apply SAS business logic to create Silver/Gold

**For SAS Migration:**
1. Set up ingestion FIRST (Lakeflow Connect, Auto Loader, or ADF)
2. Verify Bronze tables exist with data
3. THEN run converted SAS code (SDP)
4. SDP reads FROM Bronze, writes TO Silver/Gold

**This is the correct enterprise architecture for production SAS migrations.** 🎯
