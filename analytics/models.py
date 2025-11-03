"""
Analytics models for storing computed analytics and alert rules
"""
from django.db import models
from django.utils import timezone
import json


class AnalyticsCache(models.Model):
    """Cached analytics results"""
    ANALYTICS_TYPES = [
        ('price_stats', 'Price Statistics'),
        ('z_score', 'Z-Score'),
        ('spread', 'Spread'),
        ('hedge_ratio', 'Hedge Ratio'),
        ('correlation', 'Rolling Correlation'),
        ('adf_test', 'ADF Test'),
    ]

    symbol = models.CharField(max_length=20, db_index=True)
    analytics_type = models.CharField(max_length=20, choices=ANALYTICS_TYPES, db_index=True)
    timeframe = models.CharField(max_length=5, default='tick', db_index=True)
    window_size = models.IntegerField(default=100)
    computed_at = models.DateTimeField(auto_now=True)
    data = models.JSONField()  # Stores computed results

    class Meta:
        db_table = 'analytics_cache'
        indexes = [
            models.Index(fields=['symbol', 'analytics_type', 'timeframe']),
        ]
        ordering = ['-computed_at']

    def __str__(self):
        return f"{self.symbol} - {self.analytics_type}"


class AlertRule(models.Model):
    """User-defined alert rules"""
    name = models.CharField(max_length=100)
    condition = models.CharField(max_length=500)  # e.g., "z_score > 2"
    symbol = models.CharField(max_length=20, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    trigger_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'alert_rules'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.symbol}"
