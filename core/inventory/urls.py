from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('dashboard/', views.inventory_dashboard, name='dashboard'),
    path('parts/', views.parts_list, name='parts_list'),
    path('parts/add/', views.part_create, name='part_create'),
    path('parts/<int:pk>/', views.part_detail, name='part_detail'),
    path('parts/<int:pk>/edit/', views.part_edit, name='part_edit'),
    path('parts/<int:pk>/delete/', views.part_delete, name='part_delete'),
    path('parts/<int:pk>/transaction/', views.stock_transaction, name='stock_transaction'),
    path('alerts/', views.alerts_list, name='alerts'),
    path('alerts/<int:pk>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('suppliers/', views.suppliers_list, name='suppliers'),
    path('suppliers/add/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('categories/', views.categories_list, name='categories'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('machines/<int:pk>/edit/', views.machine_type_edit, name='machine_type_edit'),
    
    path('machines/', views.machine_types_list, name='machine_types'),
    path('machines/add/', views.machine_type_create, name='machine_type_create'),
    path('reports/', views.reports, name='reports'),

    path('suppliers/<int:pk>/delete/', views.supplier_delete,    name='supplier_delete'),
    path('categories/<int:pk>/delete/', views.category_delete,   name='category_delete'),
    path('machines/<int:pk>/delete/',   views.machine_type_delete, name='machine_type_delete'),
]
