"""
Data models for storing tick data and OHLC bars
"""
from django.db import models
from django.utils import timezone


class TickData(models.Model):
    """Raw tick data from Binance WebSocket"""
    symbol = models.CharField(max_length=20, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    price = models.FloatField()
    size = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tick_data'
        indexes = [
            models.Index(fields=['symbol', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.symbol} @ {self.timestamp}"


class OHLCData(models.Model):
    """OHLC bars for different timeframes"""
    TIMEFRAME_CHOICES = [
        ('1s', '1 Second'),
        ('1m', '1 Minute'),
        ('5m', '5 Minutes'),
    ]

    symbol = models.CharField(max_length=20, db_index=True)
    timeframe = models.CharField(max_length=5, choices=TIMEFRAME_CHOICES, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ohlc_data'
        unique_together = [['symbol', 'timeframe', 'timestamp']]
        indexes = [
            models.Index(fields=['symbol', 'timeframe', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.symbol} {self.timeframe} @ {self.timestamp}"


class UploadedOHLC(models.Model):
    """OHLC data uploaded by users"""
    symbol = models.CharField(max_length=20)
    timeframe = models.CharField(max_length=5)
    timestamp = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField(default=0.0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'uploaded_ohlc'
        ordering = ['-timestamp']
