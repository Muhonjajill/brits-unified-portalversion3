from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.http import JsonResponse
from django.utils import timezone
from .models import SparePart, StockTransaction, StockAlert, PartCategory, MachineType, Supplier
from .forms import SparePartForm, StockTransactionForm, SupplierForm, PartCategoryForm, MachineTypeForm, StockFilterForm
import json


@login_required
def inventory_dashboard(request):
    #total_parts = SparePart.objects.filter(is_active=True).count()
    total_parts = SparePart.objects.count()
    #total_value = SparePart.objects.filter(is_active=True).aggregate(
    total_value = SparePart.objects.aggregate(
        val=Sum(F('quantity_in_stock') * F('unit_cost'))
    )['val'] or 0
    #low_stock = SparePart.objects.filter(is_active=True, quantity_in_stock__gt=0).filter(
    low_stock = SparePart.objects.filter(is_active=False, quantity_in_stock__gt=0).filter(
        quantity_in_stock__lte=F('minimum_stock_level')
    ).count()
    #out_of_stock = SparePart.objects.filter(is_active=True, quantity_in_stock=0).count()
    out_of_stock = SparePart.objects.filter(is_active=False, quantity_in_stock=0).count()
    active_alerts = StockAlert.objects.filter(status='active').count()
    recent_transactions = StockTransaction.objects.select_related('part', 'performed_by').order_by('-performed_at')[:10]
    #low_stock_parts = SparePart.objects.filter(is_active=True).filter(
    low_stock_parts = SparePart.objects.filter(
        quantity_in_stock__lte=F('minimum_stock_level')
    ).order_by('quantity_in_stock')[:8]
    # Category breakdown
    categories = PartCategory.objects.annotate(part_count=Count('parts')).order_by('-part_count')[:6]
    # Recent 7 days transactions
    from datetime import timedelta
    week_ago = timezone.now() - timedelta(days=7)
    week_transactions = StockTransaction.objects.filter(performed_at__gte=week_ago).count()

    context = {
        'total_parts': total_parts,
        'total_value': total_value,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'active_alerts': active_alerts,
        'recent_transactions': recent_transactions,
        'low_stock_parts': low_stock_parts,
        'categories': categories,
        'week_transactions': week_transactions,
    }
    return render(request, 'core/inventory/dashboard.html', context)


@login_required
def parts_list(request):
    form = StockFilterForm(request.GET)
    #parts = SparePart.objects.filter(is_active=True).select_related('category', 'supplier').prefetch_related('compatible_machines')
    parts = SparePart.objects.select_related('category', 'supplier').prefetch_related('compatible_machines')

    if form.is_valid():
        search = form.cleaned_data.get('search')
        category = form.cleaned_data.get('category')
        machine_type = form.cleaned_data.get('machine_type')
        stock_status = form.cleaned_data.get('stock_status')

        if search:
            parts = parts.filter(Q(name__icontains=search) | Q(part_number__icontains=search) | Q(description__icontains=search))
        if category:
            parts = parts.filter(category=category)
        if machine_type:
            parts = parts.filter(compatible_machines=machine_type)
        if stock_status == 'low':
            parts = parts.filter(quantity_in_stock__gt=0, quantity_in_stock__lte=F('minimum_stock_level'))
        elif stock_status == 'out':
            parts = parts.filter(quantity_in_stock=0)
        elif stock_status == 'ok':
            parts = parts.filter(quantity_in_stock__gt=F('minimum_stock_level'))

    print(parts.query)

    return render(request, 'core/inventory/parts_list.html', {'parts': parts, 'form': form})


@login_required
def part_detail(request, pk):
    part = get_object_or_404(SparePart, pk=pk)
    transactions = part.transactions.select_related('performed_by', 'machine_type').order_by('-performed_at')[:20]
    transaction_form = StockTransactionForm()
    return render(request, 'core/inventory/part_detail.html', {
        'part': part, 'transactions': transactions, 'transaction_form': transaction_form
    })


@login_required
def part_create(request):
    if request.method == 'POST':
        form = SparePartForm(request.POST)
        if form.is_valid():
            part = form.save(commit=False)
            part.created_by = request.user
            part.save()
            form.save_m2m()
            messages.success(request, f'Part "{part.name}" created successfully.')
            return redirect('inventory:part_detail', pk=part.pk)
    else:
        form = SparePartForm()
    return render(request, 'core/inventory/part_form.html', {'form': form, 'title': 'Add New Part'})


@login_required
def part_edit(request, pk):
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        form = SparePartForm(request.POST, instance=part)
        if form.is_valid():
            form.save()
            messages.success(request, f'Part "{part.name}" updated successfully.')
            return redirect('inventory:part_detail', pk=part.pk)
    else:
        form = SparePartForm(instance=part)
    return render(request, 'core/inventory/part_form.html', {'form': form, 'title': 'Edit Part', 'part': part})


@login_required
def part_delete(request, pk):
    if request.method == 'POST':
        part = get_object_or_404(SparePart, pk=pk)
        part.is_active = False
        part.save()
        return JsonResponse({'success': True, 'message': f'Part "{part.name}" has been deleted.'})
    return JsonResponse({'success': False}, status=400)


