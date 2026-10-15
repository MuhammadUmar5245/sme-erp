// SME-ERP - Power Query (M) connector for the paginated reporting API (/api/v1/reports/<dataset>/).
//
// 1. Create three parameters (Home > Manage parameters > New):
//      BaseUrl   (Text)  e.g. "https://localhost"   - root URL of the ERP, no trailing slash
//      ApiToken  (Text)  token of powerbi@alwadi.om  - printed by `make seed`
//      DateFrom  (Text)  e.g. "2025-01-01"           - optional; "" loads everything
// 2. Paste this query into a Blank query named GetDataset, then create one query per dataset:
//      = GetDataset("fact-sales")      = GetDataset("dim-product")   ...
//    Datasets: dim-date, dim-product, dim-customer, dim-supplier, dim-employee, dim-warehouse,
//    fact-sales, fact-purchases, fact-inventory-daily, fact-payments, fact-expenses, fact-feedback,
//    fact-interactions, fact-receivables (list: GET /api/v1/reports/).
//
// Web.Contents uses a static base URL with RelativePath and Query, so the Power BI Service can refresh it
// on a schedule (dynamic URLs built from the `next` link cannot be refreshed in the Service).

(dataset as text) as table =>
let
    PageSize = 5000,
    Headers = [Authorization = "Token " & ApiToken, Accept = "application/json"],
    BaseQuery = if DateFrom = null or DateFrom = "" then [] else [date_from = DateFrom],

    GetPage = (page as number) as record =>
        Json.Document(
            Web.Contents(
                BaseUrl,
                [
                    RelativePath = "api/v1/reports/" & dataset & "/",
                    Query = BaseQuery & [page = Number.ToText(page), page_size = Number.ToText(PageSize)],
                    Headers = Headers,
                    ManualStatusHandling = {400, 401, 403, 404}
                ]
            )
        ),

    FirstPage = GetPage(1),
    Checked = if Record.HasFields(FirstPage, "results") then FirstPage
              else error Error.Record("SME-ERP API", "Request failed", FirstPage),
    PageCount = Number.RoundUp(Checked[count] / PageSize),
    OtherPages = List.Transform({2..PageCount}, each GetPage(_)[results]),
    AllRows = List.Combine({Checked[results]} & OtherPages),
    AsTable = if List.IsEmpty(AllRows) then #table({}, {}) else Table.FromRecords(AllRows, null, MissingField.UseNull)
in
    AsTable

// ---------------------------------------------------------------------------------------------
// Example: typed fact_sales query (money arrives as text so no rounding happens in JSON).
//
// let
//     Source = GetDataset("fact-sales"),
//     Typed = Table.TransformColumnTypes(Source, {
//         {"sales_line_id", Int64.Type}, {"invoice_id", Int64.Type}, {"date_key", Int64.Type},
//         {"sales_date", type date}, {"customer_id", Int64.Type}, {"product_id", Int64.Type},
//         {"warehouse_id", Int64.Type}, {"quantity", type number}, {"unit_price", Currency.Type},
//         {"discount_pct", type number}, {"net_amount", Currency.Type}, {"vat_amount", Currency.Type},
//         {"gross_amount", Currency.Type}, {"cost_amount", Currency.Type}, {"gross_margin", Currency.Type}},
//         "en-US")
// in
//     Typed
