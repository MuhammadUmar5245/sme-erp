"""factory_boy factories shared by all module tests."""
from decimal import Decimal

import factory

from crm.models import Customer
from hr.models import Department, Employee
from inventory.models import Category, Product, Warehouse
from purchasing.models import Supplier


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"CAT{n:03d}")
    name = factory.Sequence(lambda n: f"Category {n}")


class WarehouseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Warehouse
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"WH{n}")
    name = factory.Sequence(lambda n: f"Warehouse {n}")
    city = "Muscat"


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")
    name = factory.Sequence(lambda n: f"Product {n}")
    category = factory.SubFactory(CategoryFactory)
    cost_price = Decimal("1.000")
    sale_price = Decimal("1.500")
    reorder_level = Decimal("10")


class SupplierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Supplier

    code = factory.Sequence(lambda n: f"S{n:04d}")
    name = factory.Sequence(lambda n: f"Supplier {n} LLC")
    payment_terms_days = 30


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    code = factory.Sequence(lambda n: f"C{n:05d}")
    name = factory.Sequence(lambda n: f"Customer {n} Trading")
    city = "Muscat"
    payment_terms_days = 30


class DepartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Department
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"D{n}")
    name = factory.Sequence(lambda n: f"Department {n}")


class EmployeeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Employee

    employee_no = factory.Sequence(lambda n: f"E{n:04d}")
    first_name = "Ahmed"
    last_name = factory.Sequence(lambda n: f"Al Balushi {n}")
    department = factory.SubFactory(DepartmentFactory)
    job_title = "Sales executive"
    hire_date = factory.Faker("date_between", start_date="-5y", end_date="-1y")
    basic_salary = Decimal("650.000")
