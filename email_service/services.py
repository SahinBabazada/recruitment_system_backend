# email_service/services.py
import requests
import json
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from .models import EmailServiceSetting, EmailMessage, EmailAttachment, EmailSyncLog

logger = logging.getLogger(__name__)

class GraphAPIClient:
    """
    Client for Microsoft Graph API operations
    """
    
    def __init__(self, tenant_id, client_id, client_secret, user_email, user_password):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_email = user_email
        self.user_password = user_password
        self.access_token = None
        self.token_expires_at = None

    def get_access_token(self):
        """
        Get access token using Resource Owner Password Credentials (ROPC) flow
        Note: This requires special configuration in Azure AD
        """
        if self.access_token and self.token_expires_at and timezone.now() < self.token_expires_at:
            return self.access_token

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default',
            'username': self.user_email,
            'password': self.user_password
        }

        try:
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Calculate expiry time (subtract 5 minutes for safety)
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = timezone.now() + timedelta(seconds=expires_in - 300)
            
            logger.info(f"Successfully obtained access token for {self.user_email}")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get access token: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            raise Exception(f"Authentication failed: {str(e)}")

    def make_request(self, endpoint, method='GET', params=None, data=None):
        """
        Make authenticated request to Graph API
        """
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        url = f"https://graph.microsoft.com/v1.0{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Graph API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            raise

    def test_connection(self):
        """
        Test the connection to Graph API
        """
        try:
            result = self.make_request('/me')
            return {
                'success': True,
                'message': f"Connected successfully as {result.get('displayName', 'Unknown')} ({result.get('mail', 'No email')})"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_messages(self, folder='inbox', page_size=50, skip=0, filter_query=None):
        """
        Get email messages from specified folder
        """
        endpoint = f"/me/mailFolders/{folder}/messages"
        
        params = {
            '$top': page_size,
            '$skip': skip,
            '$orderby': 'receivedDateTime desc',
            '$select': ','.join([
                'id', 'conversationId', 'subject', 'bodyPreview', 'body',
                'from', 'toRecipients', 'ccRecipients', 'bccRecipients',
                'importance', 'isRead', 'isDraft', 'hasAttachments',
                'categories', 'parentFolderId',
                'sentDateTime', 'receivedDateTime', 'createdDateTime', 'lastModifiedDateTime'
            ])
        }
        
        if filter_query:
            params['$filter'] = filter_query

        return self.make_request(endpoint, params=params)

    def get_folders(self):
        """
        Get all mail folders
        """
        return self.make_request('/me/mailFolders')

    def get_attachments(self, message_id):
        """
        Get attachments for a specific message
        """
        endpoint = f"/me/messages/{message_id}/attachments"
        return self.make_request(endpoint)


class EmailSyncService:
    """
    Service for synchronizing emails from Graph API
    """
    
    def __init__(self, email_service_setting):
        self.service = email_service_setting
        self.client = None
        
    def _get_client(self):
        """
        Get Graph API client instance
        """
        if not self.client:
            password = self.service.get_password()
            if not password:
                raise Exception("Service password not available")
                
            self.client = GraphAPIClient(
                tenant_id=self.service.tenant_id,
                client_id=self.service.client_id,
                client_secret=self.service.client_secret,
                user_email=self.service.email,
                user_password=password
            )
        return self.client

    def test_connection(self):
        """
        Test connection to Graph API
        """
        try:
            client = self._get_client()
            return client.test_connection()
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def sync_emails(self, folder='inbox', max_emails=None, force_full_sync=False):
        """
        Sync emails from Graph API to database
        """
        sync_log = EmailSyncLog.objects.create(
            service=self.service,
            status='running'
        )
        
        try:
            client = self._get_client()
            
            # Determine sync window
            filter_query = None
            if not force_full_sync and self.service.last_sync_at:
                # Only sync emails newer than last sync
                last_sync = self.service.last_sync_at.isoformat()
                filter_query = f"receivedDateTime gt {last_sync}"
            
            # Get folder information
            folders_response = client.get_folders()
            folder_map = {f['displayName'].lower(): f['id'] for f in folders_response.get('value', [])}
            folder_id = folder_map.get(folder.lower(), folder)
            
            page_size = 50
            skip = 0
            total_processed = 0
            total_created = 0
            total_updated = 0
            
            logger.info(f"Starting email sync for {self.service.name} from folder {folder}")
            
            while True:
                # Get batch of messages
                messages_response = client.get_messages(
                    folder=folder_id,
                    page_size=page_size,
                    skip=skip,
                    filter_query=filter_query
                )
                
                messages = messages_response.get('value', [])
                if not messages:
                    break
                
                # Process batch
                batch_created, batch_updated = self._process_message_batch(messages, folder, sync_log)
                total_created += batch_created
                total_updated += batch_updated
                total_processed += len(messages)
                
                # Update sync log
                sync_log.emails_processed = total_processed
                sync_log.emails_created = total_created
                sync_log.emails_updated = total_updated
                sync_log.save()
                
                logger.info(f"Processed batch: {len(messages)} messages, Total: {total_processed}")
                
                # Check limits
                if max_emails and total_processed >= max_emails:
                    break
                
                # Check for more pages
                if '@odata.nextLink' not in messages_response:
                    break
                
                skip += page_size
            
            # Mark sync as completed
            sync_log.status = 'completed'
            sync_log.sync_completed_at = timezone.now()
            sync_log.save()
            
            # Update service last sync time
            self.service.last_sync_at = timezone.now()
            self.service.save()
            
            logger.info(f"Email sync completed: {total_processed} processed, {total_created} created, {total_updated} updated")
            
            return {
                'success': True,
                'processed': total_processed,
                'created': total_created,
                'updated': total_updated
            }
            
        except Exception as e:
            logger.error(f"Email sync failed: {str(e)}")
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            sync_log.sync_completed_at = timezone.now()
            sync_log.save()
            
            return {
                'success': False,
                'error': str(e)
            }

    def _process_message_batch(self, messages, folder_name, sync_log):
        """
        Process a batch of messages and save to database
        """
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for message_data in messages:
                try:
                    created, updated = self._process_single_message(message_data, folder_name)
                    if created:
                        created_count += 1
                    elif updated:
                        updated_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process message {message_data.get('id', 'unknown')}: {str(e)}")
                    # Continue processing other messages
                    continue
        
        return created_count, updated_count

    def _process_single_message(self, message_data, folder_name):
        """
        Process a single email message
        """
        message_id = message_data['id']
        
        # Check if message already exists
        try:
            email_message = EmailMessage.objects.get(message_id=message_id)
            # Update existing message
            updated = self._update_email_message(email_message, message_data, folder_name)
            return False, updated
        except EmailMessage.DoesNotExist:
            # Create new message
            email_message = self._create_email_message(message_data, folder_name)
            return True, False

    def _create_email_message(self, message_data, folder_name):
        """
        Create new EmailMessage from Graph API data
        """
        # Parse sender information
        from_data = message_data.get('from', {}).get('emailAddress', {})
        from_email = from_data.get('address', '')
        from_name = from_data.get('name', '')
        
        # Parse recipients
        to_recipients = message_data.get('toRecipients', [])
        cc_recipients = message_data.get('ccRecipients', [])
        bcc_recipients = message_data.get('bccRecipients', [])
        
        # Parse body content
        body = message_data.get('body', {})
        body_content = body.get('content', '')
        body_content_type = body.get('contentType', 'html').lower()
        
        # Parse timestamps
        sent_datetime = self._parse_datetime(message_data.get('sentDateTime'))
        received_datetime = self._parse_datetime(message_data.get('receivedDateTime'))
        created_datetime = self._parse_datetime(message_data.get('createdDateTime'))
        last_modified_datetime = self._parse_datetime(message_data.get('lastModifiedDateTime'))
        
        email_message = EmailMessage.objects.create(
            service=self.service,
            message_id=message_data['id'],
            conversation_id=message_data.get('conversationId', ''),
            subject=message_data.get('subject', ''),
            body_preview=message_data.get('bodyPreview', ''),
            body_content=body_content,
            body_content_type=body_content_type,
            from_email=from_email,
            from_name=from_name,
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            importance=message_data.get('importance', 'normal').lower(),
            is_read=message_data.get('isRead', False),
            is_draft=message_data.get('isDraft', False),
            has_attachments=message_data.get('hasAttachments', False),
            categories=message_data.get('categories', []),
            folder_id=message_data.get('parentFolderId', ''),
            folder_name=folder_name,
            sent_datetime=sent_datetime,
            received_datetime=received_datetime,
            created_datetime=created_datetime,
            last_modified_datetime=last_modified_datetime
        )
        
        # Process attachments if any
        if email_message.has_attachments:
            self._sync_attachments(email_message)
        
        return email_message

    def _update_email_message(self, email_message, message_data, folder_name):
        """
        Update existing EmailMessage with latest data
        """
        updated = False
        
        # Check if message was modified since last sync
        last_modified_datetime = self._parse_datetime(message_data.get('lastModifiedDateTime'))
        if last_modified_datetime and last_modified_datetime > email_message.last_modified_datetime:
            # Update fields that might have changed
            email_message.is_read = message_data.get('isRead', False)
            email_message.categories = message_data.get('categories', [])
            email_message.folder_name = folder_name
            email_message.last_modified_datetime = last_modified_datetime
            email_message.save()
            updated = True
        
        return updated

    def _sync_attachments(self, email_message):
        """
        Sync attachments for an email message
        """
        try:
            client = self._get_client()
            attachments_response = client.get_attachments(email_message.message_id)
            
            for attachment_data in attachments_response.get('value', []):
                self._create_attachment(email_message, attachment_data)
                
        except Exception as e:
            logger.error(f"Failed to sync attachments for message {email_message.message_id}: {str(e)}")

    def _create_attachment(self, email_message, attachment_data):
        """
        Create EmailAttachment from Graph API data
        """
        attachment_id = attachment_data['id']
        
        # Check if attachment already exists
        if EmailAttachment.objects.filter(email=email_message, attachment_id=attachment_id).exists():
            return
        
        EmailAttachment.objects.create(
            email=email_message,
            attachment_id=attachment_id,
            name=attachment_data.get('name', ''),
            content_type=attachment_data.get('contentType', ''),
            size=attachment_data.get('size', 0),
            is_inline=attachment_data.get('isInline', False),
            # Note: content_bytes would need separate API call to download
            # For now, we just store metadata
        )

    def _parse_datetime(self, datetime_str):
        """
        Parse ISO datetime string to Django datetime
        """
        if not datetime_str:
            return timezone.now()
        
        try:
            # Remove 'Z' suffix and parse
            if datetime_str.endswith('Z'):
                datetime_str = datetime_str[:-1] + '+00:00'
            
            dt = datetime.fromisoformat(datetime_str)
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse datetime: {datetime_str}")
            return timezone.now()


class EmailAPIService:
    """
    Service for providing email data to frontend
    """
    
    @staticmethod
    def get_emails_for_category(category='inbox', service_id=None, search_query='', page=1, page_size=50):
        """
        Get emails for a specific category/folder
        """
        queryset = EmailMessage.objects.select_related('service')
        
        # Filter by service if specified
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        else:
            # Use default service
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
        
        return [email.to_dict() for email in emails]

    @staticmethod
    def get_email_detail(email_id):
        """
        Get detailed email information
        """
        try:
            email = EmailMessage.objects.select_related('service').get(id=email_id)
            email_dict = email.to_dict()
            
            # Add full body content
            email_dict['content'] = email.body_content
            
            # Add attachments
            attachments = []
            for attachment in email.attachments.all():
                attachments.append({
                    'name': attachment.name,
                    'size': attachment.size,
                    'type': attachment.content_type,
                    'id': attachment.id
                })
            email_dict['attachments'] = attachments
            
            return email_dict
        except EmailMessage.DoesNotExist:
            return None

    @staticmethod
    def mark_as_read(email_id):
        """
        Mark email as read
        """
        try:
            email = EmailMessage.objects.get(id=email_id)
            email.is_read = True
            email.save()
            return True
        except EmailMessage.DoesNotExist:
            return False

    @staticmethod
    def get_folder_counts():
        """
        Get email counts for different folders
        """
        default_service = EmailServiceSetting.get_default_service()
        if not default_service:
            return {}
        
        queryset = EmailMessage.objects.filter(service=default_service)
        
        counts = {
            'inbox': queryset.filter(folder_name__icontains='inbox').count(),
            'sent': queryset.filter(folder_name__icontains='sent').count(),
            'draft': queryset.filter(is_draft=True).count(),
            'unread': queryset.filter(is_read=False).count(),
            'total': queryset.count()
        }
        
        return counts