@login_required
def stock_transaction(request, pk):
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            txn = form.save(commit=False)
            txn.part = part
            txn.performed_by = request.user
            txn.quantity_before = part.quantity_in_stock

            # Determine sign
            t_type = txn.transaction_type
            qty = abs(txn.quantity)
            if t_type in ('receipt', 'return', 'adjustment'):
                part.quantity_in_stock += qty
            elif t_type in ('issue', 'damaged', 'transfer'):
                if qty > part.quantity_in_stock:
                    return JsonResponse({'success': False, 'error': 'Insufficient stock.'})
                part.quantity_in_stock -= qty
                txn.quantity = -qty
            else:
                part.quantity_in_stock += qty

            txn.quantity_after = part.quantity_in_stock
            part.save()
            txn.save()

            # Check alerts
            _check_stock_alerts(part)

            return JsonResponse({
                'success': True,
                'new_quantity': part.quantity_in_stock,
                'message': f'Transaction recorded. New stock: {part.quantity_in_stock} {part.unit}(s)'
            })
        return JsonResponse({'success': False, 'error': str(form.errors)})
    return JsonResponse({'success': False}, status=405)


def _check_stock_alerts(part):
    existing = StockAlert.objects.filter(part=part, status='active').first()
    if part.quantity_in_stock == 0:
        if not existing or existing.alert_type != 'out_of_stock':
            if existing:
                existing.status = 'resolved'
                existing.save()
            StockAlert.objects.create(part=part, alert_type='out_of_stock', quantity_at_alert=0)
    elif part.is_low_stock:
        if not existing or existing.alert_type != 'low_stock':
            if existing:
                existing.status = 'resolved'
                existing.save()
            StockAlert.objects.create(part=part, alert_type='low_stock', quantity_at_alert=part.quantity_in_stock)
    else:
        if existing:
            existing.status = 'resolved'
            existing.save()


@login_required
def alerts_list(request):
    alerts = StockAlert.objects.filter(status='active').select_related('part', 'acknowledged_by').order_by('-created_at')
    return render(request, 'core/inventory/alerts.html', {'alerts': alerts})


@login_required
def acknowledge_alert(request, pk):
    if request.method == 'POST':
        alert = get_object_or_404(StockAlert, pk=pk)
        alert.status = 'acknowledged'
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required
def suppliers_list(request):
    suppliers = Supplier.objects.annotate(part_count=Count('sparepart')).order_by('name')
    return render(request, 'core/inventory/suppliers.html', {'suppliers': suppliers})


@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier "{supplier.name}" added.')
            return redirect('inventory:suppliers')
    else:
        form = SupplierForm()
    return render(request, 'core/inventory/supplier_form.html', {'form': form, 'title': 'Add Supplier'})


@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier updated.')
            return redirect('inventory:suppliers')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'core/inventory/supplier_form.html', {'form': form, 'title': 'Edit Supplier', 'supplier': supplier})


@login_required
def categories_list(request):
    categories = PartCategory.objects.annotate(part_count=Count('parts')).order_by('name')
    return render(request, 'core/inventory/categories.html', {'categories': categories})


@login_required
def category_create(request):
    if request.method == 'POST':
        form = PartCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f'Category "{cat.name}" created.')
            return redirect('inventory:categories')
    else:
        form = PartCategoryForm()
    return render(request, 'core/inventory/category_form.html', {'form': form, 'title': 'Add Category'})


@login_required
def machine_types_list(request):
    machines = MachineType.objects.annotate(part_count=Count('parts')).order_by('name')
    return render(request, 'core/inventory/machine_types.html', {'machines': machines})


@login_required
def machine_type_create(request):
    if request.method == 'POST':
        form = MachineTypeForm(request.POST)
        if form.is_valid():
            m = form.save()
            messages.success(request, f'Machine type "{m.name}" added.')
            return redirect('inventory:machine_types')
    else:
        form = MachineTypeForm()
    return render(request, 'core/inventory/machine_type_form.html', {'form': form, 'title': 'Add Machine Type'})


@login_required
def reports(request):
    # Top 10 most issued
    #most_issued = SparePart.objects.filter(is_active=True).annotate(
    most_issued = SparePart.objects.annotate(
        issues=Count('transactions', filter=Q(transactions__transaction_type='issue'))
    ).order_by('-issues')[:10]

    # Stock value by category
    category_values = PartCategory.objects.annotate(
        total_val=Sum(F('parts__quantity_in_stock') * F('parts__unit_cost'))
    ).order_by('-total_val')

    # Transaction history last 30 days
    from datetime import timedelta
    month_ago = timezone.now() - timedelta(days=30)
    recent_txns = StockTransaction.objects.filter(performed_at__gte=month_ago).select_related('part', 'performed_by').order_by('-performed_at')[:50]

    context = {
        'most_issued': most_issued,
        'category_values': category_values,
        'recent_txns': recent_txns,
    }
    return render(request, 'core/inventory/reports.html', context)
