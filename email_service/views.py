# email_service/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import EmailServiceSetting, EmailMessage
from .services import EmailSyncService, EmailAPIService
from .serializers import EmailServiceSettingSerializer, EmailMessageSerializer
import logging

logger = logging.getLogger(__name__)

class EmailServiceSettingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Email Service Settings (read-only for API users)
    """
    queryset = EmailServiceSetting.objects.filter(is_active=True)
    serializer_class = EmailServiceSettingSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """
        Test connection to Graph API
        """
        service = self.get_object()
        sync_service = EmailSyncService(service)
        result = sync_service.test_connection()
        
        return Response({
            'success': result['success'],
            'message': result.get('message', ''),
            'error': result.get('error', '')
        })

    @action(detail=True, methods=['post'])
    def sync_emails(self, request, pk=None):
        """
        Trigger email synchronization
        """
        service = self.get_object()
        folder = request.data.get('folder', 'inbox')
        max_emails = request.data.get('max_emails', 100)
        force_full_sync = request.data.get('force_full_sync', False)
        
        sync_service = EmailSyncService(service)
        result = sync_service.sync_emails(
            folder=folder,
            max_emails=max_emails,
            force_full_sync=force_full_sync
        )
        
        return Response(result)

    @action(detail=False, methods=['get'])
    def default_service(self, request):
        """
        Get the default email service
        """
        default_service = EmailServiceSetting.get_default_service()
        if default_service:
            serializer = self.get_serializer(default_service)
            return Response(serializer.data)
        
        return Response({'error': 'No default email service configured'}, 
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emails(request):
    """
    Get emails with filtering and pagination
    Compatible with existing frontend EmailsPage component
    """
    # Extract parameters
    category = request.GET.get('category', 'inbox')
    service_id = request.GET.get('service_id')
    search_query = request.GET.get('search', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    
    try:
        emails = EmailAPIService.get_emails_for_category(
            category=category,
            service_id=service_id,
            search_query=search_query,
            page=page,
            page_size=page_size
        )
        
        return JsonResponse({
            'success': True,
            'emails': emails,
            'page': page,
            'page_size': page_size,
            'total': len(emails)
        })
        
    except Exception as e:
        logger.error(f"Failed to get emails: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_detail(request, email_id):
    """
    Get detailed email information
    """
    try:
        email_detail = EmailAPIService.get_email_detail(email_id)
        
        if email_detail:
            # Mark as read when viewed
            EmailAPIService.mark_as_read(email_id)
            
            return JsonResponse({
                'success': True,
                'email': email_detail
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Email not found'
            }, status=404)
            
    except Exception as e:
        logger.error(f"Failed to get email detail: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_email_read(request, email_id):
    """
    Mark email as read/unread
    """
    try:
        is_read = request.data.get('is_read', True)
        
        email = get_object_or_404(EmailMessage, id=email_id)
        email.is_read = is_read
        email.save()
        
        return JsonResponse({
            'success': True,
            'message': f"Email marked as {'read' if is_read else 'unread'}"
        })
        
    except Exception as e:
        logger.error(f"Failed to update email read status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_folder_counts(request):
    """
    Get email counts for different folders
    Compatible with existing sidebar component
    """
    try:
        counts = EmailAPIService.get_folder_counts()
        
        # Format for frontend compatibility
        categories = [
            {
                'id': 'inbox',
                'name': 'Inbox',
                'count': counts.get('inbox', 0),
                'unread': counts.get('unread', 0)
            },
            {
                'id': 'sent',
                'name': 'Sent',
                'count': counts.get('sent', 0),
                'unread': 0
            },
            {
                'id': 'draft',
                'name': 'Drafts',
                'count': counts.get('draft', 0),
                'unread': 0
            }
        ]
        
        return JsonResponse({
            'success': True,
            'categories': categories,
            'total': counts.get('total', 0)
        })
        
    except Exception as e:
        logger.error(f"Failed to get folder counts: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_sync(request):
    """
    Trigger email synchronization for default service
    """
    try:
        default_service = EmailServiceSetting.get_default_service()
        if not default_service:
            return JsonResponse({
                'success': False,
                'error': 'No default email service configured'
            }, status=400)
        
        folder = request.data.get('folder', 'inbox')
        max_emails = request.data.get('max_emails', 100)
        force_full_sync = request.data.get('force_full_sync', False)
        
        sync_service = EmailSyncService(default_service)
        result = sync_service.sync_emails(
            folder=folder,
            max_emails=max_emails,
            force_full_sync=force_full_sync
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Failed to trigger sync: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_status(request):
    """
    Get current sync status
    """
    try:
        default_service = EmailServiceSetting.get_default_service()
        if not default_service:
            return JsonResponse({
                'success': False,
                'error': 'No default email service configured'
            }, status=400)
        
        # Get latest sync log
        latest_log = default_service.sync_logs.first()
        
        if latest_log:
            sync_data = {
                'status': latest_log.status,
                'started_at': latest_log.sync_started_at.isoformat(),
                'completed_at': latest_log.sync_completed_at.isoformat() if latest_log.sync_completed_at else None,
                'emails_processed': latest_log.emails_processed,
                'emails_created': latest_log.emails_created,
                'emails_updated': latest_log.emails_updated,
                'error_message': latest_log.error_message
            }
        else:
            sync_data = {
                'status': 'never_synced',
                'started_at': None,
                'completed_at': None,
                'emails_processed': 0,
                'emails_created': 0,
                'emails_updated': 0,
                'error_message': ''
            }
        
        return JsonResponse({
            'success': True,
            'sync': sync_data,
            'service': {
                'name': default_service.name,
                'email': default_service.email,
                'last_sync_at': default_service.last_sync_at.isoformat() if default_service.last_sync_at else None
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Additional API endpoints for email operations
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_mark_read(request):
    """
    Mark multiple emails as read/unread
    """
    try:
        email_ids = request.data.get('email_ids', [])
        is_read = request.data.get('is_read', True)
        
        if not email_ids:
            return JsonResponse({
                'success': False,
                'error': 'No email IDs provided'
            }, status=400)
        
        updated_count = EmailMessage.objects.filter(
            id__in=email_ids
        ).update(is_read=is_read)
        
        return JsonResponse({
            'success': True,
            'message': f"{updated_count} emails marked as {'read' if is_read else 'unread'}"
        })
        
    except Exception as e:
        logger.error(f"Failed to bulk update read status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_emails(request):
    """
    Search emails with advanced filters
    """
    try:
        query = request.GET.get('q', '')
        from_email = request.GET.get('from_email', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        has_attachments = request.GET.get('has_attachments', '')
        is_read = request.GET.get('is_read', '')
        
        queryset = EmailMessage.objects.all()
        
        # Apply filters
        if query:
            queryset = queryset.filter(
                models.Q(subject__icontains=query) |
                models.Q(body_preview__icontains=query) |
                models.Q(from_name__icontains=query)
            )
        
        if from_email:
            queryset = queryset.filter(from_email__icontains=from_email)
        
        if date_from:
            queryset = queryset.filter(received_datetime__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(received_datetime__lte=date_to)
        
        if has_attachments:
            queryset = queryset.filter(has_attachments=has_attachments.lower() == 'true')
        
        if is_read:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        # Limit results
        emails = queryset.order_by('-received_datetime')[:100]
        
        email_list = [email.to_dict() for email in emails]
        
        return JsonResponse({
            'success': True,
            'emails': email_list,
            'total': len(email_list)
        })
        
    except Exception as e:
        logger.error(f"Failed to search emails: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)