```json
[
  {
    "name": "SAS to Databricks Migration Architecture",
    "story": "Complete data flow from source systems through ingestion, Bronze/Silver/Gold transformation (converted SAS code), to consumption",
    "options": {
      "trademarkLogos": true
    },
    "columns": [
      "sources",
      "ingestion",
      "bronze",
      "transformation",
      "silver",
      "gold",
      "consumption"
    ],
    "nodes": [
      {
        "id": "adf-ingest",
        "type": "text",
        "at": [
          164,
          77
        ],
        "size": [
          104,
          26
        ],
        "ai_reasoning": "External ETL tools as text annotation",
        "text": "ADF / Fivetran",
        "fontSize": 14,
        "bold": true
      },
      {
        "id": "autoloader-ingest",
        "type": "text",
        "at": [
          158,
          13
        ],
        "size": [
          92,
          26
        ],
        "ai_reasoning": "Auto Loader for file-based ingestion; using text annotation since no dedicated catalog type",
        "text": "Auto Loader",
        "fontSize": 14,
        "bold": true
      },
      {
        "id": "bronze-claims",
        "type": "logo",
        "at": [
          463,
          94
        ],
        "text": "claims",
        "icon": "bronzeLayer",
        "caption": "right",
        "desc": "raw data"
      },
      {
        "id": "bronze-customer",
        "type": "logo",
        "at": [
          455,
          -98
        ],
        "text": "customer",
        "icon": "bronzeLayer",
        "caption": "right",
        "desc": "19,820 rows"
      },
      {
        "id": "bronze-orders",
        "type": "logo",
        "at": [
          455,
          -2
        ],
        "text": "salesorderheader",
        "icon": "bronzeLayer",
        "caption": "right",
        "desc": "31,465 rows"
      },
      {
        "id": "dashboard",
        "type": "ai-bi-dashboard",
        "at": [
          1699,
          -117
        ]
      },
      {
        "id": "genie-space",
        "type": "genie",
        "at": [
          1699,
          -21
        ]
      },
      {
        "id": "gold-claims",
        "type": "logo",
        "at": [
          1375,
          94
        ],
        "text": "claims_summary",
        "icon": "goldLayer",
        "caption": "right",
        "desc": "final metrics"
      },
      {
        "id": "gold-stats",
        "type": "logo",
        "at": [
          1367,
          -2
        ],
        "text": "sales_statistics",
        "icon": "goldLayer",
        "caption": "right",
        "desc": "KPIs, cross-tabs"
      },
      {
        "id": "gold-summary",
        "type": "logo",
        "at": [
          1367,
          -98
        ],
        "text": "customer_summary",
        "icon": "goldLayer",
        "caption": "right",
        "desc": "analytics-ready"
      },
      {
        "id": "governance",
        "type": "governance-block",
        "at": [
          1245,
          -274
        ]
      },
      {
        "id": "lakeflow-ingest",
        "type": "lakeflow-connect",
        "at": [
          163,
          -53
        ],
        "ai_reasoning": "Lakeflow Connect handles database CDC ingestion from SQL Server and Oracle"
      },
      {
        "id": "note-best-practice",
        "type": "note",
        "at": [
          226,
          -202
        ],
        "size": [
          196,
          140
        ],
        "ai_reasoning": "Architectural principle note highlighting separation of concerns between ingestion and transformation",
        "text": "✓ BEST PRACTICE: Converted SAS code does NOT connect to external sources\n• Production SAS reads from landed/staged data (Bronze), not live databases\n• Ingestion layer handles all source connections\n• SDP only reads from Bronze Delta tables"
      },
      {
        "id": "note-bronze",
        "type": "note",
        "at": [
          506,
          278
        ],
        "text": "Bronze Layer: sas_tanderson_bronze\n• Raw Delta tables\n• Landed by ingestion tools"
      },
      {
        "id": "note-gold",
        "type": "note",
        "at": [
          1386,
          278
        ],
        "text": "Gold Layer: sas_tanderson_gold\n• Analytics tables\n• Materialized for fast queries"
      },
      {
        "id": "note-ingestion",
        "type": "note",
        "at": [
          234,
          278
        ],
        "text": "Ingestion Layer (NOT part of SAS converter)\n• Lakeflow Connect for databases (CDC)\n• Auto Loader for files\n• ADF for external ETL"
      },
      {
        "id": "note-silver",
        "type": "note",
        "at": [
          1082,
          278
        ],
        "text": "Silver Layer: sas_tanderson_silver\n• Business transformations\n• Primarily views (storage optimization)"
      },
      {
        "id": "note-transformation",
        "type": "note",
        "at": [
          794,
          278
        ],
        "text": "Transformation Layer\n• Runs as Databricks Pipeline (SDP)\n• Converted SAS business logic\n• Reads FROM Bronze → Writes TO Silver/Gold"
      },
      {
        "id": "platform-box",
        "type": "box",
        "at": [
          1698,
          109
        ],
        "size": [
          196,
          90
        ],
        "title": "Databricks Platform"
      },
      {
        "id": "powerbi",
        "type": "text",
        "at": [
          1698,
          109
        ],
        "size": [
          132,
          26
        ],
        "text": "Power BI / Tableau",
        "fontSize": 14,
        "bold": true
      },
      {
        "id": "sdp-pipeline",
        "type": "sdp",
        "at": [
          755,
          8
        ],
        "ai_reasoning": "The Spark Declarative Pipeline running converted SAS business logic as a Databricks Pipeline resource",
        "label": "Databricks Pipeline",
        "desc": "Running converted SAS code (SDP)"
      },
      {
        "id": "silver-claims",
        "type": "logo",
        "at": [
          1071,
          142
        ],
        "text": "claims_adjudicated",
        "icon": "silverLayer",
        "caption": "right",
        "desc": "business logic applied"
      },
      {
        "id": "silver-customers",
        "type": "logo",
        "at": [
          1067,
          -146
        ],
        "text": "customers",
        "icon": "silverLayer",
        "caption": "right",
        "desc": "filtered, enriched"
      },
      {
        "id": "silver-metrics",
        "type": "logo",
        "at": [
          1079,
          46
        ],
        "text": "customer_metrics",
        "icon": "silverLayer",
        "caption": "right",
        "desc": "joined, aggregated"
      },
      {
        "id": "silver-orders",
        "type": "logo",
        "at": [
          1071,
          -50
        ],
        "text": "orders",
        "icon": "silverLayer",
        "caption": "right",
        "desc": "calculated fields"
      },
      {
        "id": "src-api",
        "type": "source",
        "at": [
          -124,
          124
        ],
        "label": "APIs",
        "icon": "file:cloud/aws/compute/lambda",
        "desc": "Real-time data"
      },
      {
        "id": "src-csv",
        "type": "source",
        "at": [
          -124,
          44
        ],
        "label": "CSV Files",
        "icon": "file:vendor/csv",
        "desc": "Partner Feeds"
      },
      {
        "id": "src-oracle",
        "type": "source",
        "at": [
          -124,
          -36
        ],
        "icon": "file:vendor/oracle",
        "desc": "Enterprise DW"
      },
      {
        "id": "src-sqlserver",
        "type": "source",
        "at": [
          -124,
          -132
        ],
        "label": "SQL Server",
        "icon": "file:vendor/microsoft-sql-server",
        "desc": "Adventure Works (19,820 customers)"
      }
    ],
    "edges": [
      {
        "id": "e1",
        "from": "src-sqlserver@r",
        "to": "lakeflow-ingest@l",
        "flow": true,
        "label": "CDC Sync"
      },
      {
        "id": "e10",
        "from": "bronze-claims@r",
        "to": "sdp-pipeline@l",
        "flow": true,
        "label": "Read"
      },
      {
        "id": "e11",
        "from": "sdp-pipeline@r",
        "to": "silver-customers@l",
        "flow": true,
        "label": "WHERE filters"
      },
      {
        "id": "e12",
        "from": "sdp-pipeline@r",
        "to": "silver-orders@l",
        "flow": true,
        "label": "Calculated fields"
      },
      {
        "id": "e13",
        "from": "sdp-pipeline@r",
        "to": "silver-metrics@l",
        "flow": true,
        "label": "JOIN + Aggregate"
      },
      {
        "id": "e14",
        "from": "sdp-pipeline@r",
        "to": "silver-claims@l",
        "flow": true,
        "label": "MERGE logic"
      },
      {
        "id": "e15",
        "from": "silver-customers@r",
        "to": "gold-summary@l",
        "flow": true
      },
      {
        "id": "e16",
        "from": "silver-orders@r",
        "to": "gold-summary@l",
        "flow": true
      },
      {
        "id": "e17",
        "from": "silver-metrics@r",
        "to": "gold-stats@l",
        "flow": true
      },
      {
        "id": "e18",
        "from": "silver-claims@r",
        "to": "gold-claims@l",
        "flow": true
      },
      {
        "id": "e19",
        "from": "gold-summary@r",
        "to": "dashboard@l",
        "flow": true,
        "label": "Query"
      },
      {
        "id": "e2",
        "from": "src-oracle@r",
        "to": "adf-ingest@l",
        "label": "Batch ETL"
      },
      {
        "id": "e20",
        "from": "gold-stats@r",
        "to": "dashboard@l",
        "flow": true,
        "label": "Query"
      },
      {
        "id": "e21",
        "from": "gold-summary@r",
        "to": "genie-space@l",
        "flow": true,
        "label": "Natural Language"
      },
      {
        "id": "e22",
        "from": "gold-claims@r",
        "to": "powerbi@l",
        "label": "Export"
      },
      {
        "id": "e3",
        "from": "src-csv@r",
        "to": "autoloader-ingest@l",
        "label": "Incremental"
      },
      {
        "id": "e4",
        "from": "src-api@r",
        "to": "adf-ingest@l",
        "label": "API Polling"
      },
      {
        "id": "e5",
        "from": "lakeflow-ingest@r",
        "to": "bronze-customer@l",
        "flow": true,
        "label": "19,820 rows"
      },
      {
        "id": "e6",
        "from": "lakeflow-ingest@r",
        "to": "bronze-orders@l",
        "flow": true,
        "label": "31,465 rows"
      },
      {
        "id": "e7",
        "from": "autoloader-ingest@r",
        "to": "bronze-claims@l",
        "flow": true
      },
      {
        "id": "e8",
        "from": "bronze-customer@r",
        "to": "sdp-pipeline@l",
        "flow": true,
        "label": "Read"
      },
      {
        "id": "e9",
        "from": "bronze-orders@r",
        "to": "sdp-pipeline@l",
        "flow": true,
        "label": "Read"
      }
    ]
  }
]
```
