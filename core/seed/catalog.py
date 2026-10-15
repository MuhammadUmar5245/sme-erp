"""Static master data for the Al Wadi Trading & Distribution demo company (FMCG and household goods)."""

# code, name, products: (name, unit, cost OMR)
CATEGORIES = [
    ("RICE", "Rice & Grains", [
        ("Basmati Rice Premium 5kg", "BAG", 3.250), ("Basmati Rice Premium 10kg", "BAG", 6.100),
        ("Sella Basmati Rice 20kg", "BAG", 11.400), ("Sona Masoori Rice 10kg", "BAG", 4.700),
        ("Egyptian Calrose Rice 5kg", "BAG", 2.650), ("Thai Jasmine Rice 5kg", "BAG", 3.400),
        ("Whole Wheat Flour 10kg", "BAG", 2.350), ("All Purpose Flour 1kg", "PACK", 0.290),
        ("Chakki Atta 5kg", "BAG", 1.450), ("Red Lentils 1kg", "PACK", 0.560), ("Chickpeas 1kg", "PACK", 0.620),
        ("Rolled Oats 500g", "PACK", 0.480), ("Vermicelli 400g", "PACK", 0.210), ("Spaghetti 500g", "PACK", 0.240),
        ("Semolina 1kg", "PACK", 0.390),
    ]),
    ("BEV", "Beverages", [
        ("Mineral Water 330ml x 24", "CTN", 1.150), ("Mineral Water 1.5L x 6", "PACK", 0.640),
        ("Orange Juice 1L", "BTL", 0.520), ("Mango Nectar 1L", "BTL", 0.480), ("Laban Up 200ml x 18", "CTN", 1.900),
        ("Cola 330ml x 24", "CTN", 3.600), ("Lemon Soda 330ml x 24", "CTN", 3.450),
        ("Vimto Cordial 710ml", "BTL", 0.880), ("Rooh Afza Syrup 800ml", "BTL", 0.910),
        ("Black Tea 100 bags", "BOX", 0.950), ("Karak Tea Premix 20 sachets", "BOX", 1.150),
        ("Arabic Coffee with Cardamom 250g", "PACK", 1.650), ("Instant Coffee 200g", "PACK", 2.300),
        ("Energy Drink 250ml x 24", "CTN", 6.200), ("Tang Orange Powder 2kg", "PACK", 2.700),
    ]),
    ("DAIRY", "Dairy & Edible Oils", [
        ("Fresh Milk 2L", "BTL", 0.690), ("Long Life Milk 1L x 12", "CTN", 3.900), ("Laban 2L", "BTL", 0.640),
        ("Yoghurt 1kg", "PCS", 0.540), ("Cheddar Cheese Slices 400g", "PACK", 1.250),
        ("Labneh 500g", "PCS", 0.890), ("Butter 400g", "PCS", 1.400), ("Ghee Pure Cow 1kg", "PCS", 3.350),
        ("Milk Powder 2.5kg", "PCS", 5.200), ("Sunflower Oil 1.8L", "BTL", 1.180), ("Corn Oil 1.5L", "BTL", 1.320),
        ("Olive Oil Extra Virgin 1L", "BTL", 3.150), ("Vegetable Oil 18L Tin", "PCS", 9.400),
        ("Evaporated Milk 170g x 48", "CTN", 9.800), ("Cream 170g x 48", "CTN", 11.200),
    ]),
    ("DATES", "Dates & Sweets", [
        ("Khalas Dates 1kg", "BOX", 1.350), ("Fard Dates 1kg", "BOX", 0.950), ("Khenaizi Dates 1kg", "BOX", 1.150),
        ("Medjool Dates 1kg", "BOX", 4.200), ("Dates Gift Box 500g", "BOX", 2.400), ("Date Paste 1kg", "PACK", 0.780),
        ("Omani Halwa 500g", "PCS", 1.700), ("Omani Halwa Saffron 1kg", "PCS", 3.900),
        ("Maamoul Dates 400g", "PACK", 1.050), ("Honey Sidr 500g", "BTL", 6.800), ("Tahini 450g", "BTL", 0.920),
        ("Rose Water 500ml", "BTL", 0.360), ("Saffron 1g", "PCS", 1.250), ("Cardamom 100g", "PACK", 1.800),
        ("Mixed Nuts 500g", "PACK", 2.650),
    ]),
    ("SNACK", "Snacks & Confectionery", [
        ("Potato Chips 23g x 24", "CTN", 1.750), ("Chocolate Bar 45g x 24", "BOX", 3.900),
        ("Wafer Biscuits 30g x 24", "BOX", 1.650), ("Digestive Biscuits 400g", "PACK", 0.590),
        ("Cream Biscuits 12 x 6", "PACK", 0.820), ("Popcorn Microwave 3 pack", "PACK", 0.450),
        ("Salted Peanuts 300g", "PACK", 0.640), ("Chewing Gum 12 x 20", "BOX", 2.900),
        ("Lollipop Jar 100", "PCS", 3.100), ("Croissant Chocolate 6 pack", "PACK", 0.950),
        ("Cake Slices 30g x 12", "BOX", 1.200), ("Corn Flakes 750g", "BOX", 1.350),
        ("Ice Cream Cone x 24", "CTN", 4.800), ("Jelly Cups 6 pack", "PACK", 0.550), ("Cashew Roasted 400g", "PACK", 2.950),
    ]),
    ("CANNED", "Canned & Packaged Food", [
        ("Tuna Chunks 185g x 48", "CTN", 17.500), ("Chickpeas Canned 400g x 24", "CTN", 5.300),
        ("Foul Medames 400g x 24", "CTN", 5.900), ("Tomato Paste 135g x 48", "CTN", 6.400),
        ("Sweet Corn 340g x 24", "CTN", 6.800), ("Baked Beans 400g x 24", "CTN", 6.100),
        ("Mixed Vegetables 400g x 24", "CTN", 6.300), ("Mushrooms Sliced 400g x 24", "CTN", 7.600),
        ("Chicken Luncheon 340g x 24", "CTN", 9.500), ("Instant Noodles x 40", "CTN", 4.900),
        ("Ketchup 340g", "BTL", 0.580), ("Mayonnaise 473ml", "BTL", 0.950), ("Sugar 2kg", "BAG", 0.720),
        ("Salt 1kg", "PACK", 0.120), ("Frozen Chicken 1.2kg x 10", "CTN", 13.500),
    ]),
    ("HOME", "Household Cleaning", [
        ("Laundry Powder 3kg", "BAG", 1.950), ("Laundry Liquid 3L", "BTL", 2.250), ("Fabric Softener 3L", "BTL", 1.400),
        ("Dishwashing Liquid 1L", "BTL", 0.480), ("Bleach 3.78L", "BTL", 0.690), ("Floor Cleaner 3L", "BTL", 1.050),
        ("Glass Cleaner 750ml", "BTL", 0.560), ("Toilet Cleaner 1L", "BTL", 0.650),
        ("Tissue Box 200 sheets x 5", "PACK", 1.100), ("Toilet Roll 10 pack", "PACK", 1.300),
        ("Kitchen Towel 4 rolls", "PACK", 0.980), ("Garbage Bags 50 pcs", "PACK", 0.520),
        ("Aluminium Foil 30m", "PCS", 0.890), ("Cling Film 300m", "PCS", 1.150), ("Air Freshener 300ml", "PCS", 0.640),
    ]),
    ("CARE", "Personal Care", [
        ("Shampoo 400ml", "BTL", 1.050), ("Hair Oil 200ml", "BTL", 0.780), ("Body Wash 500ml", "BTL", 0.990),
        ("Soap Bar 125g x 6", "PACK", 0.850), ("Toothpaste 120ml", "PCS", 0.540), ("Toothbrush 3 pack", "PACK", 0.620),
        ("Deodorant Spray 150ml", "PCS", 0.960), ("Baby Diapers Size 4 x 44", "PACK", 3.950),
        ("Baby Wipes 72", "PACK", 0.580), ("Sanitary Pads 30", "PACK", 1.050), ("Hand Sanitizer 500ml", "BTL", 0.720),
        ("Shaving Foam 200ml", "PCS", 0.890), ("Facial Tissue Pocket x 24", "PACK", 0.830),
        ("Oud Perfume Oil 12ml", "BTL", 2.400), ("Body Lotion 400ml", "BTL", 1.150),
    ]),
]

