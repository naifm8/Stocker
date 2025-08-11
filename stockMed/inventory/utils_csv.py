import csv
from io import StringIO
from .models import Product, Category, Supplier
from django.utils.dateparse import parse_date

def export_products_to_csv(products):
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'name', 'category', 'suppliers', 'batch_number',
        'quantity_in_stock', 'reorder_level', 'unit_price', 'expiry_date'
    ])

    for p in products:
        supplier_names = ", ".join([s.name for s in p.suppliers.all()])
        writer.writerow([
            p.name, p.category.name, supplier_names, p.batch_number,
            p.quantity_in_stock, p.reorder_level, p.unit_price, p.expiry_date
        ])

    return output.getvalue()

def import_products_from_csv(file):
    decoded = file.read().decode('utf-8')
    io_string = StringIO(decoded)
    reader = csv.DictReader(io_string)

    errors = []
    for row in reader:
        try:
            category, _ = Category.objects.get_or_create(name=row['category'])

            product, created = Product.objects.get_or_create(
                name=row['name'],
                batch_number=row['batch_number'],
                defaults={
                    'category': category,
                    'quantity_in_stock': int(row['quantity_in_stock']),
                    'reorder_level': int(row['reorder_level']),
                    'unit_price': float(row['unit_price']),
                    'expiry_date': parse_date(row['expiry_date']),
                }
            )
            if not created:
                product.quantity_in_stock = int(row['quantity_in_stock'])
                product.reorder_level = int(row['reorder_level'])
                product.unit_price = float(row['unit_price'])
                product.expiry_date = parse_date(row['expiry_date'])
                product.save()

            supplier_names = [name.strip() for name in row['suppliers'].split(',')]
            for name in supplier_names:
                if name:
                    supplier, _ = Supplier.objects.get_or_create(name=name)
                    product.suppliers.add(supplier)

        except Exception as e:
            errors.append(str(e))

    return errors
