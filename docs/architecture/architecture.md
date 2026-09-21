```json
[
  {
    "name": "SAS to Databricks Migration Architecture",
    "nodes": [
      {
        "id": "sql_server",
        "label": "SQL Server\n(Adventure Works)",
        "type": "cylinder",
        "color": "#0078D4",
        "group": "sources"
      },
      {
        "id": "oracle",
        "label": "Oracle\n(Enterprise DW)",
        "type": "cylinder",
        "color": "#F80000",
        "group": "sources"
      },
      {
        "id": "csv_files",
        "label": "CSV Files\n(Partner Feeds)",
        "type": "document",
        "color": "#107C10",
        "group": "sources"
      },
      {
        "id": "apis",
        "label": "APIs\n(Real-time)",
        "type": "cloud",
        "color": "#5E5E5E",
        "group": "sources"
      },
      {
        "id": "lakeflow_connect",
        "label": "Lakeflow Connect\n(CDC for Databases)",
        "type": "hexagon",
        "color": "#FF6C00",
        "group": "ingestion"
      },
      {
        "id": "auto_loader",
        "label": "Auto Loader\n(File Ingestion)",
        "type": "hexagon",
        "color": "#FF6C00",
        "group": "ingestion"
      },
      {
        "id": "adf",
        "label": "ADF / Fivetran\n(External ETL)",
        "type": "hexagon",
        "color": "#FF6C00",
        "group": "ingestion"
      },
      {
        "id": "bronze_customer",
        "label": "customer\n(19,820 rows)",
        "type": "rectangle",
        "color": "#CD7F32",
        "group": "bronze"
      },
      {
        "id": "bronze_orders",
        "label": "salesorderheader\n(31,465 rows)",
        "type": "rectangle",
        "color": "#CD7F32",
        "group": "bronze"
      },
      {
        "id": "bronze_claims",
        "label": "claims\n(raw data)",
        "type": "rectangle",
        "color": "#CD7F32",
        "group": "bronze"
      },
      {
        "id": "sdp_pipeline",
        "label": "Spark Declarative Pipeline\n(Converted SAS Code)\n\n• sales_summary.sas\n• claims_adjudication.sas",
        "type": "rounded",
        "color": "#00A4EF",
        "group": "transformation"
      },
      {
        "id": "silver_customers",
        "label": "customers\n(filtered, enriched)",
        "type": "parallelogram",
        "color": "#C0C0C0",
        "group": "silver"
      },
      {
        "id": "silver_orders",
        "label": "orders\n(calculated fields)",
        "type": "parallelogram",
        "color": "#C0C0C0",
        "group": "silver"
      },
      {
        "id": "silver_metrics",
        "label": "customer_metrics\n(joined, aggregated)",
        "type": "parallelogram",
        "color": "#C0C0C0",
        "group": "silver"
      },
      {
        "id": "silver_claims",
        "label": "claims_adjudicated\n(business logic applied)",
        "type": "parallelogram",
        "color": "#C0C0C0",
        "group": "silver"
      },
      {
        "id": "gold_summary",
        "label": "customer_summary\n(analytics-ready)",
        "type": "rectangle",
        "color": "#FFD700",
        "group": "gold"
      },
      {
        "id": "gold_stats",
        "label": "sales_statistics\n(KPIs, cross-tabs)",
        "type": "rectangle",
        "color": "#FFD700",
        "group": "gold"
      },
      {
        "id": "gold_claims_summary",
        "label": "claims_summary\n(final metrics)",
        "type": "rectangle",
        "color": "#FFD700",
        "group": "gold"
      },
      {
        "id": "aibi_dashboard",
        "label": "AI/BI Dashboard\n(Visual Analytics)",
        "type": "rectangle",
        "color": "#8B00FF",
        "group": "consumption"
      },
      {
        "id": "genie",
        "label": "Genie Space\n(Natural Language)",
        "type": "rectangle",
        "color": "#8B00FF",
        "group": "consumption"
      },
      {
        "id": "powerbi",
        "label": "Power BI / Tableau\n(External BI)",
        "type": "rectangle",
        "color": "#8B00FF",
        "group": "consumption"
      },
      {
        "id": "bronze_layer_label",
        "label": "BRONZE LAYER\n(Delta Tables)\nsas_tanderson_bronze",
        "type": "note",
        "color": "#CD7F32",
        "group": "bronze"
      },
      {
        "id": "silver_layer_label",
        "label": "SILVER LAYER\n(Views/Tables)\nsas_tanderson_silver",
        "type": "note",
        "color": "#C0C0C0",
        "group": "silver"
      },
      {
        "id": "gold_layer_label",
        "label": "GOLD LAYER\n(Analytics Tables)\nsas_tanderson_gold",
        "type": "note",
        "color": "#FFD700",
        "group": "gold"
      }
    ],
    "edges": [
      {
        "from": "sql_server",
        "to": "lakeflow_connect",
        "label": "CDC Sync"
      },
      {
        "from": "oracle",
        "to": "adf",
        "label": "Batch ETL"
      },
      {
        "from": "csv_files",
        "to": "auto_loader",
        "label": "Incremental"
      },
      {
        "from": "apis",
        "to": "adf",
        "label": "API Polling"
      },
      {
        "from": "lakeflow_connect",
        "to": "bronze_customer",
        "label": "19,820 rows"
      },
      {
        "from": "lakeflow_connect",
        "to": "bronze_orders",
        "label": "31,465 rows"
      },
      {
        "from": "auto_loader",
        "to": "bronze_claims",
        "label": "File → Delta"
      },
      {
        "from": "adf",
        "to": "bronze_claims",
        "label": "External → Delta"
      },
      {
        "from": "bronze_customer",
        "to": "sdp_pipeline",
        "label": "Read"
      },
      {
        "from": "bronze_orders",
        "to": "sdp_pipeline",
        "label": "Read"
      },
      {
        "from": "bronze_claims",
        "to": "sdp_pipeline",
        "label": "Read"
      },
      {
        "from": "sdp_pipeline",
        "to": "silver_customers",
        "label": "WHERE filters"
      },
      {
        "from": "sdp_pipeline",
        "to": "silver_orders",
        "label": "Calculated fields"
      },
      {
        "from": "sdp_pipeline",
        "to": "silver_metrics",
        "label": "JOIN + Aggregate"
      },
      {
        "from": "sdp_pipeline",
        "to": "silver_claims",
        "label": "MERGE logic"
      },
      {
        "from": "silver_customers",
        "to": "gold_summary",
        "label": "Materialize"
      },
      {
        "from": "silver_orders",
        "to": "gold_summary",
        "label": "Materialize"
      },
      {
        "from": "silver_metrics",
        "to": "gold_stats",
        "label": "Cross-tab"
      },
      {
        "from": "silver_claims",
        "to": "gold_claims_summary",
        "label": "Final KPIs"
      },
      {
        "from": "gold_summary",
        "to": "aibi_dashboard",
        "label": "Query"
      },
      {
        "from": "gold_stats",
        "to": "aibi_dashboard",
        "label": "Query"
      },
      {
        "from": "gold_summary",
        "to": "genie",
        "label": "Natural Language"
      },
      {
        "from": "gold_claims_summary",
        "to": "powerbi",
        "label": "Export"
      }
    ],
    "groups": [
      {
        "id": "sources",
        "label": "SOURCE SYSTEMS",
        "color": "#E8E8E8"
      },
      {
        "id": "ingestion",
        "label": "INGESTION LAYER (Not Part of SAS Converter)",
        "color": "#FFF4E6"
      },
      {
        "id": "bronze",
        "label": "BRONZE LAYER (Raw Data - Delta Format)",
        "color": "#F5E6D3"
      },
      {
        "id": "transformation",
        "label": "TRANSFORMATION LAYER (Converted SAS Code)",
        "color": "#E6F2FF"
      },
      {
        "id": "silver",
        "label": "SILVER LAYER (Business Logic)",
        "color": "#F0F0F0"
      },
      {
        "id": "gold",
        "label": "GOLD LAYER (Analytics)",
        "color": "#FFFACD"
      },
      {
        "id": "consumption",
        "label": "CONSUMPTION LAYER",
        "color": "#F0E6FF"
      }
    ]
  }
]
```
