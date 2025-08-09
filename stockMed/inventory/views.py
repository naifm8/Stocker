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
from django.db.models import Count, Sum, F
from accounts.models import User


def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

def is_employee(user):
    return user.is_authenticated and user.role == 'employee'


def public_home(request):
    return render(request, 'inventory/home.html')


'''ADMIN LOGICS (DASHBOARD)'''
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    low_stock_products = Product.objects.filter(quantity_in_stock__lte=F('reorder_level'))
    near_expiry_products = Product.objects.filter(expiry_date__lte=timezone.now().date() + timedelta(days=30))

    category_data = (
        Product.objects.values('category__name')
        .annotate(total_quantity=Sum('quantity_in_stock'))
        .order_by('category__name')
    )

    category_labels = [item['category__name'] for item in category_data]
    category_values = [item['total_quantity'] for item in category_data]

    low_stock_count = Product.objects.filter(quantity_in_stock__lte=F('reorder_level')).count()
    in_stock_count = Product.objects.filter(quantity_in_stock__gt=F('reorder_level')).count()

    employees = (
        User.objects.filter(role='employee')
        .annotate(product_count=Count('assigned_products'))
        .order_by('username')
    )

    user_labels = [e.username for e in employees]
    user_counts = [e.product_count for e in employees]

    context = {
        'low_stock_count': low_stock_products.count(),
        'near_expiry_count': near_expiry_products.count(),
        'low_stock_products': low_stock_products[:5],
        'near_expiry_products': near_expiry_products[:5],
        'category_labels': category_labels,
        'category_values': category_values,
        'low_stock_count_chart': low_stock_count,
        'in_stock_count_chart': in_stock_count,
        'employees': employees,
        'user_labels': user_labels,
        'user_counts': user_counts,
    }
    return render(request, 'inventory/admin_dashboard.html', context)



@login_required
@user_passes_test(is_employee)
def employee_dashboard(request):
    return render(request, 'inventory/employee_dashboard.html')


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
def product_list(request):
    products = Product.objects.select_related('category').prefetch_related('suppliers')

    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    supplier_id = request.GET.get('supplier')
    expiry = request.GET.get('expiry')
    low_stock = request.GET.get('low_stock')

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

    categories = Category.objects.all()
    suppliers = Supplier.objects.all()

    context = {
        'products': products.distinct(),
        'categories': categories,
        'suppliers': suppliers,
        'query': query,
        'selected_category': category_id,
        'selected_supplier': supplier_id,
        'expiry': expiry,
        'low_stock': low_stock,
    }
    return render(request, 'inventory/product_list.html', context)


@login_required
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
def trigger_email_alerts(request):
    low_stock = Product.objects.filter(quantity_in_stock__lte=F('reorder_level'))
    expiring = Product.objects.filter(expiry_date__lte=timezone.now().date() + timedelta(days=30))

    if low_stock.exists():
        message = "\n".join([f"{p.name} (Qty: {p.quantity_in_stock})" for p in low_stock])
        send_inventory_alert(" Low Stock Alert", message, [request.user.email])

    if expiring.exists():
        message = "\n".join([f"{p.name} (Expires: {p.expiry_date})" for p in expiring])
        send_inventory_alert(" Expiry Alert", message, [request.user.email])

    messages.success(request, "Email alerts triggered manually.")
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

