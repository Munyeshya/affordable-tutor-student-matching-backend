from rest_framework import serializers


class DashboardSummarySerializer(serializers.Serializer):
    users = serializers.DictField()
    tutoring = serializers.DictField()
    tutor_pipeline = serializers.DictField()
    educational_impact = serializers.DictField()
    courses = serializers.DictField()
    revenue = serializers.DictField()
    employment_impact = serializers.DictField()
    trends = serializers.DictField()
    leaderboards = serializers.DictField()
    platform_health = serializers.DictField()
