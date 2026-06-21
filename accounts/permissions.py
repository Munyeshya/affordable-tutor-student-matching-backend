from rest_framework.permissions import BasePermission

from accounts.models import User


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

