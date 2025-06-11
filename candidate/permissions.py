# candidate/permissions.py
from rest_framework import permissions


class CandidatePermission(permissions.BasePermission):
    """
    Custom permission for candidate operations
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to access candidates"""
        if not request.user.is_authenticated:
            return False
        
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions for HR and recruiters
        return (
            request.user.is_staff or
            request.user.groups.filter(name__in=['HR', 'Recruiters']).exists()
        )


class CandidateAttachmentPermission(permissions.BasePermission):
    """
    Custom permission for candidate attachment operations
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to access candidate attachments"""
        if not request.user.is_authenticated:
            return False
        
        # All authenticated users can view attachments
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only HR, recruiters, and managers can upload/modify attachments
        return (
            request.user.is_staff or
            request.user.groups.filter(
                name__in=['HR', 'Recruiters', 'Hiring Managers']
            ).exists()
        )
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific attachment"""
        # All authenticated users can view
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only uploader, HR, or recruiters can modify
        return (
            obj.uploaded_by == request.user or
            request.user.is_staff or
            request.user.groups.filter(
                name__in=['HR', 'Recruiters', 'Hiring Managers']
            ).exists()
        )


class CandidateEmailPermission(permissions.BasePermission):
    """
    Custom permission for candidate email operations
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to access candidate emails"""
        if not request.user.is_authenticated:
            return False
        
        # Only HR and recruiters can access candidate emails
        return (
            request.user.is_staff or
            request.user.groups.filter(name__in=['HR', 'Recruiters']).exists()
        )


class CandidateStatusUpdatePermission(permissions.BasePermission):
    """
    Custom permission for candidate status updates
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to update candidate status"""
        if not request.user.is_authenticated:
            return False
        
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only HR, recruiters, and hiring managers can update status
        return (
            request.user.is_staff or
            request.user.groups.filter(
                name__in=['HR', 'Recruiters', 'Hiring Managers']
            ).exists()
        )
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific candidate"""
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True