"""
WebSocket routing configuration
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/ticker/$', consumers.BinanceWebSocketConsumer.as_asgi()),
    re_path(r'ws/analytics/$', consumers.AnalyticsConsumer.as_asgi()),
    re_path(r'ws/alerts/$', consumers.AlertConsumer.as_asgi()),
]

