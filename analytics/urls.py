"""
URL routing for analytics app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'analytics', views.AnalyticsViewSet, basename='analytics')
router.register(r'alerts', views.AlertRuleViewSet, basename='alerts')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/symbols/', views.get_symbols, name='symbols'),
    path('api/ticks/', views.get_ticks, name='ticks'),
    path('api/ohlc/', views.get_ohlc, name='ohlc'),
    path('api/export/', views.export_data, name='export'),
    path('api/upload-ohlc/', views.upload_ohlc, name='upload_ohlc'),
]

