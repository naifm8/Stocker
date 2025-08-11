from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='categories_assigned'
    )

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    image = models.ImageField(upload_to='suppliers/', blank=True, null=True)
    description = models.TextField(blank=True) 

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    suppliers = models.ManyToManyField(Supplier, related_name='products')
    batch_number = models.CharField(max_length=100)
    quantity_in_stock = models.PositiveIntegerField()
    reorder_level = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField()
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    description = models.TextField(blank=True)



    def __str__(self):
        return f"{self.name} - Batch: {self.batch_number}"

    def is_low_stock(self):
        return self.quantity_in_stock <= self.reorder_level

    def is_expiring_soon(self):
        from datetime import date, timedelta
        return self.expiry_date <= date.today() + timedelta(days=30)
