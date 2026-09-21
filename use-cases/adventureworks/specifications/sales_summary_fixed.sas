/********************************************
* Sales Summary Report - FIXED FOR FULL ADVENTURE WORKS SCHEMA
*
* Purpose: Demonstrate external database integration
*          with data quality checks
*
* Source: Adventure Works (SQL Server) - FULL SCHEMA
*         - Sales.Customer (with AccountNumber, not CompanyName)
*         - Sales.SalesOrderHeader
*
* Output: Customer sales summary with metrics
*
* Author: 3Cloud SAS Migration Team
* Fixed:  Schema corrected to match actual Adventure Works database
********************************************/

/********************************************
* Step 1: Load Customers from Bronze
* (Bronze data ingested from SQL Server via Lakeflow Connect)
********************************************/
DATA work.customers;
    SET sas_tanderson_bronze.customer;

    /* Filter to active customers with account numbers */
    WHERE AccountNumber IS NOT NULL;

    /* Clean account number */
    AccountNumber = STRIP(AccountNumber);

    /* EXPECTATION: All customers should have valid IDs */
    /* EXPECT CustomerID > 0 */

    /* EXPECTATION: Account numbers should be populated after filter */
    /* EXPECT AccountNumber IS NOT NULL AND LENGTH(AccountNumber) > 0 */

    /* EXPECTATION: Territory should be assigned */
    /* EXPECT TerritoryID IS NOT NULL */
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

    /* EXPECTATION: Order IDs should be unique and positive */
    /* EXPECT SalesOrderID > 0 */

    /* EXPECTATION: Order dates should be reasonable (not in future) */
    /* EXPECT OrderDate <= TODAY() */

    /* EXPECTATION: Order year should be within business range (2010-present) */
    /* EXPECT order_year >= 2010 AND order_year <= YEAR(TODAY()) */

    /* EXPECTATION: Total Due should be positive */
    /* EXPECT TotalDue > 0 */

    /* EXPECTATION: Subtotal + Tax + Freight should equal Total */
    /* EXPECT ABS((SubTotal + TaxAmt + Freight) - TotalDue) < 0.01 */
RUN;

/********************************************
* Step 3: Calculate Customer Summary Metrics
********************************************/
PROC SQL;
    CREATE TABLE work.customer_metrics AS
    SELECT
        c.CustomerID,
        c.AccountNumber,
        c.TerritoryID,
        COUNT(o.SalesOrderID) as OrderCount,
        SUM(o.TotalDue) as TotalRevenue,
        AVG(o.TotalDue) as AvgOrderValue,
        MIN(o.OrderDate) as FirstOrderDate,
        MAX(o.OrderDate) as LastOrderDate
    FROM work.customers c
    LEFT JOIN work.orders o ON c.CustomerID = o.CustomerID
    GROUP BY c.CustomerID, c.AccountNumber, c.TerritoryID
    HAVING COUNT(o.SalesOrderID) > 0;

    /* EXPECTATION: All customers in result should have at least 1 order */
    /* EXPECT OrderCount > 0 */

    /* EXPECTATION: Total revenue should be positive */
    /* EXPECT TotalRevenue > 0 */

    /* EXPECTATION: Average order value should be reasonable (> $10) */
    /* EXPECT AvgOrderValue >= 10 */

    /* EXPECTATION: First order should be before or equal to last order */
    /* EXPECT FirstOrderDate <= LastOrderDate */

    /* EXPECTATION: Customer IDs should be unique (no duplicates) */
    /* EXPECT COUNT(DISTINCT CustomerID) = COUNT(*) */
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

    /* EXPECTATION: Value tier should be one of three categories */
    /* EXPECT value_tier IN ('High', 'Medium', 'Low') */

    /* EXPECTATION: Churn risk should be one of three categories */
    /* EXPECT churn_risk IN ('High', 'Medium', 'Low') */

    /* EXPECTATION: Days since last order should be non-negative */
    /* EXPECT days_since_last_order >= 0 */

    /* EXPECTATION: Customer lifetime should be non-negative */
    /* EXPECT customer_lifetime_days >= 0 */

    /* EXPECTATION: High value tier should match revenue threshold */
    /* EXPECT (value_tier = 'High' AND TotalRevenue >= 10000) OR value_tier != 'High' */
RUN;

/********************************************
* Step 5: Create Gold Summary Table
********************************************/
PROC SQL;
    CREATE TABLE sas_tanderson_gold.customer_summary AS
    SELECT
        CustomerID,
        AccountNumber,
        TerritoryID,
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

    /* EXPECTATION: Gold table should have all required columns */
    /* EXPECT COUNT(*) > 0 */

    /* EXPECTATION: No NULL values in key business fields */
    /* EXPECT AccountNumber IS NOT NULL */
    /* EXPECT value_tier IS NOT NULL */
    /* EXPECT churn_risk IS NOT NULL */
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

    /* EXPECTATION: Should have 9 combinations (3 tiers x 3 risk levels) */
    /* EXPECT COUNT(*) <= 9 */

    /* EXPECTATION: Customer count should match detail table */
    /* EXPECT SUM(customer_count) = (SELECT COUNT(*) FROM work.customer_classified) */

    /* EXPECTATION: All aggregated values should be positive */
    /* EXPECT customer_count > 0 */
    /* EXPECT tier_revenue > 0 */
QUIT;

/* End of SAS program */
