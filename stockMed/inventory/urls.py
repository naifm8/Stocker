from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path("", views.public_home, name="home"),


    # Dashboards URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('alerts/send/', views.trigger_email_alerts, name='trigger_alerts'),
    path("send-test-email/", views.send_test_email, name="send_test_email"),
    path("alerts/test/", views.send_test_email, name="send_test_email"),



    # Category URLs
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),


    # Supplier URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),


    # Product URLs
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),


    # CSV Import/Export
    path('products/export/', views.export_products, name='product_export'),
    path('products/import/', views.import_products, name='product_import'),

]
