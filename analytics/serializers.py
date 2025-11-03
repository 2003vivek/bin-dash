"""
Serializers for analytics models
"""
from rest_framework import serializers
from analytics.models import AlertRule


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = '__all__'