# Category demand profile: (popularity, Ramadan boost, summer factor)
CATEGORY_PROFILE = {
    "RICE": (1.3, 1.7, 0.85), "BEV": (1.4, 1.5, 1.25), "DAIRY": (1.2, 1.4, 0.9), "DATES": (0.8, 2.6, 0.7),
    "SNACK": (1.0, 1.1, 1.0), "CANNED": (1.0, 1.6, 0.85), "HOME": (0.9, 1.2, 0.9), "CARE": (0.8, 1.1, 0.95),
}

# name, city, country, categories supplied, lead time days
SUPPLIERS = [
    ("Oman Flour Mills SAOG", "Muscat", "Oman", ["RICE"], 3), ("Khimji Ramdas Food Division", "Muscat", "Oman", ["RICE", "CANNED"], 4),
    ("Al Hilal Rice Importers LLC", "Muscat", "Oman", ["RICE"], 5), ("India Gate Foods Gulf FZE", "Dubai", "UAE", ["RICE"], 9),
    ("Oman Refreshment Company SAOG", "Muscat", "Oman", ["BEV"], 3), ("Tanuf Water Factory", "Nizwa", "Oman", ["BEV"], 3),
    ("Al Rawabi Beverages LLC", "Muscat", "Oman", ["BEV"], 4), ("Nestle Middle East FZE", "Dubai", "UAE", ["BEV", "DAIRY"], 8),
    ("Mazoon Dairy Company SAOC", "Muscat", "Oman", ["DAIRY"], 2), ("A'Saffa Foods SAOG", "Muscat", "Oman", ["DAIRY", "CANNED"], 3),
    ("Al Marai Oman LLC", "Muscat", "Oman", ["DAIRY", "BEV"], 3), ("Areej Vegetable Oils SAOG", "Sohar", "Oman", ["DAIRY"], 4),
    ("Dhofar Cattle Feed SAOG", "Salalah", "Oman", ["DAIRY"], 6), ("Al Khair Dates Factory", "Nizwa", "Oman", ["DATES"], 4),
    ("Bateel Dates Trading", "Muscat", "Oman", ["DATES"], 5), ("Al Fair Omani Halwa", "Muscat", "Oman", ["DATES"], 3),
    ("Sohar Dates & Honey Est", "Sohar", "Oman", ["DATES"], 4), ("Americana Gulf FZE", "Dubai", "UAE", ["SNACK", "CANNED"], 8),
    ("Oman Chocolate Factory", "Muscat", "Oman", ["SNACK"], 4), ("Mondelez Gulf Trading", "Dubai", "UAE", ["SNACK"], 9),
    ("Al Islami Foods FZE", "Dubai", "UAE", ["CANNED"], 8), ("Oman Canning Company", "Sohar", "Oman", ["CANNED"], 5),
    ("Bahwan Trading Food Div", "Muscat", "Oman", ["CANNED", "SNACK"], 4), ("Sadia Gulf Trading", "Jebel Ali", "UAE", ["CANNED"], 10),
    ("National Detergent Company SAOG", "Sohar", "Oman", ["HOME"], 4), ("Unilever Gulf FZE", "Dubai", "UAE", ["HOME", "CARE"], 9),
    ("Procter & Gamble Gulf FZE", "Dubai", "UAE", ["HOME", "CARE"], 9), ("Oman Paper Products LLC", "Rusayl", "Oman", ["HOME"], 4),
    ("Gulf Plastic Industries", "Sohar", "Oman", ["HOME"], 5), ("Henkel Gulf Trading", "Dubai", "UAE", ["HOME"], 10),
    ("Al Jazeera Personal Care LLC", "Muscat", "Oman", ["CARE"], 5), ("Ajmal Perfumes Gulf", "Dubai", "UAE", ["CARE"], 7),
    ("Kimberly-Clark Gulf", "Dubai", "UAE", ["CARE", "HOME"], 9), ("Colgate-Palmolive Arabia", "Riyadh", "Saudi Arabia", ["CARE"], 12),
    ("Muscat Packaging Supplies", "Muscat", "Oman", ["HOME"], 3), ("Salalah Sweets Factory", "Salalah", "Oman", ["DATES", "SNACK"], 6),
    ("Nizwa Food Industries", "Nizwa", "Oman", ["CANNED", "RICE"], 5), ("Barka Water & Juice LLC", "Barka", "Oman", ["BEV"], 3),
    ("Global Foods Trading Est", "Seeb", "Oman", ["SNACK", "BEV"], 4), ("Sur Fisheries Canning", "Sur", "Oman", ["CANNED"], 6),
]

