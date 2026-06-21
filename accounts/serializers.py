import re

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User
from students.models import ParentProfile, StudentProfile
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


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ("full_name", "level", "location", "budget_min", "budget_max", "prefers_online", "prefers_in_person")


class TutorProfileSerializer(serializers.ModelSerializer):
    verification_status = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = (
            "full_name",
            "headline",
            "bio",
            "hourly_rate",
            "currency",
            "location",
            "teaches_online",
            "teaches_in_person",
            "verification_status",
        )

    def get_verification_status(self, obj):
        verification = getattr(obj.user, "tutor_verification", None)
        return getattr(verification, "status", None)


class ParentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentProfile
        fields = ("full_name", "location", "phone_number", "notes")


class AuthUserDetailSerializer(UserSerializer):
    profile = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("profile",)

    def get_profile(self, obj):
        if obj.role == User.Role.STUDENT and hasattr(obj, "student_profile"):
            return {"type": "student", "data": StudentProfileSerializer(obj.student_profile).data}
        if obj.role == User.Role.TUTOR and hasattr(obj, "tutor_profile"):
            return {"type": "tutor", "data": TutorProfileSerializer(obj.tutor_profile).data}
        if obj.role == User.Role.PARENT and hasattr(obj, "parent_profile"):
            return {"type": "parent", "data": ParentProfileSerializer(obj.parent_profile).data}
        return None


class MeUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    location = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    level = serializers.CharField(max_length=100, required=False, allow_blank=True)
    budget_min = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    budget_max = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    prefers_online = serializers.BooleanField(required=False)
    prefers_in_person = serializers.BooleanField(required=False)

    headline = serializers.CharField(max_length=180, required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    hourly_rate = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    currency = serializers.CharField(max_length=10, required=False, allow_blank=True)
    teaches_online = serializers.BooleanField(required=False)
    teaches_in_person = serializers.BooleanField(required=False)

    def update(self, instance, validated_data):
        user = instance

        if "first_name" in validated_data:
            user.first_name = validated_data["first_name"]
        if "last_name" in validated_data:
            user.last_name = validated_data["last_name"]
        user.save(update_fields=["first_name", "last_name"])

        if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
            profile = user.student_profile
            if "full_name" in validated_data:
                profile.full_name = validated_data["full_name"]
            for field in ("level", "location", "budget_min", "budget_max", "prefers_online", "prefers_in_person"):
                if field in validated_data:
                    setattr(profile, field, validated_data[field])
            profile.save()

        elif user.role == User.Role.TUTOR and hasattr(user, "tutor_profile"):
            profile = user.tutor_profile
            if "full_name" in validated_data:
                profile.full_name = validated_data["full_name"]
            for field in ("headline", "bio", "hourly_rate", "currency", "location", "teaches_online", "teaches_in_person"):
                if field in validated_data:
                    setattr(profile, field, validated_data[field])
            profile.save()

        elif user.role == User.Role.PARENT and hasattr(user, "parent_profile"):
            profile = user.parent_profile
            if "full_name" in validated_data:
                profile.full_name = validated_data["full_name"]
            for field in ("location", "phone_number", "notes"):
                if field in validated_data:
                    setattr(profile, field, validated_data[field])
            profile.save()

        return user


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
        elif role == User.Role.PARENT:
            ParentProfile.objects.create(user=user, full_name=full_name)
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
