"""
REST API views for analytics
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from datetime import datetime, timedelta
import csv
import json
import pandas as pd

from data_ingestion.models import TickData, OHLCData, UploadedOHLC
from analytics.models import AnalyticsCache, AlertRule
from analytics.engine import AnalyticsEngine
from analytics.serializers import AlertRuleSerializer


class AnalyticsViewSet(viewsets.ViewSet):
    """ViewSet for analytics endpoints"""
    
    @action(detail=False, methods=['get'])
    def price_stats(self, request):
        """Get price statistics"""
        symbol = request.query_params.get('symbol')
        window = int(request.query_params.get('window', 1000))
        
        if not symbol:
            return Response({'error': 'Symbol required'}, status=400)
            
        ticks = list(TickData.objects.filter(symbol=symbol)
                    .order_by('-timestamp')[:window])
        
        if not ticks:
            return Response({'error': 'No data found'}, status=404)
            
        engine = AnalyticsEngine()
        prices = [t.price for t in reversed(ticks)]
        stats = engine.calculate_price_stats(prices)
        
        return Response(stats)
        
    @action(detail=False, methods=['get'])
    def z_score(self, request):
        """Get z-score"""
        symbol = request.query_params.get('symbol')
        window = int(request.query_params.get('window', 100))
        
        if not symbol:
            return Response({'error': 'Symbol required'}, status=400)
            
        cache = AnalyticsCache.objects.filter(
            symbol=symbol,
            analytics_type='z_score'
        ).first()
        
        if cache:
            return Response(cache.data)
            
        # Calculate on the fly
        ticks = list(TickData.objects.filter(symbol=symbol)
                    .order_by('-timestamp')[:window])
        
        if not ticks:
            return Response({'error': 'No data found'}, status=404)
            
        engine = AnalyticsEngine()
        prices = [t.price for t in reversed(ticks)]
        z_score = engine.calculate_z_score(prices, window)
        
        return Response({'z_score': z_score, 'window': window})
        
    @action(detail=False, methods=['get'])
    def spread(self, request):
        """
        Get pair spread between two symbols (price1 - price2)
        Note: This is for pairs trading, not bid-ask spread.
        Bid-ask spread would require order book data.
        """
        symbol1 = request.query_params.get('symbol1')
        symbol2 = request.query_params.get('symbol2')
        window = int(request.query_params.get('window', 100))
        
        if not symbol1 or not symbol2:
            return Response({'error': 'Both symbol1 and symbol2 required'}, status=400)
            
        ticks1 = list(TickData.objects.filter(symbol=symbol1)
                     .order_by('-timestamp')[:window])
        ticks2 = list(TickData.objects.filter(symbol=symbol2)
                     .order_by('-timestamp')[:window])
        
        if not ticks1 or not ticks2:
            return Response({'error': 'Insufficient data'}, status=404)
            
        engine = AnalyticsEngine()
        prices1 = [t.price for t in reversed(ticks1)]
        prices2 = [t.price for t in reversed(ticks2)]
        spread = engine.calculate_spread(prices1, prices2)
        
        return Response(spread)
        
    @action(detail=False, methods=['get'])
    def hedge_ratio(self, request):
        """Get hedge ratio"""
        symbol1 = request.query_params.get('symbol1')
        symbol2 = request.query_params.get('symbol2')
        
        if not symbol1 or not symbol2:
            return Response({'error': 'Both symbol1 and symbol2 required'}, status=400)
            
        ticks1 = list(TickData.objects.filter(symbol=symbol1)
                     .order_by('-timestamp')[:1000])
        ticks2 = list(TickData.objects.filter(symbol=symbol2)
                     .order_by('-timestamp')[:1000])
        
        if not ticks1 or not ticks2:
            return Response({'error': 'Insufficient data'}, status=404)
            
        engine = AnalyticsEngine()
        prices1 = [t.price for t in reversed(ticks1)]
        prices2 = [t.price for t in reversed(ticks2)]
        hedge_ratio = engine.calculate_hedge_ratio(prices1, prices2)
        
        if not hedge_ratio:
            return Response({'error': 'Could not calculate hedge ratio'}, status=400)
            
        return Response(hedge_ratio)
        
    @action(detail=False, methods=['get'])
    def correlation(self, request):
        """Get rolling correlation"""
        symbol1 = request.query_params.get('symbol1')
        symbol2 = request.query_params.get('symbol2')
        window = int(request.query_params.get('window', 100))
        
        if not symbol1 or not symbol2:
            return Response({'error': 'Both symbol1 and symbol2 required'}, status=400)
            
        ticks1 = list(TickData.objects.filter(symbol=symbol1)
                     .order_by('-timestamp')[:window*2])
        ticks2 = list(TickData.objects.filter(symbol=symbol2)
                     .order_by('-timestamp')[:window*2])
        
        if not ticks1 or not ticks2:
            return Response({'error': 'Insufficient data'}, status=404)
            
        engine = AnalyticsEngine()
        prices1 = [t.price for t in reversed(ticks1)]
        prices2 = [t.price for t in reversed(ticks2)]
        correlation = engine.calculate_rolling_correlation(prices1, prices2, window)
        
        return Response(correlation)
        
    @action(detail=False, methods=['get'])
    def adf_test(self, request):
        """Run ADF test"""
        symbol = request.query_params.get('symbol')
        window = int(request.query_params.get('window', 500))
        
        if not symbol:
            return Response({'error': 'Symbol required'}, status=400)
            
        ticks = list(TickData.objects.filter(symbol=symbol)
                    .order_by('-timestamp')[:window])
        
        if not ticks:
            return Response({'error': 'No data found'}, status=404)
            
        engine = AnalyticsEngine()
        prices = [t.price for t in reversed(ticks)]
        adf_result = engine.adf_test(prices)
        
        if not adf_result:
            return Response({'error': 'Could not perform ADF test'}, status=400)
            
        return Response(adf_result)


@api_view(['GET'])
def get_symbols(request):
    """Get list of available symbols"""
    symbols = list(TickData.objects.values_list('symbol', flat=True).distinct())
    return Response({'symbols': symbols})


@api_view(['GET'])
def get_ticks(request):
    """Get tick data"""
    symbol = request.query_params.get('symbol')
    start = request.query_params.get('start')
    end = request.query_params.get('end')
    limit = int(request.query_params.get('limit', 1000))
    
    queryset = TickData.objects.all()
    
    if symbol:
        queryset = queryset.filter(symbol=symbol)
    if start:
        queryset = queryset.filter(timestamp__gte=start)
    if end:
        queryset = queryset.filter(timestamp__lte=end)
        
    ticks = queryset.order_by('-timestamp')[:limit]
    
    data = [{
        'symbol': t.symbol,
        'timestamp': t.timestamp.isoformat(),
        'price': t.price,
        'size': t.size,
    } for t in ticks]
    
    return Response(data)


@api_view(['GET'])
def get_ohlc(request):
    """Get OHLC data"""
    symbol = request.query_params.get('symbol')
    timeframe = request.query_params.get('timeframe', '1m')
    limit = int(request.query_params.get('limit', 1000))
    
    queryset = OHLCData.objects.all()
    
    if symbol:
        queryset = queryset.filter(symbol=symbol)
    queryset = queryset.filter(timeframe=timeframe)
    
    ohlc = queryset.order_by('-timestamp')[:limit]
    
    data = [{
        'symbol': o.symbol,
        'timeframe': o.timeframe,
        'timestamp': o.timestamp.isoformat(),
        'open': o.open,
        'high': o.high,
        'low': o.low,
        'close': o.close,
        'volume': o.volume,
    } for o in ohlc]
    
    return Response(data)


@api_view(['POST'])
def export_data(request):
    """Export data as CSV or NDJSON"""
    format_type = request.data.get('format', 'csv')
    symbol = request.data.get('symbol')
    data_type = request.data.get('type', 'ticks')  # 'ticks' or 'ohlc'
    timeframe = request.data.get('timeframe', '1m')
    
    if data_type == 'ticks':
        queryset = TickData.objects.all()
        if symbol:
            queryset = queryset.filter(symbol=symbol)
        data = queryset.order_by('-timestamp')[:10000]
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{symbol or "all"}_ticks.csv"'
            writer = csv.writer(response)
            writer.writerow(['symbol', 'timestamp', 'price', 'size'])
            for t in data:
                writer.writerow([t.symbol, t.timestamp.isoformat(), t.price, t.size])
            return response
        else:  # NDJSON
            response = HttpResponse(content_type='application/x-ndjson')
            response['Content-Disposition'] = f'attachment; filename="{symbol or "all"}_ticks.ndjson"'
            for t in data:
                json.dump({
                    'symbol': t.symbol,
                    'timestamp': t.timestamp.isoformat(),
                    'price': t.price,
                    'size': t.size,
                }, response)
                response.write('\n')
            return response
    else:  # OHLC
        queryset = OHLCData.objects.all()
        if symbol:
            queryset = queryset.filter(symbol=symbol)
        queryset = queryset.filter(timeframe=timeframe)
        data = queryset.order_by('-timestamp')[:10000]
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{symbol or "all"}_ohlc.csv"'
            writer = csv.writer(response)
            writer.writerow(['symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume'])
            for o in data:
                writer.writerow([o.symbol, o.timeframe, o.timestamp.isoformat(), 
                               o.open, o.high, o.low, o.close, o.volume])
            return response
        else:  # NDJSON
            response = HttpResponse(content_type='application/x-ndjson')
            response['Content-Disposition'] = f'attachment; filename="{symbol or "all"}_ohlc.ndjson"'
            for o in data:
                json.dump({
                    'symbol': o.symbol,
                    'timeframe': o.timeframe,
                    'timestamp': o.timestamp.isoformat(),
                    'open': o.open,
                    'high': o.high,
                    'low': o.low,
                    'close': o.close,
                    'volume': o.volume,
                }, response)
                response.write('\n')
            return response


@api_view(['POST'])
def upload_ohlc(request):
    """Upload OHLC data"""
    try:
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=400)
            
        # Parse CSV
        df = pd.read_csv(file)
        required_cols = ['symbol', 'timestamp', 'open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return Response({'error': f'Required columns: {required_cols}'}, status=400)
            
        timeframe = request.data.get('timeframe', '1m')
        
        created = 0
        for _, row in df.iterrows():
            UploadedOHLC.objects.create(
                symbol=row['symbol'],
                timeframe=timeframe,
                timestamp=pd.to_datetime(row['timestamp']),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row.get('volume', 0)),
            )
            created += 1
            
        return Response({'message': f'Uploaded {created} records'})
    except Exception as e:
        return Response({'error': str(e)}, status=400)


class AlertRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for alert rules"""
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    
    def get_queryset(self):
        queryset = AlertRule.objects.all()
        symbol = self.request.query_params.get('symbol')
        if symbol:
            queryset = queryset.filter(symbol=symbol)
        return queryset
