from django import forms
from .models import Category, Supplier, Product

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'email', 'phone', 'website', 'address']

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'suppliers', 'batch_number',
            'quantity_in_stock', 'reorder_level', 'unit_price', 'expiry_date'
        ]
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'suppliers': forms.CheckboxSelectMultiple(),
        }
