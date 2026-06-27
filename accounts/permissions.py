from rest_framework.permissions import BasePermission

from accounts.models import User
from tutors.models import TutorVerification


class HasRole(BasePermission):
    allowed_roles = set()

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.role in self.allowed_roles


class IsStudent(HasRole):
    allowed_roles = {User.Role.STUDENT}


class IsTutor(HasRole):
    allowed_roles = {User.Role.TUTOR}


class IsParent(HasRole):
    allowed_roles = {User.Role.PARENT}


class IsAdminRole(HasRole):
    allowed_roles = {User.Role.ADMIN}


class IsMarketplaceReadyTutor(HasRole):
    allowed_roles = {User.Role.TUTOR}

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        verification = TutorVerification.objects.filter(tutor=request.user).first()
        return bool(verification and verification.is_marketplace_ready())