CITY_WEIGHTS = [("Muscat", 30), ("Seeb", 20), ("Sohar", 18), ("Salalah", 14), ("Nizwa", 10), ("Sur", 8)]
CITY_AREAS = {
    "Muscat": ["Ruwi", "Al Khuwair", "Qurum", "Ghubra", "Muttrah", "Wattayah", "Azaiba", "Darsait", "Al Amerat"],
    "Seeb": ["Mawaleh", "Al Hail", "Maabela", "Sur Al Hadid", "Al Khoudh", "Mabelah South"],
    "Sohar": ["Falaj Al Qabail", "Al Hambar", "Sallan", "Al Tareef", "Corniche"],
    "Salalah": ["Al Saada", "Al Haffa", "Al Dahariz", "Awqad", "Al Wadi"],
    "Nizwa": ["Firq", "Al Aqr", "Tanuf Road", "Birkat Al Mouz"],
    "Sur": ["Al Ayjah", "Sur Al Lawatiya", "Bilad Sur"],
}
# customer type, share, payment terms (days), order size factor, visits per month weight
CUSTOMER_TYPES = [
    ("RETAIL", 55, (15, 30), 1.0, 1.0), ("HORECA", 20, (30, 30), 1.3, 0.8), ("WHOLESALE", 10, (30, 45), 4.0, 1.6),
    ("HYPERMARKET", 8, (45, 60), 5.0, 2.2), ("INSTITUTION", 7, (60, 60), 2.0, 0.6),
]
NAME_PREFIX = ["Al Noor", "Al Waha", "Al Bahja", "Al Amal", "Bait Al Khair", "Al Najah", "Al Fajr", "Al Shorooq",
               "Al Manar", "Al Sahwa", "Al Bustan", "Al Qamar", "Dar Al Salam", "Al Rimal", "Al Mouj", "Al Wafa",
               "Al Hamra", "Al Yusr", "Al Baraka", "Al Thuraya", "Al Sharq", "Al Ghaith", "Ras Al Hadd", "Al Ruwais",
               "Majan", "Sohar Star", "Dhofar Pearl", "Al Jabal", "Al Batinah", "Green Valley", "Golden Palm",
               "Blue Lagoon", "Royal", "Union", "Family", "City", "Gulf Star", "Al Kawthar", "Al Salam", "Zahra"]
