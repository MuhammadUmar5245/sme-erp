"""Generate the deliberately dirty 'legacy system' files used to demo the import wizard.

Run inside the web container:  python sample_data/legacy/generate_legacy_files.py
Each file contains typical legacy problems: inconsistent case and spacing, phone formats, city
spellings, duplicates (exact and fuzzy), missing required fields, negative numbers, mixed date formats.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

CUSTOMERS = [
    ["Cust No", "CUSTOMER NAME", "Type", "Tel", "E-mail", "Town", "Address", "VAT No", "Credit Limit (OMR)", "Credit Days"],
    ["L-C001", "AL MEERA HYPERMARKET", "Supermarket", "2456 1234", "orders@almeera.om", "MCT", "Qurum", "OM1100223344", "5,000.000", "45"],
    ["L-C002", "  al-meera hypermarket llc ", "Supermarket", "+968 2456-1234", "", "muscat", "Qurum", "", "5000", "45"],
    ["L-C003", "Nesto Hypermarket Seeb", "hypermarket", "00968 99887766", "SEEB@NESTO.OM", "Al Seeb", "Mawaleh South", "", "OMR 4000", "30"],
    ["L-C004", "Sultan Center Bausher", "Supermarket", "968 24561299", "info@sultan-center.om", "bousher", "", "", "3500", "30"],
    ["L-C005", "AL FAIR SUPERMARKET", "supermarket", "9123 4567", "alfair@@mail", "Muscat", "Shatti Al Qurum", "", "2500", "30"],
    ["L-C006", "Al Fair Supermarket", "supermarket", "92345678", "", "Sohar", "Sohar Corniche", "", "2000", "30"],
    ["L-C007", "Bait Al Baraka Baqala", "baqala", "1234", "", "Nizwah", "Firq", "", "300", "15"],
    ["L-C008", "", "baqala", "9988 7766", "", "Nizwa", "", "", "200", "15"],
    ["L-C009", "Crowne Plaza Muscat", "Hotel", "+96824660660", "purchasing@cpmuscat.om", "Ghubra", "Ghubra North", "OM1100998877", "8000", "60"],
    ["L-C010", "Dhofar Mart", "wholesale", "2329 1100", "", "salala", "Al Saada", "", "3000", "30"],
    ["L-C011", "Dhofar Mart", "wholesale", "2329 1100", "", "Salalah", "Al Saada", "", "3000", "30"],
    ["L-C012", "Sur Fresh Market", "Supermarket", "9555 1212", "", "Soor", "", "", "-500", "30"],
    ["L-C013", "Ibri Trading Est", "WHOLESALE", "9666 3434", "ibri.trading@gmail.com", "Ibri", "", "", "1500", "abc"],
    ["", "Barka Family Store", "baqala", "9777 4545", "", "Barkha", "", "", "250", "15"],
    ["L-C015", "Royal Hospital Canteen", "hospital", "2459 9000", "", "Bawshar", "", "", "1000", "45"],
    ["L-C016", "Gulf Hotel Supplies", "???", "9811 2233", "", "Muscat", "", "", "1000", "30"],
    ["L-C017", "Rustaq Mini Mart", "baqala", "9822 3344", "", "", "", "", "150", "15"],
    ["L-C018", "Lulu Hypermarket Sohar", "Supermarket", "26 84 12 00", "sohar@lulu.om", "suhar", "Falaj Al Qabail", "", "6000", "45"],
    ["L-C019", "Spar Al Khuwair", "supermarket", "9833 4455", "spar.khuwair@spar.om", "Al Khuwair", "", "", "1800", "30"],
    ["L-C001", "Duplicate Code Trading", "wholesale", "9844 5566", "", "Muscat", "", "", "500", "30"],
    ["L-C021", "Grand Mall Kiosk", "shop", "+968 9855 6677", "", "Dubai", "", "", "100", "7"],
    ["L-C022", "Nizwa Grand Hotel", "Hotel", "2541 1111", "fnb@nizwagrand.om", "Nizwa", "", "", "4000", "60"],
    ["L-C023", "sohar university cafeteria", "school", "2672 0101", "", "Sohar", "", "", "800", "30"],
]

SUPPLIERS = [
    ["Vendor Code", "Vendor Name", "Contact", "Phone", "Email", "City", "Country", "VAT", "Terms"],
    ["L-S01", "OMAN FLOUR MILLS SAOG", "Khalid Al Harthy", "2471 1155", "sales@omanflour.com", "Muscat", "oman", "OM1100001111", "30"],
    ["L-S02", "  Al Marai Oman LLC", "ravi kumar", "9911 2233", "", "Muscat", "Oman", "", "45"],
    ["L-S03", "almarai oman llc", "Ravi Kumar", "+968 9911 2233", "", "Muscat", "Oman", "", "45"],
    ["L-S04", "A'Saffa Foods SAOG", "Sara", "2444 5566", "orders@asaffa", "Muscat", "Oman", "", "30"],
    ["L-S05", "Gulf Plastic Industries", "", "123", "", "Sohar", "Oman", "", "60"],
    ["L-S06", "", "Ahmed", "9922 3344", "", "Muscat", "Oman", "", "30"],
    ["L-S07", "Unilever Gulf FZE", "Priya Nair", "+971 4 555 1000", "gulf@unilever.com", "Dubai", "UAE", "", "60"],
    ["L-S08", "Areej Vegetable Oils", "Salim", "2671 2233", "", "Sohar", "Oman", "", "-30"],
    ["L-S09", "National Detergent Co SAOG", "Hamed", "2681 0000", "info@ndc.om", "SOHAR", "OMAN", "", "45"],
    ["L-S01", "Oman Flour Mills", "Khalid", "2471 1155", "", "Muscat", "Oman", "", "30"],
]

PRODUCTS = [
    ["Item Code", "Description", "Item Group", "UOM", "Unit Cost", "Selling Price", "Min Stock", "EAN"],
    ["lgc-1001", "BASMATI RICE 5KG", "rice & grains", "bag", 3.2, 4.1, 50, "6291000000011"],
    ["LGC-1002", "sona masoori rice 10kg", "Rice & Grains", "Bag", 4.75, "5.900", 30, ""],
    ["LGC 1003", "Arabic Coffee 250g", "BEVERAGES", "pcs", "1.250 OMR", "1.800", 40, ""],
    ["LGC-1004", "Saffron Tea 100 bags", " beverages ", "pack", 0.95, 1.4, 60, ""],
    ["LGC-1005", "Dates Khalas 1kg", "Dates", "box", 1.1, 1.75, 80, ""],
    ["LGC-1006", "Dates Fard Premium 5kg", "dates", "Carton", -2.5, 6, 20, ""],
    ["LGC-1007", "Halwa Omani 500g", "Sweets", "PCS", 1.6, 2.4, 25, ""],
    ["", "Rose Water 500ml", "Grocery", "btl", 0.35, 0.6, 50, ""],
    ["LGC-1009", "Laundry Detergent 3kg", "Household", "kgs", 1.9, 2.7, 40, ""],
    ["LGC-1009", "Laundry Detergent 3kg (dup)", "Household", "pcs", 1.9, 2.7, 40, ""],
    ["LGC-1011", "Dish Wash Liquid 1L", "household", "LTR", 0.45, 0.4, 60, ""],
    ["LGC-1012", "Tissue Box 200s", "Household", "box", 0.3, "", 100, ""],
    ["LGC-1013", "Ghee 1kg Tin", "Dairy & Oils", "tin", 2.8, 3.6, 30, ""],
    ["LGC-1014", "Sunflower Oil 1.8L", "Dairy & Oils", "btl", 1.15, 1.6, 70, ""],
]

OPENING_STOCK = [
    ["Item Code", "Store", "Qty On Hand", "Avg Cost", "Count Date"],
    ["LGC-1001", "Muscat WH", "120", "3.200", "31/12/2025"],
    ["LGC-1002", "MCT", "80", "4.750", "2025-12-31"],
    ["LGC-1003", "Sohar", "60", "", "31-Dec-2025"],
    ["LGC-1004", "SOHAR WAREHOUSE", "-15", "0.950", "31/12/2025"],
    ["LGC-1005", "Muscat WH", "", "1.100", "31/12/2025"],
    ["LGC-1007", "Nizwa store", "40", "1.600", "31/12/2025"],
    ["LGC-9999", "MCT", "10", "1.000", "31/12/2025"],
    ["LGC-1001", "Muscat WH", "5", "3.200", "31/12/2025"],
    ["LGC-1009", "MCT", "35", "1.900", "12.31.2025"],
    ["LGC-1014", "SOH", "1,200", "1.150", "31.12.2025"],
]

OPENING_BALANCES = [
    ["Account", "Account Name", "Dr", "Cr", "As Of"],
    ["1000 - Cash", "Cash on hand", "1,250.500", "", "31/12/2025"],
    ["1010", "Bank Muscat", "48,300.000", "", "31/12/2025"],
    ["1100", "Debtors control", "12,400.750", "", "31/12/2025"],
    ["2000", "Creditors control", "", "9,875.250", "31/12/2025"],
    ["2100", "VAT payable", "", "1,120.000", "31/12/2025"],
    ["1500", "Vehicles", "18,000", "500", "31/12/2025"],
    ["1999", "Suspense", "300", "", "31/12/2025"],
    ["3000", "Capital", "", "60,000.000", "31/12/2025"],
    ["1010", "Bank Muscat (again)", "100", "", "31/12/2025"],
]


def write_csv(name, rows):
    with open(HERE / name, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)


def write_xlsx(name, rows):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Items"
    for row in rows:
        ws.append(row)
    wb.save(HERE / name)


if __name__ == "__main__":
    write_csv("customers_legacy.csv", CUSTOMERS)
    write_csv("suppliers_legacy.csv", SUPPLIERS)
    write_xlsx("products_legacy.xlsx", PRODUCTS)
    write_csv("opening_stock_legacy.csv", OPENING_STOCK)
    write_csv("opening_balances_legacy.csv", OPENING_BALANCES)
    print("Legacy sample files written to", HERE)
