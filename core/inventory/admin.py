from django.contrib import admin
from .models import SparePart, StockTransaction, StockAlert, PartCategory, MachineType, Supplier


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ['part_number', 'name', 'category', 'quantity_in_stock', 'unit_cost', 'is_active']
    list_filter = ['category', 'condition', 'is_active']
    search_fields = ['part_number', 'name']


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['part', 'transaction_type', 'quantity', 'performed_by', 'performed_at']
    list_filter = ['transaction_type']


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['part', 'alert_type', 'status', 'created_at']
    list_filter = ['status', 'alert_type']


admin.site.register(PartCategory)
admin.site.register(MachineType)
admin.site.register(Supplier)
