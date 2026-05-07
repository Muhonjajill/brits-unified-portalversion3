from .models import StockAlert


def inventory_alerts(request):
    if request.user.is_authenticated:
        active_alert_count = StockAlert.objects.filter(status='active').count()
        return {'active_alert_count': active_alert_count}
    return {'active_alert_count': 0}
