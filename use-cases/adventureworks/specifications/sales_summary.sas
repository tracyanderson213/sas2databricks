/********************************************
* Sales Summary Report
*
* Purpose: Demonstrate external database integration
*
* Source: Adventure Works (SQL Server)
*         - Sales.Customer
*         - Sales.SalesOrderHeader
*
* Output: Customer sales summary with metrics
*
* Author: 3Cloud SAS Migration Team
********************************************/

/********************************************
* Step 1: Load Customers from Bronze
* (Bronze data ingested from SQL Server via Lakeflow Connect)
********************************************/
DATA work.customers;
    SET sas_tanderson_bronze.customer;

    /* Filter to active customers with company names */
    WHERE CompanyName IS NOT NULL;

    /* Clean company name */
    CompanyName = STRIP(CompanyName);
RUN;

/********************************************
* Step 2: Load Orders from Bronze
********************************************/
DATA work.orders;
    SET sas_tanderson_bronze.salesorderheader;

    /* Calculate days since order */
    days_since_order = TODAY() - OrderDate;

    /* Extract order year */
    order_year = YEAR(OrderDate);

    /* Flag recent orders (last 90 days) */
    IF days_since_order <= 90 THEN recent_order = 'Y';
    ELSE recent_order = 'N';
RUN;

/********************************************
* Step 3: Calculate Customer Summary Metrics
********************************************/
PROC SQL;
    CREATE TABLE work.customer_metrics AS
    SELECT
        c.CustomerID,
        c.CompanyName,
        c.EmailAddress,
        COUNT(o.SalesOrderID) as OrderCount,
        SUM(o.TotalDue) as TotalRevenue,
        AVG(o.TotalDue) as AvgOrderValue,
        MIN(o.OrderDate) as FirstOrderDate,
        MAX(o.OrderDate) as LastOrderDate
    FROM work.customers c
    LEFT JOIN work.orders o ON c.CustomerID = o.CustomerID
    GROUP BY c.CustomerID, c.CompanyName, c.EmailAddress
    HAVING COUNT(o.SalesOrderID) > 0;
QUIT;

/********************************************
* Step 4: Classify Customers by Value
********************************************/
DATA work.customer_classified;
    SET work.customer_metrics;

    /* Customer value tier */
    IF TotalRevenue >= 10000 THEN value_tier = 'High';
    ELSE IF TotalRevenue >= 5000 THEN value_tier = 'Medium';
    ELSE value_tier = 'Low';

    /* Calculate days since last order */
    days_since_last_order = TODAY() - LastOrderDate;

    /* Churn risk flag */
    IF days_since_last_order > 180 THEN churn_risk = 'High';
    ELSE IF days_since_last_order > 90 THEN churn_risk = 'Medium';
    ELSE churn_risk = 'Low';

    /* Customer lifetime (days) */
    customer_lifetime_days = LastOrderDate - FirstOrderDate;
RUN;

/********************************************
* Step 5: Create Gold Summary Table
********************************************/
PROC SQL;
    CREATE TABLE sas_tanderson_gold.customer_summary AS
    SELECT
        CustomerID,
        CompanyName,
        EmailAddress,
        OrderCount,
        TotalRevenue,
        AvgOrderValue,
        FirstOrderDate,
        LastOrderDate,
        value_tier,
        churn_risk,
        days_since_last_order,
        customer_lifetime_days
    FROM work.customer_classified
    ORDER BY TotalRevenue DESC;
QUIT;

/********************************************
* Step 6: Create Summary Statistics
********************************************/
PROC SQL;
    CREATE TABLE sas_tanderson_gold.sales_statistics AS
    SELECT
        value_tier,
        churn_risk,
        COUNT(*) as customer_count,
        SUM(TotalRevenue) as tier_revenue,
        AVG(TotalRevenue) as avg_customer_revenue,
        AVG(OrderCount) as avg_orders_per_customer
    FROM work.customer_classified
    GROUP BY value_tier, churn_risk
    ORDER BY value_tier, churn_risk;
QUIT;

/* End of SAS program */
