# candidate/utils/email_integration.py
from django.db import transaction
from django.db.models import Q
from django.core.files.base import ContentFile
import re
import logging

logger = logging.getLogger(__name__)

# Import models - use try/except to handle import order issues
try:
    from email_service.models import EmailMessage, EmailAttachment
    from candidate.models import (
        Candidate, 
        CandidateEmailConnection, 
        CandidateAttachment
    )
except ImportError as e:
    logger.warning(f"Import error in email_integration: {e}")
    # Define placeholder classes if imports fail
    EmailMessage = None
    EmailAttachment = None
    Candidate = None
    CandidateEmailConnection = None
    CandidateAttachment = None


class CandidateEmailMatcher:
    """Utility class to match emails with candidates and create connections"""
    
    @staticmethod
    def extract_candidate_email_from_message(email_message):
        """Extract candidate email from EmailMessage"""
        if not email_message:
            return None, []
            
        # Check sender first
        sender_email = email_message.from_email.lower() if email_message.from_email else ""
        
        # Check recipients
        recipient_emails = []
        if email_message.to_recipients:
            recipient_emails.extend([r.get('email', '').lower() for r in email_message.to_recipients if 'email' in r])
        if email_message.cc_recipients:
            recipient_emails.extend([r.get('email', '').lower() for r in email_message.cc_recipients if 'email' in r])
            
        return sender_email, recipient_emails
    
    @staticmethod
    def find_candidates_by_email(email_addresses):
        """Find candidates by email addresses"""
        if not Candidate:
            return []
            
        candidates = []
        for email in email_addresses:
            if not email:
                continue
            try:
                candidate = Candidate.objects.get(email__iexact=email)
                candidates.append(candidate)
            except Candidate.DoesNotExist:
                continue
        return candidates
    
    @staticmethod
    def determine_email_direction_and_type(email_message, candidate):
        """Determine if email is inbound/outbound and categorize type"""
        if not email_message or not candidate:
            return False, 'general'
            
        sender_email = email_message.from_email.lower() if email_message.from_email else ""
        candidate_email = candidate.email.lower()
        
        is_inbound = sender_email == candidate_email
        
        # Auto-categorize email type based on subject and content
        subject_lower = email_message.subject.lower() if email_message.subject else ""
        
        email_type = 'general'  # default
        
        # Keywords for different email types
        if any(keyword in subject_lower for keyword in ['application', 'apply', 'cv', 'resume']):
            email_type = 'application'
        elif any(keyword in subject_lower for keyword in ['interview', 'meeting', 'schedule']):
            if any(keyword in subject_lower for keyword in ['invitation', 'invite']):
                email_type = 'interview_invitation'
            elif any(keyword in subject_lower for keyword in ['confirmation', 'confirm']):
                email_type = 'interview_confirmation'
            elif any(keyword in subject_lower for keyword in ['reminder', 'tomorrow']):
                email_type = 'interview_reminder'
            else:
                email_type = 'interview_invitation'
        elif any(keyword in subject_lower for keyword in ['offer', 'congratulations']):
            email_type = 'offer_letter'
        elif any(keyword in subject_lower for keyword in ['reject', 'unfortunately', 'regret']):
            email_type = 'rejection_letter'
        elif any(keyword in subject_lower for keyword in ['follow up', 'follow-up', 'update']):
            email_type = 'follow_up'
        elif any(keyword in subject_lower for keyword in ['feedback', 'reference']):
            email_type = 'feedback_request'
            
        return is_inbound, email_type
    
    @classmethod
    def create_candidate_email_connection(cls, email_message, candidate=None):
        """Create connection between email and candidate"""
        if not CandidateEmailConnection or not email_message:
            logger.warning("CandidateEmailConnection model not available")
            return None
        
        if not candidate:
            # Try to find candidate by email
            sender_email, recipient_emails = cls.extract_candidate_email_from_message(email_message)
            all_emails = [sender_email] + recipient_emails
            candidates = cls.find_candidates_by_email(all_emails)
            
            if not candidates:
                return None
            
            candidate = candidates[0]  # Take first match
        
        # Check if connection already exists
        existing_connection = CandidateEmailConnection.objects.filter(
            candidate=candidate,
            email_message=email_message
        ).first()
        
        if existing_connection:
            return existing_connection
        
        # Determine email properties
        is_inbound, email_type = cls.determine_email_direction_and_type(email_message, candidate)
        
        try:
            # Create new connection
            connection = CandidateEmailConnection.objects.create(
                candidate=candidate,
                email_message=email_message,
                email_type=email_type,
                is_inbound=is_inbound,
                requires_response=is_inbound and email_type in ['application', 'follow_up']
            )
            
            logger.info(f"Created email connection for candidate {candidate.email}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create email connection: {e}")
            return None
    
    @classmethod
    def process_email_attachments(cls, email_connection):
        """Process attachments from email and create candidate attachments"""
        if not EmailAttachment or not CandidateAttachment or not email_connection:
            return []
            
        email_message = email_connection.email_message
        candidate = email_connection.candidate
        
        # Get attachments from email_service
        try:
            email_attachments = EmailAttachment.objects.filter(email=email_message)
        except:
            logger.warning("Could not fetch email attachments")
            return []
        
        candidate_attachments = []
        
        for email_attachment in email_attachments:
            try:
                # Determine file type based on filename
                file_type = cls.determine_attachment_type(email_attachment.file_name)
                
                # Create candidate attachment
                candidate_attachment = CandidateAttachment.objects.create(
                    candidate=candidate,
                    email_connection=email_connection,
                    file_name=email_attachment.file_name,
                    original_file_name=getattr(email_attachment, 'original_file_name', email_attachment.file_name),
                    file_size=getattr(email_attachment, 'file_size', 0),
                    file_type=file_type,
                    mime_type=getattr(email_attachment, 'mime_type', 'application/octet-stream'),
                    description=f"Attachment from email: {email_message.subject}",
                    # Copy file from email attachment if available
                    file=getattr(email_attachment, 'file', None)
                )
                
                # Set as primary CV if it's a CV/Resume
                if file_type == 'cv' and not candidate.attachments.filter(is_primary_cv=True).exists():
                    candidate_attachment.is_primary_cv = True
                    candidate_attachment.save()
                
                candidate_attachments.append(candidate_attachment)
                logger.info(f"Processed attachment {email_attachment.file_name}")
                
            except Exception as e:
                logger.error(f"Failed to process attachment {email_attachment.file_name}: {e}")
        
        return candidate_attachments
    
    @staticmethod
    def determine_attachment_type(filename):
        """Determine attachment type based on filename"""
        if not filename:
            return 'other'
            
        filename_lower = filename.lower()
        
        if any(keyword in filename_lower for keyword in ['cv', 'resume', 'curriculum']):
            return 'cv'
        elif any(keyword in filename_lower for keyword in ['cover', 'letter']):
            return 'cover_letter'
        elif any(keyword in filename_lower for keyword in ['portfolio', 'work', 'sample']):
            return 'portfolio'
        elif any(keyword in filename_lower for keyword in ['certificate', 'certification', 'diploma']):
            return 'certificate'
        elif any(keyword in filename_lower for keyword in ['transcript', 'grade']):
            return 'transcript'
        elif filename_lower.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            return 'photo'
        else:
            return 'other'


