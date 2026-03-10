from rest_framework import serializers

from .models import BirthdayNotification, EmailConfig, Employee


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "birth_date",
            "location",
            "team",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BirthdayNotificationSerializer(serializers.ModelSerializer):
    birthday_employees = EmployeeSerializer(many=True, read_only=True)

    class Meta:
        model = BirthdayNotification
        fields = [
            "id",
            "sent_at",
            "subject",
            "body_preview",
            "recipients",
            "birthday_employees",
            "success",
            "error_message",
        ]
        read_only_fields = fields


class EmailConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailConfig
        fields = [
            "id",
            "subject_template",
            "body_template",
            "sender_email",
            "created_at",
            "updated_at",
        ]
    read_only_fields = ["id", "created_at", "updated_at"]


