from django.contrib import admin
from .models import TickData, OHLCData, UploadedOHLC


@admin.register(TickData)
class TickDataAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'timestamp', 'price', 'size')
    list_filter = ('symbol', 'timestamp')
    search_fields = ('symbol',)


@admin.register(OHLCData)
class OHLCDataAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume')
    list_filter = ('symbol', 'timeframe', 'timestamp')
    search_fields = ('symbol',)


@admin.register(UploadedOHLC)
class UploadedOHLCAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close')
    list_filter = ('symbol', 'timeframe', 'timestamp')
