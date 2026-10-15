"""Seeded chart of accounts and the system account codes used by automatic postings."""

CASH = "1000"
BANK = "1010"
ACCOUNTS_RECEIVABLE = "1100"
INVENTORY = "1200"
VAT_INPUT = "1300"
ACCOUNTS_PAYABLE = "2000"
VAT_OUTPUT = "2100"
GRNI = "2150"
CAPITAL = "3000"
RETAINED_EARNINGS = "3100"
OPENING_BALANCE_EQUITY = "3900"
SALES = "4000"
SALES_RETURNS = "4100"
OTHER_INCOME = "4900"
COGS = "5000"
INVENTORY_ADJUSTMENTS = "5100"

CHART_OF_ACCOUNTS = [
    # code, name, type, system
    (CASH, "Cash on hand", "ASSET", True),
    (BANK, "Bank - Bank Muscat current account", "ASSET", True),
    (ACCOUNTS_RECEIVABLE, "Accounts receivable", "ASSET", True),
    (INVENTORY, "Inventory", "ASSET", True),
    (VAT_INPUT, "VAT input (recoverable)", "ASSET", True),
    ("1500", "Vehicles and equipment", "ASSET", False),
    (ACCOUNTS_PAYABLE, "Accounts payable", "LIABILITY", True),
    (VAT_OUTPUT, "VAT output payable", "LIABILITY", True),
    (GRNI, "Goods received not invoiced", "LIABILITY", True),
    ("2200", "Salaries payable", "LIABILITY", False),
    (CAPITAL, "Owner's capital", "EQUITY", True),
    (RETAINED_EARNINGS, "Retained earnings", "EQUITY", True),
    (OPENING_BALANCE_EQUITY, "Opening balance equity", "EQUITY", True),
    (SALES, "Sales revenue", "INCOME", True),
    (SALES_RETURNS, "Sales returns and allowances", "INCOME", True),
    (OTHER_INCOME, "Other income", "INCOME", False),
    (COGS, "Cost of goods sold", "EXPENSE", True),
    (INVENTORY_ADJUSTMENTS, "Inventory adjustments and write-offs", "EXPENSE", True),
    ("6000", "Salaries and wages", "EXPENSE", False),
    ("6100", "Rent - warehouses and office", "EXPENSE", False),
    ("6200", "Utilities (electricity and water)", "EXPENSE", False),
    ("6300", "Transport and fuel", "EXPENSE", False),
    ("6400", "Marketing and promotions", "EXPENSE", False),
    ("6500", "Office and IT expenses", "EXPENSE", False),
    ("6600", "Bank charges", "EXPENSE", False),
    ("6700", "Vehicle maintenance", "EXPENSE", False),
    ("6900", "Miscellaneous expenses", "EXPENSE", False),
]
