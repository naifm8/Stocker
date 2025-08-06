from django.contrib import admin
from .models import Category, Supplier, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone')
    search_fields = ('name', 'email')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'batch_number', 'quantity_in_stock', 'reorder_level', 'expiry_date')
    list_filter = ('category', 'expiry_date')
    search_fields = ('name', 'batch_number')
    filter_horizontal = ('suppliers',)
