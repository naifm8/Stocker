from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from .models import Category, Supplier, Product
from .forms import CategoryForm, SupplierForm, ProductForm
from django.utils import timezone
from datetime import timedelta
from .utils import send_inventory_alert
from django.contrib import messages
from django.http import HttpResponse
from .utils_csv import export_products_to_csv, import_products_from_csv
from django.db.models import Sum, F, Q
from accounts.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .utils import get_inventory_alerts

def is_admin(u): return u.is_authenticated and u.role == 'admin'
def is_employee(u): return u.is_authenticated and u.role == 'employee'
def is_staffer(u): return u.is_authenticated and u.role in ('admin', 'employee')

def _near_expiry_qs(days=30):
    return Product.objects.filter(expiry_date__lte=timezone.now().date() + timedelta(days=days))

def _low_stock_qs():
    return Product.objects.filter(quantity_in_stock__lte=F('reorder_level'))

def _inventory_value_qs(qs=None):
    qs = qs or Product.objects.all()
    return qs.aggregate(total=Sum(F('quantity_in_stock') * F('unit_price')))['total'] or 0

def public_home(request):
    return render(request, "inventory/public_home.html")

def format_inventory_value(val):
    if val is None:
        return "0"
    if val >= 1_000_000:
        return f"{val/1_000_000:.1f}M"
    elif val >= 1_000:
        return f"{val/1_000:.1f}K"
    return str(int(val))



'''ADMIN LOGICS (DASHBOARD)'''
def admin_dashboard(request):
    products = Product.objects.all()
    low_stock = products.filter(quantity_in_stock__lte=F('reorder_level'))
    near_expiry = products.filter(expiry_date__lte=timezone.now().date() + timedelta(days=30))

    metrics = {
        'total_products': products.count(),
        'low_stock': low_stock.count(),
        'near_expiry': near_expiry.count(),
        'inventory_value': sum(p.quantity_in_stock * p.unit_price for p in products),
        'total_suppliers': Supplier.objects.count(),
        'total_categories': Category.objects.count(),
    }

    # Category chart
    by_category = products.values('category__name').annotate(qty=Sum('quantity_in_stock'))
    cat_labels = [c['category__name'] for c in by_category]
    cat_qty = [c['qty'] for c in by_category]

    # Stock chart counts
    low_count = low_stock.count()
    ok_count = products.filter(quantity_in_stock__gt=F('reorder_level')).count()

    # Users chart
    employees = User.objects.filter(role='employee')
    user_labels = [e.get_full_name() or e.username for e in employees]
    user_counts = [e.categories_assigned.count() for e in employees]

    context = {
        'metrics': metrics,
        'low_list': low_stock[:6],
        'exp_list': near_expiry[:6],
        'employees': employees,

        # Charts data as JSON
        'cat_labels': json.dumps(cat_labels),
        'cat_qty': json.dumps(cat_qty),
        'low_count': low_count,
        'ok_count': ok_count,
        'user_labels': json.dumps(user_labels),
        'user_counts': json.dumps(user_counts),
    }
    return render(request, 'inventory/admin_dashboard.html', context)

@login_required
@user_passes_test(is_employee)
def employee_dashboard(request):
    my_categories = Category.objects.filter(assigned_to=request.user)

    my_products = Product.objects.select_related('category') \
                                 .filter(category__in=my_categories)

    q = request.GET.get('q') or ''
    cat_id = request.GET.get('cat')
    if q:
        my_products = my_products.filter(
            Q(name__icontains=q) |
            Q(batch_number__icontains=q) |
            Q(category__name__icontains=q)
        )
    if cat_id:
        my_products = my_products.filter(category_id=cat_id)

    low_stock = my_products.filter(quantity_in_stock__lte=F('reorder_level'))
    near_expiry = my_products.filter(expiry_date__lte=timezone.now().date() + timedelta(days=30))

    metrics = {
        'assigned_products': my_products.count(),
        'my_low_stock': low_stock.count(),
        'my_near_expiry': near_expiry.count(),
        'my_inventory_value': format_inventory_value(_inventory_value_qs(my_products)),
        'suppliers_count': Supplier.objects.filter(products__in=my_products).distinct().count(),
    }

    by_category = (my_products.values('category__name')
                   .annotate(qty=Sum('quantity_in_stock'))
                   .order_by('category__name'))
    cat_labels = [c['category__name'] for c in by_category]
    cat_qty = [c['qty'] for c in by_category]

    low_count = low_stock.count()
    ok_count = my_products.filter(quantity_in_stock__gt=F('reorder_level')).count()

    context = {
        'metrics': metrics,
        'low_list': low_stock[:6],
        'exp_list': near_expiry[:6],
        'cat_labels': json.dumps(cat_labels),
        'cat_qty': json.dumps(cat_qty),
        'low_count': low_count,
        'ok_count': ok_count,
        'my_products': my_products.order_by('category__name', 'name'),
        'my_categories': my_categories.order_by('name'),
        'q': q,
        'selected_cat': int(cat_id) if cat_id else None,
    }
    return render(request, 'inventory/employee_dashboard.html', context)




'''CATEGORY LOGICS (CRUD)'''
@login_required
@user_passes_test(is_admin)
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'inventory/category_list.html', {'categories': categories})

@login_required
@user_passes_test(is_admin)
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventory:category_list')
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Create Category'})

@login_required
@user_passes_test(is_admin)
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Edit Category'})

@login_required
@user_passes_test(is_admin)
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect('inventory:category_list')
    return render(request, 'inventory/category_confirm_delete.html', {'category': category})


'''SUPPLIER LOGICS (CRUD)'''
@login_required
@user_passes_test(is_admin)
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

@login_required
@user_passes_test(is_admin)
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'inventory/supplier_form.html', {'form': form, 'title': 'Create Supplier'})