NAME_SUFFIX = {
    "RETAIL": ["Baqala", "Mini Mart", "Grocery", "Foodstuff Trading", "Supermarket", "Shopping Centre"],
    "HORECA": ["Restaurant", "Cafe", "Hotel", "Catering Services", "Coffee Shop", "Hotel Apartments"],
    "WHOLESALE": ["Wholesale Trading LLC", "General Trading LLC", "Distribution Est", "Foodstuff Wholesale"],
    "HYPERMARKET": ["Hypermarket", "Hypermarket LLC", "Mega Mart", "Supermarket Chain"],
    "INSTITUTION": ["Hospital Canteen", "School Cafeteria", "University Cafeteria", "Camp Catering", "Club"],
}

DEPARTMENTS = [("MGT", "Management"), ("SAL", "Sales"), ("WHS", "Warehouse & Logistics"), ("FIN", "Finance"),
               ("HRA", "HR & Administration"), ("PRC", "Procurement"), ("CSV", "Customer Service"), ("IT", "IT")]
# department code, job title, count, salary range (OMR/month)
JOBS = [
    ("MGT", "General Manager", 1, (3200, 3500)), ("MGT", "Operations Manager", 1, (2200, 2500)),
    ("MGT", "Sohar Branch Manager", 1, (1600, 1900)),
    ("SAL", "Sales Manager", 1, (1500, 1800)), ("SAL", "Sales Executive", 10, (550, 850)),
    ("SAL", "Key Account Executive", 2, (900, 1200)),
    ("WHS", "Warehouse Supervisor", 2, (700, 900)), ("WHS", "Storekeeper", 4, (420, 520)),
    ("WHS", "Delivery Driver", 7, (380, 450)), ("WHS", "Warehouse Helper", 3, (325, 360)),
    ("FIN", "Finance Manager", 1, (1800, 2100)), ("FIN", "Accountant", 2, (750, 950)),
    ("FIN", "Credit Controller", 1, (650, 800)),
    ("HRA", "HR Officer", 1, (800, 950)), ("HRA", "PRO & Admin Officer", 1, (550, 650)),
    ("PRC", "Procurement Officer", 2, (700, 900)), ("CSV", "Customer Service Agent", 4, (450, 550)),
    ("IT", "IT & ERP Administrator", 1, (1000, 1250)),
]
OMANI_FIRST = ["Ahmed", "Mohammed", "Salim", "Khalid", "Said", "Hamed", "Sultan", "Yousuf", "Ali", "Nasser",
               "Fatma", "Aisha", "Maryam", "Zainab", "Shamsa", "Muna", "Rahma", "Huda", "Laila", "Asma"]
