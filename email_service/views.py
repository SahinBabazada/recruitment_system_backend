# email_service/views.py
from candidate.models import Candidate, CandidateEmailConnection
from candidate.serializers import CandidateListSerializer

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

from email_service import models

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
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_candidate_from_email(request, email_id):
    """
    Create a candidate from an email
    """
    try:
        email = get_object_or_404(EmailMessage, id=email_id)
        
        # Check if candidate already exists
        existing_candidate = Candidate.objects.filter(email__iexact=email.from_email).first()
        if existing_candidate:
            # Create connection if it doesn't exist
            connection, created = CandidateEmailConnection.objects.get_or_create(
                candidate=existing_candidate,
                email_message=email,
                defaults={
                    'email_type': 'general',
                    'is_inbound': True
                }
            )
            return JsonResponse({
                'success': True,
                'message': 'Email linked to existing candidate',
                'candidate': CandidateListSerializer(existing_candidate).data,
                'connection_created': created
            })
        
        # Extract name from email
        if email.from_name:
            name_parts = email.from_name.split()
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        else:
            # Extract from email address
            local_part = email.from_email.split('@')[0]
            name_parts = local_part.replace('.', ' ').replace('_', ' ').split()
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Get data from request or use extracted data
        candidate_data = {
            'name': request.data.get('name', f"{first_name} {last_name}".strip()),
            'email': email.from_email,
            'hiring_status': 'applied',
            'professional_summary': f'Candidate created from email: {email.subject}',
        }
        
        # Create candidate
        candidate = Candidate.objects.create(**candidate_data)
        
        # Create email connection
        CandidateEmailConnection.objects.create(
            candidate=candidate,
            email_message=email,
            email_type='application',
            is_inbound=True,
            internal_notes=f'Created candidate from email: {email.subject}'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Candidate created successfully',
            'candidate': CandidateListSerializer(candidate).data
        })
        
    except Exception as e:
        logger.error(f"Failed to create candidate from email: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emails_with_candidate_status(request):
    """
    Get emails with candidate status information
    """
    try:
        # Get emails using existing logic
        category = request.GET.get('category', 'inbox')
        service_id = request.GET.get('service_id')
        search_query = request.GET.get('search', '')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))
        filter_type = request.GET.get('filter')  # 'candidates', 'non-candidates', 'all'
        
        # Get base queryset
        queryset = EmailMessage.objects.select_related('service')
        
        # Filter by service
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        else:
            default_service = EmailServiceSetting.get_default_service()
            if default_service:
                queryset = queryset.filter(service=default_service)
        
        # Filter by category/folder
        if category and category != 'all':
            if category == 'inbox':
                queryset = queryset.filter(folder_name__icontains='inbox')
            elif category == 'sent':
                queryset = queryset.filter(folder_name__icontains='sent')
            elif category == 'draft':
                queryset = queryset.filter(is_draft=True)
            else:
                queryset = queryset.filter(folder_name__icontains=category)
        
        # Get candidate emails for filtering
        candidate_emails = set(Candidate.objects.values_list('email', flat=True))
        
        # Apply candidate filter
        if filter_type == 'candidates':
            queryset = queryset.filter(from_email__in=candidate_emails)
        elif filter_type == 'non-candidates':
            queryset = queryset.exclude(from_email__in=candidate_emails)
        
        # Apply search filter
        if search_query:
            queryset = queryset.filter(
                models.Q(subject__icontains=search_query) |
                models.Q(from_name__icontains=search_query) |
                models.Q(from_email__icontains=search_query) |
                models.Q(body_preview__icontains=search_query)
            )
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        emails = queryset.order_by('-received_datetime')[start:end]
        
        # Enhance emails with candidate information
        enhanced_emails = []
        for email in emails:
            email_dict = email.to_dict()
            
            # Check if sender is a candidate
            candidate = Candidate.objects.filter(email__iexact=email.from_email).first()
            if candidate:
                email_dict['candidate'] = {
                    'id': candidate.id,
                    'name': candidate.name,
                    'hiring_status': candidate.hiring_status,
                    'overall_score': float(candidate.overall_score) if candidate.overall_score else None
                }
            else:
                email_dict['candidate'] = None
            
            # Check if there's an email connection
            connection = email.candidate_connections.first()
            if connection:
                email_dict['email_connection'] = {
                    'id': connection.id,
                    'email_type': connection.email_type,
                    'requires_response': connection.requires_response,
                    'is_responded': connection.is_responded
                }
            else:
                email_dict['email_connection'] = None
                
            enhanced_emails.append(email_dict)
        
        # Get counts for filters
        total_emails = queryset.count()
        candidate_emails_count = queryset.filter(from_email__in=candidate_emails).count()
        non_candidate_emails_count = total_emails - candidate_emails_count
        
        return JsonResponse({
            'success': True,
            'emails': enhanced_emails,
            'page': page,
            'page_size': page_size,
            'total': total_emails,
            'counts': {
                'all': total_emails,
                'candidates': candidate_emails_count,
                'non_candidates': non_candidate_emails_count
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get emails with candidate status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_candidate_emails(request):
    """
    Get emails by candidate email address
    """
    try:
        candidate_email = request.GET.get('candidate_email')
        if not candidate_email:
            return JsonResponse({
                'success': False,
                'error': 'candidate_email parameter is required'
            }, status=400)
        
        # Get emails from this candidate
        emails = EmailMessage.objects.filter(
            from_email__iexact=candidate_email
        ).order_by('-received_datetime')
        
        email_list = []
        for email in emails:
            email_dict = email.to_dict()
            
            # Add connection info if exists
            connection = email.candidate_connections.first()
            if connection:
                email_dict['email_connection'] = {
                    'email_type': connection.email_type,
                    'requires_response': connection.requires_response,
                    'is_responded': connection.is_responded,
                    'internal_notes': connection.internal_notes
                }
            
            email_list.append(email_dict)
        
        return JsonResponse({
            'success': True,
            'emails': email_list,
            'total': len(email_list)
        })
        
    except Exception as e:
        logger.error(f"Failed to get candidate emails: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)