@login_required
@user_passes_test(is_admin)
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, request.FILES, instance=supplier)
        if form.is_valid():
            form.save()
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {'form': form, 'title': 'Edit Supplier'})

@login_required
@user_passes_test(is_admin)
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, "Supplier deleted successfully.")
        return redirect('inventory:supplier_list')
    return render(request, 'inventory/supplier_confirm_delete.html', {'supplier': supplier})


'''PRODUCTS LOGICS (CRUD)'''
@login_required
@user_passes_test(is_staffer)
def product_list(request):
    products = Product.objects.select_related('category').prefetch_related('suppliers')

    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    supplier_id = request.GET.get('supplier')
    expiry = request.GET.get('expiry')
    low_stock = request.GET.get('low_stock')
    view_mode = request.GET.get('view', 'card')

    if query:
        products = products.filter(name__icontains=query)

    if category_id:
        products = products.filter(category_id=category_id)

    if supplier_id:
        products = products.filter(suppliers__id=supplier_id)

    if expiry == '1':
        from datetime import timedelta
        from django.utils import timezone
        near_expiry = timezone.now().date() + timedelta(days=30)
        products = products.filter(expiry_date__lte=near_expiry)

    if low_stock == '1':
        products = products.filter(quantity_in_stock__lte=F('reorder_level'))

    products = products.distinct()

    paginator = Paginator(products, 8)
    page_number = request.GET.get('page')
    try:
        products_page = paginator.page(page_number)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    params = request.GET.copy()
    params.pop('page', None)
    base_qs = params.urlencode()  

    categories = Category.objects.all()
    suppliers = Supplier.objects.all()

    context = {
        'products': products_page,     
        'page_obj': products_page,
        'paginator': paginator,
        'is_paginated': products_page.has_other_pages(),
        'view_mode': view_mode,
        'categories': categories,
        'suppliers': suppliers,
        'query': query,
        'selected_category': category_id,
        'selected_supplier': supplier_id,
        'expiry': expiry,
        'low_stock': low_stock,
        'base_qs': base_qs,             
    }
    return render(request, 'inventory/product_list.html', context)

@login_required
@user_passes_test(is_staffer)
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('inventory:product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Create Product'})

@login_required
@user_passes_test(is_staffer)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('inventory:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Edit Product'})

@login_required
@user_passes_test(is_admin)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect('inventory:product_list')
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})


@login_required
@user_passes_test(is_admin)
def send_test_email(request):
    low_stock, near_expiry = get_inventory_alerts()

    subject = "StockMed Alerts"
    ctx = {"low_stock": low_stock, "near_expiry": near_expiry}
    text_body = []
    if low_stock.exists():
        text_body.append("Low Stock:")
        text_body += [f"- {p.name} (Qty: {p.quantity_in_stock}, Reorder: {p.reorder_level})" for p in low_stock]
        text_body.append("")
    else:
        text_body.append("No low stock items.")
        text_body.append("")
    if near_expiry.exists():
        text_body.append("Expiring ≤30 days:")
        text_body += [f"- {p.name} (Expiry: {p.expiry_date})" for p in near_expiry]
    else:
        text_body.append("No items near expiry.")

    to_email = settings.MANAGER_ALERT_EMAIL or request.user.email
    try:
        html_body = render_to_string("emails/alerts.html", ctx) if False else None

        if html_body:
            msg = EmailMultiAlternatives(subject, "\n".join(text_body),
                                         settings.DEFAULT_FROM_EMAIL, [to_email])
            msg.attach_alternative(html_body, "text/html")
            msg.send()
        else:
            from django.core.mail import send_mail
            send_mail(subject, "\n".join(text_body),
                      settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)

        messages.success(request, f"Email sent to {to_email}.")
    except Exception as e:
        messages.error(request, f"Failed to send email: {e}")

    return redirect("inventory:admin_dashboard")

@login_required
@user_passes_test(is_admin)
def trigger_email_alerts(request):
    low_stock = _low_stock_qs()
    expiring = _near_expiry_qs()

    sent_total = 0
    if low_stock.exists():
        body = "Low Stock Items:\n" + "\n".join(
            f"- {p.name} (Qty: {p.quantity_in_stock}, Reorder: {p.reorder_level})" for p in low_stock[:100]
        )
        sent_total += send_inventory_alert("StockMed: Low Stock Alert", body)

    if expiring.exists():
        body = "Expiring ≤30 days:\n" + "\n".join(
            f"- {p.name} (Expires: {p.expiry_date})" for p in expiring[:100]
        )
        sent_total += send_inventory_alert("StockMed: Expiry Alert", body)

    if sent_total:
        messages.success(request, f"Alerts sent ({sent_total}).")
    else:
        messages.info(request, "No alerts to send (nothing low or expiring).")
    return redirect('inventory:admin_dashboard')


'''CSV Import/Export'''
@login_required
@user_passes_test(is_admin)
def export_products(request):
    products = Product.objects.all()
    csv_data = export_products_to_csv(products)

    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products.csv"'
    return response


@login_required
@user_passes_test(is_admin)
def import_products(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        errors = import_products_from_csv(csv_file)
        if errors:
            messages.error(request, f"Import completed with errors: {errors}")
        else:
            messages.success(request, "Products imported successfully.")
        return redirect('inventory:product_list')

    return render(request, 'inventory/product_import.html')


''' DETAIL PAGES (PRODUCTS-CATEGORYS-SUPPLIERS)'''
@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'inventory/product_detail.html', {'product': product})

@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    products = supplier.products.all()
    return render(request, 'inventory/supplier_detail.html', {
        'supplier': supplier,
        'products': products
    })

@login_required
def category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    return render(request, 'inventory/category_detail.html', {'category': category})

