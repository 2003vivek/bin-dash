from django.contrib import admin
from .models import AnalyticsCache, AlertRule


@admin.register(AnalyticsCache)
class AnalyticsCacheAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'analytics_type', 'timeframe', 'window_size', 'computed_at')
    list_filter = ('analytics_type', 'timeframe', 'symbol')
    search_fields = ('symbol',)


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'condition', 'is_active', 'trigger_count', 'last_triggered')
    list_filter = ('is_active', 'symbol')
    search_fields = ('name', 'symbol')
