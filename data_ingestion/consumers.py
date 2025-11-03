"""
WebSocket consumers for Binance data ingestion and real-time broadcasting
"""
import json
import asyncio
import websockets
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import datetime
from datetime import timezone as dt_timezone
from data_ingestion.models import TickData
from analytics.tasks import process_tick_data
import logging

logger = logging.getLogger(__name__)


class BinanceWebSocketConsumer(AsyncWebsocketConsumer):
    """Consumer that connects to Binance WebSocket and stores data"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binance_ws = None
        self.symbols = []
        self.running = False
        
    async def connect(self):
        await self.accept()
        logger.info("WebSocket client connected")
        
    async def disconnect(self, close_code):
        self.running = False
        if self.binance_ws:
            await self.binance_ws.close()
        logger.info(f"WebSocket client disconnected: {close_code}")
        
    async def receive(self, text_data):
        """Handle messages from client (start/stop commands)"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'start':
                symbols = data.get('symbols', [])
                await self.start_collection(symbols)
            elif message_type == 'stop':
                await self.stop_collection()
            elif message_type == 'get_symbols':
                await self.send_symbols_list()
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
            
    async def start_collection(self, symbols):
        """Start collecting data from Binance WebSocket"""
        if self.running:
            return
            
        self.symbols = [s.lower() for s in symbols if s]
        if not self.symbols:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'No symbols provided'
            }))
            return
            
        self.running = True
        await self.send(text_data=json.dumps({
            'type': 'status',
            'message': f'Starting collection for: {", ".join(self.symbols)}'
        }))
        
        # Start Binance WebSocket connection in background
        asyncio.create_task(self.connect_to_binance())
        
    async def stop_collection(self):
        """Stop collecting data"""
        self.running = False
        if self.binance_ws:
            await self.binance_ws.close()
            self.binance_ws = None
        await self.send(text_data=json.dumps({
            'type': 'status',
            'message': 'Collection stopped'
        }))
        
    async def connect_to_binance(self):
        """Connect to Binance WebSocket streams"""
        streams = [f"{symbol}@trade" for symbol in self.symbols]
        stream_url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"
        
        try:
            async with websockets.connect(stream_url) as ws:
                self.binance_ws = ws
                await self.send(text_data=json.dumps({
                    'type': 'status',
                    'message': f'Connected to Binance WebSocket'
                }))
                
                async for message in ws:
                    if not self.running:
                        break
                    await self.process_binance_message(message)
                    
        except Exception as e:
            logger.error(f"Binance WebSocket error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Binance connection error: {str(e)}'
            }))
            self.running = False
            
    async def process_binance_message(self, message):
        """Process incoming message from Binance"""
        try:
            data = json.loads(message)
            stream = data.get('stream', '')
            
            if '@trade' in stream:
                trade_data = data.get('data', {})
                symbol = trade_data.get('s', '').lower()
                
                if symbol in self.symbols:
                    tick = await self.save_tick_data(trade_data)
                    if tick:  # Only process if tick was saved successfully
                        await self.broadcast_tick(tick)
                        # Trigger async analytics processing
                        asyncio.create_task(process_tick_data(tick))
                    
        except Exception as e:
            logger.error(f"Error processing Binance message: {e}")
            
    @database_sync_to_async
    def save_tick_data(self, trade_data):
        """Save tick data to database"""
        try:
            symbol = trade_data.get('s', '').lower()
            price = float(trade_data.get('p', 0))
            size = float(trade_data.get('q', 0))
            # Binance provides 'T' (trade time) or 'E' (event time)
            timestamp_ms = trade_data.get('T') or trade_data.get('E', 0)
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=dt_timezone.utc)
            
            tick = TickData.objects.create(
                symbol=symbol,
                timestamp=timestamp,
                price=price,
                size=size
            )
            return {
                'id': tick.id,
                'symbol': tick.symbol,
                'timestamp': tick.timestamp.isoformat(),
                'price': tick.price,
                'size': tick.size,
            }
        except Exception as e:
            logger.error(f"Error saving tick data: {e}")
            return None
            
    async def broadcast_tick(self, tick):
        """Broadcast tick data to all connected clients"""
        if tick:
            await self.send(text_data=json.dumps({
                'type': 'tick',
                'data': tick
            }))
            
    async def send_symbols_list(self):
        """Send list of available symbols"""
        symbols = await self.get_available_symbols()
        await self.send(text_data=json.dumps({
            'type': 'symbols',
            'data': symbols
        }))
        
    @database_sync_to_async
    def get_available_symbols(self):
        """Get list of symbols in database"""
        return list(TickData.objects.values_list('symbol', flat=True).distinct())


class AnalyticsConsumer(AsyncWebsocketConsumer):
    """Consumer for broadcasting analytics updates"""
    
    async def connect(self):
        self.room_group_name = 'analytics_updates'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
    async def analytics_update(self, event):
        """Send analytics update to client"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'analytics',
                'data': event['data']
            }))
        except Exception as e:
            # Connection may be closed, ignore
            pass


class AlertConsumer(AsyncWebsocketConsumer):
    """Consumer for broadcasting alerts"""
    
    async def connect(self):
        self.room_group_name = 'alerts'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
    async def alert_triggered(self, event):
        """Send alert to client"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'alert',
                'data': event['data']
            }))
        except Exception as e:
            # Connection may be closed, ignore
            pass