class EmailSyncService:
    """Service to sync emails from email_service with candidates"""
    
    @classmethod
    def sync_candidate_emails(cls, candidate_email=None, days_back=30):
        """Sync emails for specific candidate or all candidates"""
        if not EmailMessage:
            logger.warning("EmailMessage model not available")
            return {'processed_emails': 0, 'created_connections': 0}
            
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Get date range
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Get relevant emails from email service
            email_query = EmailMessage.objects.filter(
                received_datetime__gte=start_date,
                received_datetime__lte=end_date
            )
            
            if candidate_email:
                # Filter for specific candidate
                email_query = email_query.filter(
                    Q(from_email__iexact=candidate_email) |
                    Q(to_recipients__contains=[{'email': candidate_email}]) |
                    Q(cc_recipients__contains=[{'email': candidate_email}])
                )
            
            processed_count = 0
            connection_count = 0
            
            for email_message in email_query[:100]:  # Limit for safety
                try:
                    # Try to create candidate connection
                    connection = CandidateEmailMatcher.create_candidate_email_connection(email_message)
                    
                    if connection:
                        connection_count += 1
                        # Process attachments
                        CandidateEmailMatcher.process_email_attachments(connection)
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_message.id}: {e}")
            
            logger.info(f"Email sync completed: {processed_count} processed, {connection_count} connections")
            return {
                'processed_emails': processed_count,
                'created_connections': connection_count
            }
            
        except Exception as e:
            logger.error(f"Email sync failed: {e}")
            return {'processed_emails': 0, 'created_connections': 0}
    
    @classmethod
    def sync_new_candidate_emails(cls, candidate):
        """Sync emails when a new candidate is created"""
        if not candidate or not candidate.email:
            return {'processed_emails': 0, 'created_connections': 0}
            
        # Look for emails from this candidate in the past 90 days
        return cls.sync_candidate_emails(candidate.email, days_back=90)


# Backward compatibility functions
def sync_candidate_emails(candidate_email=None, days_back=30):
    """Backward compatibility function"""
    return EmailSyncService.sync_candidate_emails(candidate_email, days_back)


def sync_new_candidate_emails(candidate):
    """Backward compatibility function"""
    return EmailSyncService.sync_new_candidate_emails(candidate)