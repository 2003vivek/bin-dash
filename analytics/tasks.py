"""
Async tasks for analytics processing
"""
import asyncio
from channels.db import database_sync_to_async
from data_ingestion.models import TickData, OHLCData
from analytics.engine import AnalyticsEngine
from analytics.models import AnalyticsCache, AlertRule
from channels.layers import get_channel_layer
import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


async def process_tick_data(tick_data):
    """Process tick data for analytics and resampling"""
    try:
        if not tick_data:
            return
            
        # Resample to OHLC bars
        await resample_to_ohlc(tick_data['symbol'], tick_data['timestamp'])
        
        # Update tick-based analytics
        await update_tick_analytics(tick_data['symbol'])
        
        # Check alerts
        await check_alerts(tick_data['symbol'])
        
    except Exception as e:
        logger.error(f"Error processing tick data: {e}")


@database_sync_to_async
def resample_to_ohlc(symbol, timestamp_str):
    """Resample ticks to OHLC bars for different timeframes"""
    from datetime import datetime
    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    
    engine = AnalyticsEngine()
    timeframes = ['1s', '1m', '5m']
    
    for tf in timeframes:
        try:
            # Get recent ticks for this symbol
            start_time = timestamp - timedelta(minutes=10)
            ticks = list(TickData.objects.filter(
                symbol=symbol,
                timestamp__gte=start_time
            ).order_by('timestamp')[:1000])
            
            if ticks:
                ohlc_bars = engine.resample_ticks(ticks, tf)
                for bar in ohlc_bars:
                    OHLCData.objects.update_or_create(
                        symbol=symbol,
                        timeframe=tf,
                        timestamp=bar['timestamp'],
                        defaults={
                            'open': bar['open'],
                            'high': bar['high'],
                            'low': bar['low'],
                            'close': bar['close'],
                            'volume': bar['volume'],
                        }
                    )
        except Exception as e:
            logger.error(f"Error resampling {tf} for {symbol}: {e}")


@database_sync_to_async
def _compute_tick_analytics(symbol):
    """Compute tick-based analytics (sync function for DB operations)"""
    try:
        engine = AnalyticsEngine()
        
        # Get recent ticks (last 1000)
        ticks = list(TickData.objects.filter(
            symbol=symbol
        ).order_by('-timestamp')[:1000])
        
        if len(ticks) < 50:
            return None  # Need enough data
        
        # Calculate z-score and spread
        prices = [t.price for t in reversed(ticks)]
        
        # Z-score (assuming mean reversion)
        z_score = engine.calculate_z_score(prices)
        
        # Price statistics
        stats = engine.calculate_price_stats(prices)
        
        # Cache results
        AnalyticsCache.objects.update_or_create(
            symbol=symbol,
            analytics_type='z_score',
            timeframe='tick',
            window_size=1000,
            defaults={'data': {'z_score': z_score, 'timestamp': timezone.now().isoformat()}}
        )
        
        AnalyticsCache.objects.update_or_create(
            symbol=symbol,
            analytics_type='price_stats',
            timeframe='tick',
            window_size=1000,
            defaults={'data': stats}
        )
        
        return {'z_score': z_score, 'stats': stats}
            
    except Exception as e:
        logger.error(f"Error updating tick analytics: {e}")
        return None


async def update_tick_analytics(symbol):
    """Update tick-based analytics (async wrapper)"""
    result = await _compute_tick_analytics(symbol)
    
    if result and channel_layer:
        await channel_layer.group_send(
            'analytics_updates',
            {
                'type': 'analytics_update',
                'data': {
                    'symbol': symbol,
                    'type': 'z_score',
                    'value': result['z_score'],
                    'stats': result['stats'],
                }
            }
        )


@database_sync_to_async
def _check_alerts_db(symbol):
    """Check alerts in database (sync function)"""
    try:
        active_alerts = AlertRule.objects.filter(
            symbol=symbol,
            is_active=True
        )
        
        # Get latest analytics
        z_score_cache = AnalyticsCache.objects.filter(
            symbol=symbol,
            analytics_type='z_score'
        ).first()
        
        if not z_score_cache:
            return None
            
        z_score = z_score_cache.data.get('z_score', 0)
        triggered_alerts = []
        
        for alert in active_alerts:
            try:
                # Simple condition evaluation (e.g., "z_score > 2")
                condition = alert.condition.replace('z_score', str(z_score))
                if eval(condition):  # In production, use a safer evaluator
                    alert.trigger_count += 1
                    alert.last_triggered = timezone.now()
                    alert.save()
                    
                    triggered_alerts.append({
                        'rule_id': alert.id,
                        'name': alert.name,
                        'symbol': alert.symbol,
                        'condition': alert.condition,
                        'value': z_score,
                    })
            except Exception as e:
                logger.error(f"Error evaluating alert {alert.id}: {e}")
        
        return triggered_alerts if triggered_alerts else None
                
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")
        return None


async def check_alerts(symbol):
    """Check if any alert rules should trigger (async wrapper)"""
    triggered = await _check_alerts_db(symbol)
    
    if triggered and channel_layer:
        for alert_data in triggered:
            await channel_layer.group_send(
                'alerts',
                {
                    'type': 'alert_triggered',
                    'data': {
                        **alert_data,
                        'timestamp': timezone.now().isoformat(),
                    }
                }
            )

