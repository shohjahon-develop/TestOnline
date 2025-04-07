# users/permissions.py
from rest_framework import permissions
from django.contrib.auth import get_user_model

from users.models import *

User = get_user_model()

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allows access only to the owner of the object or admin users.
    Assumes the model instance has a `user` attribute.
    For Profile views, checks if the object itself is the request.user.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            # For some objects, maybe even read access should be restricted
            # e.g., UserSettings, UserRating should only be readable by owner/admin
            if isinstance(obj, (UserSettings, UserRating, UserAchievement, UserCourseEnrollment, ScheduleItem, Notification)):
                return obj.user == request.user or request.user.is_staff
            return True # Allow read for other objects like Tests, Courses etc.

        # Write permissions only allowed to the owner or admin.
        owner = None
        if isinstance(obj, User): # Profile view
            owner = obj
        elif hasattr(obj, 'user'):
            owner = obj.user
        elif hasattr(obj, 'created_by'): # For models created by admin/teacher
             owner = obj.created_by
        # Add other owner attributes if necessary e.g., obj.owner

        return owner == request.user or request.user.is_staff


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access to any user, but write access only to admin users.
    """
    def has_permission(self, request, view):
        # Allow all SAFE_METHODS (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True
        # Allow write methods only if the user is an admin
        return request.user and request.user.is_staff

class IsStudent(permissions.BasePermission):
    """
    Allows access only to users with the 'student' role.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'student'

class IsAdminUser(permissions.BasePermission):
     """
     Allows access only to admin users (is_staff=True).
     """
     def has_permission(self, request, view):
         return request.user and request.user.is_staff