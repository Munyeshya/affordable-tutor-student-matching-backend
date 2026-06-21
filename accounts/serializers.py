import re

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User
from students.models import StudentProfile
from tutors.models import TutorProfile, TutorVerification


def _generate_username(email: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@", 1)[0]).strip("_").lower()
    base = base or "user"
    username = base[:150]
    suffix = 1

    while User.objects.filter(username=username).exists():
        candidate = f"{base}{suffix}"
        username = candidate[:150]
        suffix += 1

    return username


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "username", "role", "first_name", "last_name", "is_active")
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=120)
    role = serializers.ChoiceField(choices=User.Role.choices)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError("Admin accounts cannot be created through public registration.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data["email"].lower().strip()
        password = validated_data["password"]
        full_name = validated_data["full_name"].strip()
        role = validated_data["role"]

        user = User.objects.create_user(
            username=_generate_username(email),
            email=email,
            password=password,
            role=role,
        )

        if role == User.Role.STUDENT:
            StudentProfile.objects.create(user=user, full_name=full_name)
        elif role == User.Role.TUTOR:
            tutor_profile = TutorProfile.objects.create(user=user, full_name=full_name)
            TutorVerification.objects.create(tutor=user)
            return {"user": user, "profile": tutor_profile}

        return {"user": user}


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def create(self, validated_data):
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken(validated_data["refresh"])
        token.blacklist()
        return validated_data
