# How to Check SQL Server Tables

**Quick guide to see what's available in your Adventure Works database.**

---

## TL;DR

**Run the notebook to see all available tables:**

1. Upload `check_adventureworks_tables_notebook.py` to Databricks workspace
2. Run all cells
3. It will tell you which schema to use (Sales vs SalesLT)

---

## Three Ways to Check

### Method 1: Databricks Notebook (Recommended) ⭐

**File:** `check_adventureworks_tables_notebook.py`

**Steps:**
1. **Upload notebook to Databricks:**
   ```bash
   databricks workspace import \
     check_adventureworks_tables_notebook.py \
     /Users/your.email@domain.com/check_adventureworks_tables \
     --language PYTHON
   ```

2. **Open notebook in Databricks UI**
   - Workflows → Notebooks → check_adventureworks_tables

3. **Run all cells**
   - It automatically:
     - Gets password from Key Vault
     - Connects to SQL Server
     - Lists all tables
     - Finds Customer & SalesOrderHeader tables
     - Shows row counts
     - Tells you which schema to use

**Output you'll see:**
```
✅ Adventure Works FULL version detected!

Available tables:
  • Sales.Customer (19,185 rows)
  • Sales.SalesOrderHeader (31,465 rows)

🎯 Recommended Action:
  1. Use schema: Sales
  2. Ingest: Sales.Customer, Sales.SalesOrderHeader
  3. Run sales_summary.sas
```

---

### Method 2: SQL Editor

**Use Databricks SQL Editor with external connection:**

1. **Create SQL connection to Adventure Works** (if not exists)
   - Catalog → External Data → Connections → Create
   - Type: SQL Server
   - Use your credentials

2. **Run this query:**
   ```sql
   -- List all tables
   SELECT TABLE_SCHEMA, TABLE_NAME
   FROM INFORMATION_SCHEMA.TABLES
   WHERE TABLE_TYPE = 'BASE TABLE'
   ORDER BY TABLE_SCHEMA, TABLE_NAME;

   -- Find Customer & SalesOrder tables
   SELECT TABLE_SCHEMA, TABLE_NAME
   FROM INFORMATION_SCHEMA.TABLES
   WHERE TABLE_TYPE = 'BASE TABLE'
     AND (TABLE_NAME LIKE '%Customer%' OR TABLE_NAME LIKE '%SalesOrder%')
   ORDER BY TABLE_SCHEMA, TABLE_NAME;
   ```

---

### Method 3: Python Script (Reference Only)

**File:** `check_adventureworks_tables.py`

**Note:** This script shows you the queries but requires running in a notebook for JDBC access.

**To use:**
```bash
python check_adventureworks_tables.py
```

**Output:** SQL queries you can copy/paste into a notebook

---

## What You're Looking For

### Scenario 1: Sales Schema (Full Adventure Works)

**If you see:**
- `Sales.Customer`
- `Sales.SalesOrderHeader`

**Then:**
✅ You have the FULL Adventure Works database  
✅ Use `Sales` schema in Lakeflow Connect config  
✅ Expected data: ~19K customers, ~31K orders  

---

### Scenario 2: SalesLT Schema (AdventureWorksLT)

**If you see:**
- `SalesLT.Customer`
- `SalesLT.SalesOrderHeader`

**Then:**
✅ You have AdventureWorksLT (light version)  
✅ Use `SalesLT` schema in Lakeflow Connect config  
✅ Expected data: ~800 customers, ~32K orders  

**Both versions work great for the demo!**

---

### Scenario 3: Neither Schema Has Customer/SalesOrder

**If you DON'T see Customer or SalesOrderHeader:**

**Option A: Use existing tables**
- You already have: Production.Product, Sales.SalesTerritory, HumanResources.Department
- Create a different SAS file using these tables
- Still proves the same architecture!

**Option B: Check if different table names exist**
- Some Adventure Works versions use different naming
- Look for tables with "Customer" or "Order" in the name

---

## Expected Results

### Full Adventure Works (Sales schema)

| Schema | Table | Approx Rows |
|--------|-------|-------------|
| Sales | Customer | 19,185 |
| Sales | SalesOrderHeader | 31,465 |
| Sales | SalesOrderDetail | 121,317 |
| Sales | SalesTerritory | 10 |
| Production | Product | 504 |
| HumanResources | Department | 16 |

### AdventureWorksLT (SalesLT schema)

| Schema | Table | Approx Rows |
|--------|-------|-------------|
| SalesLT | Customer | 847 |
| SalesLT | SalesOrderHeader | 32,166 |
| SalesLT | SalesOrderDetail | 542 |
| SalesLT | Product | 295 |
| SalesLT | ProductCategory | 41 |

---

## After Running the Check

### If Customer & SalesOrderHeader Exist

**Update Lakeflow Connect config:**

```yaml
# In lakeflow_connect_adventureworks.yml
# Change source_schema to match what you found:

objects:
  - table:
      source_schema: "Sales"        # ← or "SalesLT"
      source_table: "Customer"
      
  - table:
      source_schema: "Sales"        # ← or "SalesLT"
      source_table: "SalesOrderHeader"
```

**Then proceed with Option 2:**
1. Create UC connection
2. Add Lakeflow Connect pipeline
3. Deploy and run ingestion
4. Use sales_summary.sas

---

### If Tables Don't Exist

**No problem! Use existing tables:**

1. You already have:
   - `bronze_aw_products` (from Production.Product)
   - `bronze_aw_territories` (from Sales.SalesTerritory)
   - `bronze_aw_departments` (from HumanResources.Department)

2. Create a simple SAS file using these tables

3. Still proves the full architecture (SQL Server → Bronze → Gold)

---

## Troubleshooting

### "Cannot connect to SQL Server"

**Check:**
- Password is in Key Vault: `dbx-ss-kv-natraining-2/natraining-sql-adventureworks-password`
- Server is accessible: `sqldbdbxtraining.database.windows.net`
- Network connectivity (VPC peering, firewall rules)

### "Table not found"

**Possible causes:**
- Schema name is case-sensitive (use exact case)
- Table might be in a different schema
- Run the notebook to see ALL available tables

### "Permission denied"

**Check SQL user permissions:**
```sql
-- In SQL Server, grant permissions:
GRANT SELECT ON SCHEMA::Sales TO sqladministrator;
GRANT SELECT ON SCHEMA::SalesLT TO sqladministrator;
```

---

## Quick Reference

**Your connection details:**
```
Server: sqldbdbxtraining.database.windows.net
Database: sqldb-adventureworks
User: sqladministrator@sqldbdbxtraining
Password: In Key Vault (dbx-ss-kv-natraining-2)
```

**Already ingested:**
- Production.Product → bronze_aw_products
- Sales.SalesTerritory → bronze_aw_territories
- HumanResources.Department → bronze_aw_departments

**Need to ingest (for sales_summary.sas):**
- Sales.Customer (or SalesLT.Customer)
- Sales.SalesOrderHeader (or SalesLT.SalesOrderHeader)

---

## Next Steps

1. **Run the notebook** → `check_adventureworks_tables_notebook.py`
2. **Note which schema** → Sales or SalesLT
3. **Update Lakeflow Connect config** → Use correct schema
4. **Proceed with Option 2** → Ingest Customer & SalesOrderHeader
5. **Run converter** → Use sales_summary.sas

**Total time: 5 minutes to check + 20 minutes to ingest** ✅
