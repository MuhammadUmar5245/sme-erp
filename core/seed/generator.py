"""Deterministic demo-data generator for Al Wadi Trading & Distribution LLC.

Simulates 18 months of trading day by day through the real business services (so stock, ledger and
documents stay consistent): Ramadan/Eid peaks, a slow June-August summer, a Khareef boost in Salalah,
weekly replenishment purchasing, realistic customer payment behaviour (for AR aging), returns,
feedback, complaints, POS sales, operating expenses, employees and leave.
"""
import datetime
import heapq
import itertools
import math
import random
from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts import audit
from accounts.services import create_user, sync_role_permissions
from core import oman_calendar as cal
from crm.models import Contact, Customer, Feedback, Interaction
from finance import chart
from finance import services as finance
from finance.models import JournalEntry
from hr import services as hr_services
from hr.models import Department, Employee, LeaveRequest
from inventory import services as inventory
from inventory.models import Category, Product, Warehouse
from purchasing import services as purchasing
from purchasing.models import Supplier
from sales import services as sales
from sales.models import Invoice, Payment

from . import catalog

D = Decimal
Q3 = Decimal("0.001")


def add_months(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    last = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return day.replace(year=year, month=month, day=min(day.day, last))


def money(value):
    return D(str(value)).quantize(Q3)


class DemoSeeder:
    def __init__(self, today=None, months=18, target_invoices=8000, seed=42, log=print):
        self.rng = random.Random(seed)
        self.today = today or timezone.localdate()
        self.start = add_months(self.today, -months) + datetime.timedelta(days=1)
        self.target_invoices = target_invoices
        self.log = log
        self.events = []
        self.counter = itertools.count()
        self.stock = defaultdict(int)  # (product_id, warehouse_id) -> units on hand
        self.on_order = defaultdict(int)
        self.outstanding = {}  # invoice_id -> balance due
        self.sold_units = defaultdict(int)  # (product_id, warehouse_id) -> units sold in simulation
        self.stats = defaultdict(int)

    # ------------------------------------------------------------------ helpers
    def schedule(self, day, kind, payload):
        heapq.heappush(self.events, (day, next(self.counter), kind, payload))

    def weighted(self, items, weights):
        return self.rng.choices(items, weights=weights, k=1)[0]

    def moment(self, day, hour=9):
        return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hour, 0)))

    # ------------------------------------------------------------------ master data
    def create_people(self):
        sync_role_permissions()
        finance.seed_chart_of_accounts()
        self.departments = {code: Department.objects.create(code=code, name=name)
                            for code, name in catalog.DEPARTMENTS}
        User = get_user_model()
        self.users = {}
        for email, first, last, role, dept, _job in catalog.DEMO_USERS:
            user = create_user(email, catalog.DEMO_PASSWORD, roles=[role], first_name=first, last_name=last,
                               department=self.departments[dept], phone=f"+9689{self.rng.randint(1000000, 9999999)}")
            if role == "Admin":
                user.is_superuser = True
                user.save(update_fields=["is_superuser"])
            self.users[role] = user
        self.powerbi_user = create_user("powerbi@alwadi.om", catalog.DEMO_PASSWORD, roles=["Viewer"],
                                        first_name="Power BI", last_name="Service")

        # Employees (45). Demo users are linked to their employee records.
        employees, demo_by_job = [], defaultdict(list)
        for email, first, last, role, dept, job in catalog.DEMO_USERS:
            demo_by_job[job].append((first, last, self.users[role]))
        number = itertools.count(1)
        self.sales_reps = []
        for dept_code, job, count, (low, high) in catalog.JOBS:
            for _ in range(count):
                if demo_by_job[job]:
                    first, last, user = demo_by_job[job].pop(0)
                    nationality = "Indian" if last == "Kumar" else "Omani"
                else:
                    user = None
                    if self.rng.random() < 0.55 or dept_code in ("MGT", "HRA"):
                        first, last, nationality = (self.rng.choice(catalog.OMANI_FIRST),
                                                    self.rng.choice(catalog.OMANI_LAST), "Omani")
                    else:
                        first, last, nationality = self.rng.choice(catalog.EXPAT)
                n = next(number)
                if job == "Sales Executive" and user is None and len(self.sales_reps) < 4:
                    user = create_user(f"rep{len(self.sales_reps) + 1}@alwadi.om", catalog.DEMO_PASSWORD,
                                       roles=["SalesOfficer"], first_name=first, last_name=last,
                                       department=self.departments["SAL"])
                if job == "Sales Executive" and user is not None:
                    self.sales_reps.append(user)
                hire = datetime.date(self.rng.randint(2012, 2024), self.rng.randint(1, 12), self.rng.randint(1, 28))
                employees.append(Employee.objects.create(
                    employee_no=f"AW{n:03d}", user=user, first_name=first, last_name=last,
                    department=self.departments[dept_code], job_title=job, hire_date=hire,
                    phone=f"+9689{self.rng.randint(1000000, 9999999)}",
                    email=user.email if user else f"{first.lower()}.{last.split()[-1].lower()}{n}@alwadi.om",
                    city="Sohar" if "Sohar" in job else self.weighted(["Muscat", "Seeb", "Sohar"], [6, 3, 1]),
                    nationality=nationality, basic_salary=money(self.rng.randint(low, high)),
                    national_id=str(self.rng.randint(10_000_000, 99_999_999)),
                    bank_iban=f"OM{self.rng.randint(10, 99)}018{self.rng.randint(10**15, 10**16 - 1)}",
                    annual_leave_days=30,
                ))
        self.employees = employees
        self.payroll = sum((e.basic_salary for e in employees), D(0))

    def create_master_data(self):
        self.mct = Warehouse.objects.create(code="MCT", name="Muscat Main Warehouse", city="Muscat",
                                            address="Rusayl Industrial Estate, Muscat")
        self.soh = Warehouse.objects.create(code="SOH", name="Sohar Warehouse", city="Sohar",
                                            address="Sohar Industrial Estate, Sohar")
        self.warehouses = [self.mct, self.soh]

        # Suppliers
        self.suppliers, self.supplier_lead, supplier_by_cat = [], {}, defaultdict(list)
        for i, (name, city, country, cats, lead) in enumerate(catalog.SUPPLIERS, start=1):
            supplier = Supplier.objects.create(
                code=f"S{i:04d}", name=name, city=city, country=country,
                contact_person=f"{self.rng.choice(catalog.OMANI_FIRST)} {self.rng.choice(catalog.OMANI_LAST)}"
                if country == "Oman" else self.rng.choice(catalog.EXPAT)[0] + " " + self.rng.choice(catalog.EXPAT)[1],
                phone=f"+968{self.rng.choice('29')}{self.rng.randint(1000000, 9999999)}",
                email=f"sales@{name.split()[0].lower().replace(chr(39), '')}{i}.com",
                vat_number=f"OM11{self.rng.randint(10**7, 10**8 - 1)}" if country == "Oman" else "",
                payment_terms_days=self.rng.choice([30, 30, 45, 60]),
            )
            self.suppliers.append(supplier)
            self.supplier_lead[supplier.pk] = lead
            for cat in cats:
                supplier_by_cat[cat].append(supplier)

        # Categories and products
        self.products, self.product_cat, self.product_supplier, self.popularity = [], {}, {}, {}
        sku = itertools.count(1)
        margins = {"RICE": (1.16, 1.24), "BEV": (1.22, 1.35), "DAIRY": (1.15, 1.25), "DATES": (1.28, 1.45),
                   "SNACK": (1.25, 1.40), "CANNED": (1.18, 1.30), "HOME": (1.22, 1.35), "CARE": (1.25, 1.40)}
        for code, name, items in catalog.CATEGORIES:
            category = Category.objects.create(code=code, name=name)
            for item_name, unit, cost in items:
                cost = money(cost)
                low, high = margins[code]
                price = money(round(float(cost) * self.rng.uniform(low, high) / 0.005) * 0.005)
                product = Product.objects.create(
                    sku=f"{code[:3]}-{next(sku):04d}", name=item_name, category=category, unit=unit,
                    barcode=f"629{self.rng.randint(10**9, 10**10 - 1)}", cost_price=cost, sale_price=price,
                )
                self.products.append(product)
                self.product_cat[product.pk] = code
                self.product_supplier[product.pk] = self.rng.choice(supplier_by_cat[code])
                self.popularity[product.pk] = catalog.CATEGORY_PROFILE[code][0] * self.rng.uniform(0.35, 1.8)
        self.by_category = defaultdict(list)
        for p in self.products:
            self.by_category[self.product_cat[p.pk]].append(p)
        # A few products have an unreliable supplier: they will run out of stock.
        self.unreliable = set(self.rng.sample([p.pk for p in self.products], 5))

        # Customers (300) + the walk-in cash customer used by the POS
        self.customers, self.customer_profile = [], {}
        used = set()
        reps = self.sales_reps or [self.users["SalesOfficer"]]
        cities = [c for c, _ in catalog.CITY_WEIGHTS]
        city_w = [w for _, w in catalog.CITY_WEIGHTS]
        types = catalog.CUSTOMER_TYPES
        for n in range(1, 301):
            ctype = self.weighted(types, [t[1] for t in types])
            city = self.weighted(cities, city_w)
            area = self.rng.choice(catalog.CITY_AREAS[city])
            for _ in range(20):
                base = f"{self.rng.choice(catalog.NAME_PREFIX)} {self.rng.choice(catalog.NAME_SUFFIX[ctype[0]])}"
                name = base if base not in used else f"{base} {area}"
                if name not in used:
                    break
            used.add(name)
            terms = self.rng.choice(ctype[2])
            customer = Customer.objects.create(
                code=f"C{n:05d}", name=name, customer_type=ctype[0], city=city, address=f"{area}, {city}",
                phone=f"+968{self.rng.choice('9729')}{self.rng.randint(1000000, 9999999)}",
                email=f"orders{n}@{name.split()[1].lower().replace(chr(39), '')}.om" if self.rng.random() < 0.6 else "",
                vat_number=f"OM11{self.rng.randint(10**7, 10**8 - 1)}" if ctype[0] != "RETAIL" else "",
                credit_limit=money(self.rng.choice([500, 1000, 1500, 2000, 3000]) * ctype[3]),
                payment_terms_days=terms,
            )
            Contact.objects.create(customer=customer, name=f"{self.rng.choice(catalog.OMANI_FIRST)} "
                                   f"{self.rng.choice(catalog.OMANI_LAST)}", position=self.rng.choice(
                                       ["Owner", "Purchasing Manager", "Store Manager", "Accountant"]),
                                   phone=customer.phone, is_primary=True)
            behaviour = self.weighted(["punctual", "normal", "slow", "bad"], [30, 45, 20, 5])
            self.customers.append(customer)
            self.customer_profile[customer.pk] = {
                "type": ctype, "behaviour": behaviour, "rep": self.rng.choice(reps),
                "satisfaction": min(4.9, max(2.8, self.rng.gauss(4.15, 0.45))),
                "warehouse": self.soh if city == "Sohar" else self.mct,
                "activity": self.rng.uniform(0.4, 1.6) * ctype[4],
            }
        self.walk_in = Customer.objects.create(code="CASH", name="Cash customer (POS walk-in)", customer_type="RETAIL",
                                               city="Muscat", payment_terms_days=0, notes="Used by the POS integration")

    # ------------------------------------------------------------------ demand model
    def season(self, day):
        factor = 1.0
        if cal.is_ramadan(day):
            factor *= 1.55
        if cal.is_pre_eid(day):
            factor *= 1.7
        if cal.is_eid(day):
            factor *= 0.35
        if day.month in (6, 7, 8):
            factor *= 0.72
        if day.month in (11, 12):
            factor *= 1.1
        return factor

    def weekday_factor(self, day):
        return {4: 0.12, 5: 0.6}.get(day.weekday(), 1.0)  # Friday, Saturday

    def day_weight(self, day):
        growth = 1 + 0.12 * (day - self.start).days / 365
        return self.weekday_factor(day) * self.season(day) * growth

    def category_weights(self, day):
        ramadan = cal.is_ramadan(day) or (cal.is_pre_eid(day, 15) and day.month < 5)
        summer = day.month in (6, 7, 8)
        weights = []
        for code, _name, _items in catalog.CATEGORIES:
            pop, boost, summer_factor = catalog.CATEGORY_PROFILE[code]
            weights.append(pop * (boost if ramadan else 1) * (summer_factor if summer else 1))
        return [c[0] for c in catalog.CATEGORIES], weights

    def customer_weight(self, customer, day):
        profile = self.customer_profile[customer.pk]
        weight = profile["activity"]
        if customer.city == "Salalah" and cal.is_khareef(day):
            weight *= 2.4  # Khareef tourist season
        elif day.month in (6, 7, 8):
            weight *= 0.9
        if profile["type"][0] == "HYPERMARKET" and (cal.is_ramadan(day) or cal.is_pre_eid(day)):
            weight *= 1.3
        return weight

    def basket(self, customer, day, pos=False):
        if pos:
            n_lines, size = self.rng.randint(1, 4), 0.35
        else:
            ctype = self.customer_profile[customer.pk]["type"]
            lo, hi = {"RETAIL": (2, 5), "HORECA": (2, 6), "WHOLESALE": (4, 8), "HYPERMARKET": (5, 9),
                      "INSTITUTION": (3, 7)}[ctype[0]]
            n_lines, size = self.rng.randint(lo, hi), ctype[3]
        cats, cat_w = self.category_weights(day) if day else ([c[0] for c in catalog.CATEGORIES],
                                                              [catalog.CATEGORY_PROFILE[c[0]][0] for c in catalog.CATEGORIES])
        lines, seen = [], set()
        for _ in range(n_lines):
            cat = self.weighted(cats, cat_w)
            options = self.by_category[cat]
            product = self.weighted(options, [self.popularity[p.pk] for p in options])
            if product.pk in seen:
                continue
            seen.add(product.pk)
            base = {"CTN": (1, 4), "BAG": (1, 6)}.get(product.unit, (2, 12))
            qty = max(1, round(self.rng.randint(*base) * size * self.rng.uniform(0.7, 1.3)))
            lines.append([product, qty])
        return lines

    def estimate_demand(self):
        """Monte-Carlo estimate of average daily units per product per warehouse (drives reorder levels)."""
        sample = random.Random(7)
        saved, self.rng = self.rng, sample
        units = defaultdict(float)
        n = 25000
        weights = [self.customer_profile[c.pk]["activity"] for c in self.customers]
        for _ in range(n):
            if sample.random() < 0.1:
                customer, wh = self.walk_in, self.mct
                lines = self.basket(customer, None, pos=True)
            else:
                customer = sample.choices(self.customers, weights=weights)[0]
                wh = self.customer_profile[customer.pk]["warehouse"]
                lines = self.basket(customer, None)
            for product, qty in lines:
                units[(product.pk, wh.pk)] += qty
        self.rng = saved
        days = (self.today - self.start).days + 1
        invoices_per_day = self.target_invoices / days
        self.daily_demand = {key: value / n * invoices_per_day for key, value in units.items()}
        for product in self.products:  # floor so slow movers are still stocked and replenished
            for wh in self.warehouses:
                key = (product.pk, wh.pk)
                self.daily_demand[key] = max(self.daily_demand.get(key, 0), 0.3 if wh == self.mct else 0.15)
        for product in self.products:
            total = sum(self.daily_demand.get((product.pk, wh.pk), 0) for wh in self.warehouses)
            lead = self.supplier_lead[self.product_supplier[product.pk].pk]
            product.reorder_level = D(max(5, math.ceil(total * (lead + 7))))
            product.reorder_quantity = D(max(10, math.ceil(total * 28)))
            product.save(update_fields=["reorder_level", "reorder_quantity"])

    # ------------------------------------------------------------------ opening position
    def opening_position(self):
        start = self.start
        finance.post_journal(start, "Owner's capital introduced", [(chart.BANK, 150000, 0), (chart.CAPITAL, 0, 150000)],
                             JournalEntry.Source.OPENING, reference="OPENING")
        value = D(0)
        moment = self.moment(start, 6)
        for product in self.products:
            for wh in self.warehouses:
                qty = math.ceil(self.daily_demand.get((product.pk, wh.pk), 0) * 45)
                if product.pk in self.unreliable:
                    qty = math.ceil(qty * 0.5)
                if qty <= 0:
                    continue
                inventory.record_opening_stock(product, wh, qty, product.cost_price, movement_date=moment)
                self.stock[(product.pk, wh.pk)] += qty
                value += money(qty * product.cost_price)
        finance.post_journal(start, "Opening stock valuation", [(chart.INVENTORY, value, 0),
                                                                (chart.OPENING_BALANCE_EQUITY, 0, value)],
                             JournalEntry.Source.OPENING, reference="OPENING")

    # ------------------------------------------------------------------ purchasing
    def replenish(self, day):
        """Weekly (Sunday) review: order up to cover lead time + 3 weeks, adjusted for the coming season."""
        horizon = [day + datetime.timedelta(days=i) for i in range(28)]
        outlook = sum(self.season(d) * self.weekday_factor(d) for d in horizon) / sum(
            self.weekday_factor(d) for d in horizon)
        growth = 1 + 0.12 * (day - self.start).days / 365
        orders = defaultdict(list)
        for product in self.products:
            supplier = self.product_supplier[product.pk]
            lead = self.supplier_lead[supplier.pk]
            unreliable = product.pk in self.unreliable
            for wh in self.warehouses:
                daily = self.daily_demand.get((product.pk, wh.pk), 0) * outlook * growth
                if daily <= 0:
                    continue
                key = (product.pk, wh.pk)
                position = self.stock[key] + self.on_order[key]
                reorder_point = daily * (lead + 14)  # includes safety stock for lumpy B2B orders
                if unreliable:
                    if (self.today - day).days < 35 or self.rng.random() < 0.6:  # supplier stopped delivering
                        continue  # supplier failed to confirm the order
                    reorder_point *= 0.5
                if position < reorder_point:
                    target = daily * (lead + 42)  # about six weeks of cover per order
                    qty = max(5, int(math.ceil((target - position) / 5.0)) * 5)
                    orders[(supplier.pk, wh.pk)].append((product, qty))
        manager = self.users["Manager"]
        for (supplier_id, wh_id), lines in orders.items():
            supplier = next(s for s in self.suppliers if s.pk == supplier_id)
            wh = self.mct if wh_id == self.mct.pk else self.soh
            po = purchasing.create_purchase_order(
                supplier, wh, [{"product": p, "quantity": q, "unit_cost": money(float(p.cost_price) *
                                                                                 self.rng.uniform(0.97, 1.04))}
                               for p, q in lines], user=manager, order_date=day)
            purchasing.approve_purchase_order(po, manager)
            lead = self.supplier_lead[supplier_id] * (3 if any(p.pk in self.unreliable for p, _ in lines) else 1)
            arrival = day + datetime.timedelta(days=lead + self.rng.randint(0, 2))
            for p, q in lines:
                self.on_order[(p.pk, wh_id)] += q
            self.schedule(arrival, "receive", po)
            self.stats["purchase_orders"] += 1

    def receive(self, day, po):
        receipt = purchasing.receive_goods(po, user=self.users["Storekeeper"], receipt_date=day)
        for line in receipt.lines.all():
            key = (line.product_id, receipt.warehouse_id)
            self.stock[key] += int(line.quantity)
            self.on_order[key] -= int(line.quantity)
        self.schedule(day + datetime.timedelta(days=self.rng.randint(0, 4)), "bill", po)

    def bill(self, day, po):
        bill = purchasing.create_bill_from_po(po, f"{po.supplier.code}-INV-{self.rng.randint(10000, 99999)}",
                                              day, self.users["Accountant"])
        delay = self.rng.randint(-5, 12)
        self.schedule(bill.due_date + datetime.timedelta(days=delay), "pay_bill", bill)

    def pay_bill(self, day, bill):
        method = self.weighted(["BANK", "CHEQUE"], [80, 20])
        purchasing.pay_supplier_bill(bill, bill.balance_due, day, method, f"TRF-{self.rng.randint(100000, 999999)}",
                                     self.users["Accountant"])
        self.stats["supplier_payments"] += 1

    # ------------------------------------------------------------------ sales
    def sell(self, day, customer, pos=False):
        profile = None if pos else self.customer_profile[customer.pk]
        wh = self.mct if pos else profile["warehouse"]
        wanted = self.basket(customer, day, pos)
        lines, short = [], False
        for product, qty in wanted:
            available = self.stock[(product.pk, wh.pk)]
            if available <= 0:
                short = True
                self.stats["stockout_lines"] += 1
                continue
            if qty > available:
                qty, short = available, True
            discount = 0
            if profile and profile["type"][0] in ("HYPERMARKET", "WHOLESALE"):
                discount = self.rng.choice([3, 5, 5, 7])
            elif profile and self.rng.random() < 0.1:
                discount = 2
            lines.append({"product": product, "quantity": qty, "discount_pct": discount})
        if not lines:
            return None
        rep = profile["rep"] if profile else None
        if not pos and self.rng.random() < 0.1:
            order = sales.create_sales_order(customer, wh, lines, user=rep, order_date=day)
            sales.confirm_sales_order(order, rep)
            invoice = sales.invoice_sales_order(order, user=rep, invoice_date=day)
        else:
            invoice = sales.create_invoice(
                customer, wh, lines, user=rep, invoice_date=day, salesperson=rep,
                source=Invoice.Source.POS if pos else Invoice.Source.MANUAL,
                external_ref=f"MCT-POS1-{self.stats['pos_sales'] + 1:06d}" if pos else "")
        for line in lines:
            self.stock[(line["product"].pk, wh.pk)] -= int(line["quantity"])
            self.sold_units[(line["product"].pk, wh.pk)] += int(line["quantity"])
        self.outstanding[invoice.pk] = invoice.total
        self.stats["invoices"] += 1
        if pos:
            self.stats["pos_sales"] += 1
            sales.record_payment(invoice, invoice.total, day, self.weighted(["CASH", "CARD"], [45, 55]),
                                 invoice.external_ref)
            self.outstanding[invoice.pk] = D(0)
            return invoice
        self.plan_payment(invoice, profile)
        self.after_sale(day, invoice, customer, profile, short)
        return invoice

    def plan_payment(self, invoice, profile):
        behaviour = profile["behaviour"]
        if behaviour == "bad" and self.rng.random() < 0.35:
            return  # never pays -> 90+ days overdue
        delay = {"punctual": (-12, 2), "normal": (-3, 20), "slow": (10, 55), "bad": (45, 110)}[behaviour]
        pay_day = invoice.due_date + datetime.timedelta(days=self.rng.randint(*delay))
        pay_day = max(pay_day, invoice.invoice_date)
        method = self.weighted(["BANK", "CHEQUE", "CASH", "CARD"], [55, 20, 15, 10])
        if self.rng.random() < 0.15:  # partial payment first
            first = money(float(invoice.total) * self.rng.uniform(0.3, 0.7))
            self.schedule(pay_day, "pay_invoice", (invoice, first, method))
            self.schedule(pay_day + datetime.timedelta(days=self.rng.randint(10, 40)), "pay_invoice",
                          (invoice, None, method))
        else:
            self.schedule(pay_day, "pay_invoice", (invoice, None, method))

    def after_sale(self, day, invoice, customer, profile, short):
        if self.rng.random() < 0.02:
            self.schedule(day + datetime.timedelta(days=self.rng.randint(1, 10)), "credit", invoice)
        if self.rng.random() < (0.06 if short else 0.012):
            self.schedule(day + datetime.timedelta(days=self.rng.randint(0, 3)), "complaint",
                          (invoice, customer, "Short delivery - items out of stock" if short else None))
        if self.rng.random() < 0.13:
            score = profile["satisfaction"] + self.rng.gauss(0, 0.7) - (1.1 if short else 0)
            self.schedule(day + datetime.timedelta(days=self.rng.randint(1, 7)), "feedback",
                          (invoice, customer, int(min(5, max(1, round(score))))))

    def pay_invoice(self, day, payload):
        invoice, amount, method = payload
        balance = self.outstanding.get(invoice.pk, D(0))
        amount = balance if amount is None else min(amount, balance)
        if amount <= 0:
            return
        sales.record_payment(invoice, amount, day, method, f"{method}-{self.rng.randint(100000, 999999)}")
        self.outstanding[invoice.pk] = balance - amount
        self.stats["payments"] += 1

    def credit(self, day, invoice):
        line = self.rng.choice(list(invoice.lines.all()))
        qty = max(1, int(line.quantity) // self.rng.choice([2, 3, 4, 10]))
        note = sales.create_credit_note(invoice, [{"invoice_line": line, "quantity": qty}],
                                        self.rng.choice(["Damaged in transit", "Expired stock returned",
                                                         "Wrong item delivered", "Price dispute"]),
                                        credit_date=day, restock=self.rng.random() < 0.7,
                                        user=self.users["Accountant"])
        if note.restock:
            self.stock[(line.product_id, invoice.warehouse_id)] += qty
        self.outstanding[invoice.pk] = self.outstanding.get(invoice.pk, D(0)) - note.total
        self.stats["credit_notes"] += 1

    COMMENTS = {
        5: ["Excellent service and on-time delivery.", "Very happy with the quality.", "Great prices for Ramadan stock."],
        4: ["Good service.", "Delivery was on time.", "Driver was polite and helpful."],
        3: ["Average, delivery was a bit late.", "Prices could be better.", "OK but some cartons were dented."],
        2: ["Late delivery again.", "Missing items in the order.", "Sales rep did not call back."],
        1: ["Very poor service, items out of stock.", "Damaged goods and no replacement.", "Wrong invoice amount."],
    }

    def feedback(self, day, payload):
        invoice, customer, score = payload
        Feedback.objects.create(customer=customer, invoice=invoice, feedback_date=day, score=score,
                                channel=self.weighted(["SURVEY", "CALL", "WHATSAPP", "VISIT"], [40, 25, 25, 10]),
                                comment=self.rng.choice(self.COMMENTS[score]))
        self.stats["feedback"] += 1

    def complaint(self, day, payload):
        invoice, customer, subject = payload
        subject = subject or self.rng.choice(["Late delivery", "Damaged cartons", "Wrong item delivered",
                                              "Invoice amount query", "Expired product on shelf"])
        status = Interaction.Status.OPEN if (self.today - day).days < 21 and self.rng.random() < 0.6 \
            else Interaction.Status.CLOSED
        Interaction.objects.create(customer=customer, interaction_type=Interaction.Type.COMPLAINT,
                                   interaction_date=self.moment(day, 11), subject=subject, status=status,
                                   notes=f"Related to {invoice.number}", user=self.users["SalesOfficer"])
        self.stats["complaints"] += 1

    def routine_interactions(self, day):
        if day.weekday() in (4, 5):
            return
        for _ in range(self.rng.randint(1, 5)):
            customer = self.rng.choice(self.customers)
            kind = self.weighted([Interaction.Type.VISIT, Interaction.Type.CALL, Interaction.Type.EMAIL], [45, 40, 15])
            subject = self.rng.choice(["Monthly sales visit", "New price list shared", "Ramadan promotion offer",
                                       "Payment follow-up", "Order confirmation", "Product range review",
                                       "Credit limit discussion"])
            Interaction.objects.create(customer=customer, interaction_type=kind, interaction_date=self.moment(day, 10),
                                       subject=subject, user=self.customer_profile[customer.pk]["rep"],
                                       status=Interaction.Status.CLOSED)
            self.stats["interactions"] += 1

    # ------------------------------------------------------------------ expenses
    def monthly_expenses(self, day):
        accountant = self.users["Accountant"]
        summer = day.month in (5, 6, 7, 8, 9)
        items = [
            ("6100", "Rusayl Properties LLC", "Muscat warehouse rent", 1800, 5),
            ("6100", "Sohar Industrial Estate", "Sohar warehouse rent", 950, 5),
            ("6100", "Al Khuwair Towers", "Head office rent", 1200, 5),
            ("6200", "Nama Electricity", "Electricity - warehouses and office",
             self.rng.randint(1400, 1900) if summer else self.rng.randint(700, 1000), 5),
            ("6200", "Nama Water Services", "Water", self.rng.randint(80, 140), 5),
            ("6500", "Omantel", "Internet, phones and cloud ERP hosting", self.rng.randint(380, 460), 5),
            ("6600", "Bank Muscat", "Bank charges", self.rng.randint(25, 70), 0),
            ("6700", "Al Jazeera Auto Service", "Delivery vehicle maintenance", self.rng.randint(200, 650), 5),
            ("6900", "Various", "Sundry office expenses", self.rng.randint(60, 220), 5),
        ]
        if cal.is_ramadan(day + datetime.timedelta(days=20)) or day.month == 11:
            items.append(("6400", "Times of Oman Media", "Ramadan / National Day promotion",
                          self.rng.randint(900, 1800), 5))
        for code, payee, description, amount, vat in items:
            finance.record_expense(day, code, payee, description, amount, vat_rate=vat, user=accountant,
                                   reference=f"{payee[:3].upper()}-{day:%Y%m}")
            self.stats["expenses"] += 1

    def payroll_run(self, day):
        finance.record_expense(day, "6000", "Staff payroll (WPS)", f"Salaries {day:%B %Y} - {len(self.employees)} staff",
                               self.payroll, vat_rate=0, user=self.users["Accountant"], reference=f"PAY-{day:%Y%m}")
        self.stats["expenses"] += 1

    def weekly_fuel(self, day):
        finance.record_expense(day, "6300", "Shell Oman Marketing", "Fuel for delivery fleet",
                               self.rng.randint(160, 280), vat_rate=0, user=self.users["Accountant"],
                               reference=f"FUEL-{day:%Y%m%d}")
        self.stats["expenses"] += 1

    # ------------------------------------------------------------------ HR
    def leave(self):
        manager = self.users["Manager"]
        hr_user = self.users["HROfficer"]
        for employee in self.employees:
            for year in sorted({self.start.year, self.today.year}):
                for _ in range(self.rng.randint(1, 2)):
                    month = self.weighted(list(range(1, 13)), [1, 1, 2, 3, 2, 4, 5, 5, 2, 1, 1, 3])
                    start = datetime.date(year, month, self.rng.randint(1, 20))
                    if start < self.start:
                        continue
                    end = start + datetime.timedelta(days=self.rng.randint(4, 16))
                    self._leave(employee, "ANNUAL", start, end, manager, hr_user)
                if self.rng.random() < 0.35:
                    start = datetime.date(year, self.rng.randint(1, 12), self.rng.randint(1, 26))
                    if start >= self.start:
                        self._leave(employee, "SICK", start, start + datetime.timedelta(days=self.rng.randint(0, 2)),
                                    manager, hr_user)

    def _leave(self, employee, kind, start, end, manager, hr_user):
        try:
            request = hr_services.submit_leave_request(employee, kind, start, end, "Seeded leave request", hr_user)
        except hr_services.LeaveError:
            return
        self.stats["leave_requests"] += 1
        if start > self.today - datetime.timedelta(days=5) and self.rng.random() < 0.7:
            return  # still pending
        approver = hr_user if employee.user_id == manager.pk else manager
        try:
            if self.rng.random() < 0.9:
                hr_services.approve_leave(request, approver)
            else:
                hr_services.reject_leave(request, approver, "Peak season - please reschedule")
        except hr_services.LeaveError:
            pass

    # ------------------------------------------------------------------ main loop
    def simulate(self):
        days = [self.start + datetime.timedelta(days=i) for i in range((self.today - self.start).days + 1)]
        weights = [self.day_weight(d) for d in days]
        scale = self.target_invoices * 0.9 / sum(weights)  # 90% B2B, ~10% POS
        pos_per_day = self.target_invoices * 0.1 / len(days)
        current_month = None
        for day, weight in zip(days, weights):
            if day.month != current_month:
                current_month = day.month
                self.log(f"  {day:%b %Y}: {self.stats['invoices']} invoices so far")
            while self.events and self.events[0][0] <= day:
                _when, _n, kind, payload = heapq.heappop(self.events)
                getattr(self, kind)(day, payload)
            if day.weekday() == 6:  # Sunday: purchasing review and fuel
                self.replenish(day)
                self.weekly_fuel(day)
            if day.day == 1:
                self.monthly_expenses(day)
            if day.day == 26:
                self.payroll_run(day)
            expected = weight * scale
            count = max(0, int(round(self.rng.gauss(expected, math.sqrt(max(expected, 1)) * 0.6))))
            customer_weights = [self.customer_weight(c, day) for c in self.customers]
            for _ in range(count):
                self.sell(day, self.rng.choices(self.customers, weights=customer_weights)[0])
            if day.weekday() != 4:
                for _ in range(max(0, int(round(self.rng.gauss(pos_per_day * 1.15, 1))))):
                    self.sell(day, self.walk_in, pos=True)
            self.routine_interactions(day)

    def open_documents(self):
        """A handful of in-flight documents at 'today' for the demo (draft/confirmed orders)."""
        rep = self.users["SalesOfficer"]
        for i in range(8):
            customer = self.rng.choice(self.customers)
            wh = self.customer_profile[customer.pk]["warehouse"]
            lines = [{"product": p, "quantity": q} for p, q in self.basket(customer, self.today)]
            order = sales.create_sales_order(customer, wh, lines, user=rep,
                                             order_date=self.today - datetime.timedelta(days=self.rng.randint(0, 3)))
            if i % 2:
                sales.confirm_sales_order(order, rep)
        supplier = self.rng.choice(self.suppliers)
        purchasing.create_purchase_order(supplier, self.mct, [{"product": self.rng.choice(self.products),
                                                               "quantity": 50}], user=self.users["Manager"],
                                         order_date=self.today, notes="Draft awaiting approval")

    def run(self):
        with audit.disabled(), transaction.atomic():
            self.log("Creating users, roles, employees ...")
            self.create_people()
            self.log("Creating warehouses, suppliers, products, customers ...")
            self.create_master_data()
            self.estimate_demand()
            self.opening_position()
            self.log(f"Simulating trading from {self.start} to {self.today} ...")
            self.simulate()
            self.open_documents()
            self.log("Creating leave records ...")
            self.leave()
            self.integrations()
        return self.summary()

    def integrations(self):
        from rest_framework.authtoken.models import Token

        from integrations.services import create_api_key

        self.powerbi_token = Token.objects.create(user=self.powerbi_user).key
        _key, self.pos_api_key = create_api_key("Muscat showroom POS 1", self.mct, self.walk_in)

    def summary(self):
        from inventory.services import low_stock_products

        stockouts = sum(1 for p in low_stock_products() if p.on_hand_qty <= 0)
        return {
            "Users": get_user_model().objects.count(),
            "Employees": Employee.objects.count(),
            "Leave requests": LeaveRequest.objects.count(),
            "Customers": Customer.objects.count(),
            "Suppliers": Supplier.objects.count(),
            "Categories": Category.objects.count(),
            "Products": Product.objects.count(),
            "Warehouses": Warehouse.objects.count(),
            "Purchase orders": self.stats["purchase_orders"],
            "Invoices": Invoice.objects.count(),
            "  of which POS": Invoice.objects.filter(source="POS").count(),
            "Customer payments": Payment.objects.count(),
            "Credit notes": self.stats["credit_notes"],
            "Feedback records": Feedback.objects.count(),
            "Interactions": Interaction.objects.count(),
            "Expenses": self.stats["expenses"],
            "Journal entries": JournalEntry.objects.count(),
            "Products out of stock now": stockouts,
            "Products below reorder level": len(low_stock_products()),
            "Order lines lost to stock-outs": self.stats["stockout_lines"],
            "Open receivables (OMR)": f"{sum(v for v in self.outstanding.values() if v > 0):,.3f}",
        }
