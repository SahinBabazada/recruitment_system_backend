# candidate/tasks.py (Updated with optional imports)
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Candidate, CandidateStatusUpdate
import logging

logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    from .utils.email_integration import EmailSyncService
except ImportError:
    logger.warning("Email integration not available")
    EmailSyncService = None

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    REPORTLAB_AVAILABLE = True
except ImportError:
    logger.warning("ReportLab not available - PDF generation disabled")
    REPORTLAB_AVAILABLE = False


@shared_task
def sync_candidate_emails_task(candidate_email=None, days_back=30):
    """
    Celery task to sync candidate emails in background
    """
    if not EmailSyncService:
        logger.error("EmailSyncService not available")
        return {'error': 'EmailSyncService not available'}
        
    try:
        result = EmailSyncService.sync_candidate_emails(
            candidate_email=candidate_email,
            days_back=days_back
        )
        
        logger.info(f"Email sync completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Email sync failed: {str(e)}")
        raise


@shared_task
def sync_new_candidate_emails_task(candidate_id):
    """
    Celery task to sync emails for a new candidate
    """
    if not EmailSyncService:
        logger.error("EmailSyncService not available")
        return {'error': 'EmailSyncService not available'}
        
    try:
        candidate = Candidate.objects.get(id=candidate_id)
        result = EmailSyncService.sync_new_candidate_emails(candidate)
        
        logger.info(f"New candidate email sync completed for {candidate.email}: {result}")
        return result
        
    except Candidate.DoesNotExist:
        logger.error(f"Candidate with ID {candidate_id} not found")
        return {'error': 'Candidate not found'}
    except Exception as e:
        logger.error(f"New candidate email sync failed: {str(e)}")
        raise


@shared_task
def send_candidate_status_notification(candidate_id, status_update_id):
    """
    Send notification when candidate status is updated
    """
    try:
        candidate = Candidate.objects.get(id=candidate_id)
        status_update = CandidateStatusUpdate.objects.get(id=status_update_id)
        
        # Send email to relevant stakeholders
        subject = f"Candidate Status Update - {candidate.name}"
        
        # Get recipient list (HR, recruiters, hiring managers)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        recipients = User.objects.filter(
            groups__name__in=['HR', 'Recruiters', 'Hiring Managers'],
            is_active=True
        ).values_list('email', flat=True).distinct()
        
        if recipients:
            context = {
                'candidate': candidate,
                'status_update': status_update,
                'updated_by': status_update.updated_by.get_full_name() if status_update.updated_by else 'System'
            }
            
            try:
                html_message = render_to_string('candidate/emails/status_update.html', context)
                plain_message = render_to_string('candidate/emails/status_update.txt', context)
            except:
                # Fallback if templates don't exist
                plain_message = f"""
Candidate Status Update

Candidate: {candidate.name} ({candidate.email})
Previous Status: {status_update.get_previous_status_display()}
New Status: {status_update.get_new_status_display()}
Updated By: {context['updated_by']}
Date: {status_update.updated_at}

Reason: {status_update.reason}
"""
                html_message = plain_message.replace('\n', '<br>')
            
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=list(recipients),
                fail_silently=False
            )
            
            logger.info(f"Status update notification sent for candidate {candidate.email}")
        
        return {'status': 'sent', 'recipients': len(recipients)}
        
    except (Candidate.DoesNotExist, CandidateStatusUpdate.DoesNotExist):
        logger.error(f"Candidate or status update not found")
        return {'error': 'Not found'}
    except Exception as e:
        logger.error(f"Failed to send status notification: {str(e)}")
        raise