OMANI_LAST = ["Al Balushi", "Al Harthy", "Al Hinai", "Al Rawahi", "Al Busaidi", "Al Kindi", "Al Lawati", "Al Siyabi",
              "Al Amri", "Al Maskari", "Al Shukaili", "Al Abri", "Al Saadi", "Al Riyami", "Al Farsi"]
EXPAT = [("Rajesh", "Kumar", "Indian"), ("Anil", "Menon", "Indian"), ("Mohammed", "Rafiq", "Indian"),
         ("Imran", "Khan", "Pakistani"), ("Asif", "Mahmood", "Pakistani"), ("Shahid", "Hussain", "Bangladeshi"),
         ("Jose", "Santos", "Filipino"), ("Maria", "Cruz", "Filipina"), ("Tarek", "Mansour", "Egyptian"),
         ("Priya", "Nair", "Indian"), ("Suresh", "Pillai", "Indian"), ("Kamal", "Hossain", "Bangladeshi")]

# Demo login accounts, one per role (password printed by seed_demo and listed in README).
DEMO_USERS = [
    ("admin@alwadi.om", "Ahmed", "Al Balushi", "Admin", "MGT", "IT & ERP Administrator"),
    ("manager@alwadi.om", "Khalid", "Al Harthy", "Manager", "MGT", "Operations Manager"),
    ("accountant@alwadi.om", "Fatma", "Al Hinai", "Accountant", "FIN", "Accountant"),
    ("sales@alwadi.om", "Salim", "Al Rawahi", "SalesOfficer", "SAL", "Sales Executive"),
    ("store@alwadi.om", "Rajesh", "Kumar", "Storekeeper", "WHS", "Storekeeper"),
    ("hr@alwadi.om", "Maryam", "Al Busaidi", "HROfficer", "HRA", "HR Officer"),
    ("viewer@alwadi.om", "Sultan", "Al Kindi", "Viewer", "MGT", "General Manager"),
]
DEMO_PASSWORD = "AlWadi-Demo-2026!"