@shared_task
def generate_candidate_report(filters=None, format='pdf'):
    """
    Generate candidate report in background
    """
    try:
        from django.db.models import Q
        import io
        import os
        
        # Apply filters
        queryset = Candidate.objects.all()
        
        if filters:
            if filters.get('hiring_status'):
                queryset = queryset.filter(hiring_status=filters['hiring_status'])
            if filters.get('experience_years__gte'):
                queryset = queryset.filter(experience_years__gte=filters['experience_years__gte'])
            # Add more filters as needed
        
        # Generate report
        buffer = io.BytesIO()
        
        if format == 'pdf' and REPORTLAB_AVAILABLE:
            # Generate PDF report
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            # Title
            p.setFont("Helvetica-Bold", 16)
            p.drawString(50, height - 50, "Candidate Report")
            
            # Content
            y_position = height - 100
            p.setFont("Helvetica", 12)
            
            for candidate in queryset[:50]:  # Limit for demo
                text = f"{candidate.name} - {candidate.email} - {candidate.get_hiring_status_display()}"
                p.drawString(50, y_position, text)
                y_position -= 20
                
                if y_position < 50:  # New page if needed
                    p.showPage()
                    y_position = height - 50
            
            p.save()
            
        elif format == 'csv':
            # Generate CSV report
            import csv
            
            # Create StringIO for CSV
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Name', 'Email', 'Status', 'Experience Years', 'Applied Date'])
            
            # Write data
            for candidate in queryset:
                writer.writerow([
                    candidate.name,
                    candidate.email,
                    candidate.get_hiring_status_display(),
                    candidate.experience_years or 'N/A',
                    candidate.applied_at.strftime('%Y-%m-%d') if candidate.applied_at else 'N/A'
                ])
            
            buffer.write(output.getvalue().encode('utf-8'))
            output.close()
        
        else:
            # Fallback to text report
            content = "Candidate Report\n" + "="*50 + "\n\n"
            for candidate in queryset[:100]:
                content += f"{candidate.name} - {candidate.email} - {candidate.get_hiring_status_display()}\n"
            
            buffer.write(content.encode('utf-8'))
        
        # Save file
        filename = f"candidate_report_{format}.{format}"
        filepath = os.path.join(settings.MEDIA_ROOT, 'reports', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
        
        buffer.close()
        
        logger.info(f"Candidate report generated: {filepath}")
        return {'file_path': filepath, 'filename': filename}
        
    except Exception as e:
        logger.error(f"Failed to generate candidate report: {str(e)}")
        raise


@shared_task
def cleanup_old_candidate_data():
    """
    Cleanup old candidate data periodically
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Delete old status updates (older than 2 years)
        cutoff_date = timezone.now() - timedelta(days=730)
        
        deleted_count = CandidateStatusUpdate.objects.filter(
            updated_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old status updates")
        
        # Clean up old temporary files, logs, etc.
        # Add more cleanup logic as needed
        
        return {'deleted_status_updates': deleted_count}
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {str(e)}")
        raise


@shared_task
def process_candidate_cv(attachment_id):
    """
    Process candidate CV in background (extract text, analyze skills, etc.)
    """
    try:
        from .models import CandidateAttachment
        
        attachment = CandidateAttachment.objects.get(id=attachment_id)
        
        # Placeholder for CV processing logic
        # You could integrate with:
        # - PDF text extraction libraries (PyPDF2, pdfplumber)
        # - AI/ML services for skill extraction
        # - Resume parsing services
        
        processing_results = {
            'extracted_text_length': 0,
            'identified_skills': [],
            'experience_years_detected': None,
            'education_detected': [],
            'contact_info': {}
        }
        
        # Update attachment processing status
        attachment.is_processed = True
        attachment.processing_notes = f"Processed successfully: {processing_results}"
        attachment.save()
        
        logger.info(f"CV processed for attachment {attachment_id}")
        return processing_results
        
    except Exception as e:
        logger.error(f"CV processing failed: {str(e)}")
        # Don't fail the attachment creation
        try:
            from .models import CandidateAttachment
            attachment = CandidateAttachment.objects.get(id=attachment_id)
            attachment.processing_notes = f"Processing failed: {str(e)}"
            attachment.save()
        except:
            pass
        return {'error': str(e)}


@shared_task
def send_bulk_candidate_emails(candidate_ids, email_template, subject, sender_id):
    """
    Send bulk emails to candidates
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        sender = User.objects.get(id=sender_id)
        candidates = Candidate.objects.filter(id__in=candidate_ids)
        
        sent_count = 0
        failed_count = 0
        
        for candidate in candidates:
            try:
                context = {
                    'candidate': candidate,
                    'sender': sender
                }
                
                try:
                    html_message = render_to_string(f'candidate/emails/{email_template}.html', context)
                    plain_message = render_to_string(f'candidate/emails/{email_template}.txt', context)
                except:
                    # Fallback if templates don't exist
                    plain_message = f"Dear {candidate.name},\n\nThis is a message from {sender.get_full_name()}.\n\nBest regards,\n{sender.get_full_name()}"
                    html_message = plain_message.replace('\n', '<br>')
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    html_message=html_message,
                    from_email=sender.email,
                    recipient_list=[candidate.email],
                    fail_silently=False
                )
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send email to {candidate.email}: {str(e)}")
                failed_count += 1
        
        logger.info(f"Bulk email completed: {sent_count} sent, {failed_count} failed")
        return {'sent': sent_count, 'failed': failed_count}
        
    except Exception as e:
        logger.error(f"Bulk email failed: {str(e)}")
        raise