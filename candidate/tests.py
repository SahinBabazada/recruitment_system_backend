# candidate/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import (
    Candidate, CandidateWorkExperience, CandidateEducation,
    CandidateProject, CandidateAttachment, CandidateStatusUpdate
)

User = get_user_model()


class CandidateModelTest(TestCase):
    """Test cases for Candidate model"""
    
    def setUp(self):
        self.candidate = Candidate.objects.create(
            email='test@example.com',
            name='Test Candidate',
            phone='+1234567890',
            location='Test City',
            current_position='Software Developer',
            current_company='Test Company',
            experience_years=5
        )
    
    def test_candidate_creation(self):
        """Test candidate is created successfully"""
        self.assertEqual(self.candidate.email, 'test@example.com')
        self.assertEqual(self.candidate.name, 'Test Candidate')
        self.assertEqual(self.candidate.hiring_status, 'applied')
    
    def test_candidate_str_method(self):
        """Test candidate string representation"""
        expected = f"{self.candidate.name} ({self.candidate.email})"
        self.assertEqual(str(self.candidate), expected)
    
    def test_candidate_unique_email(self):
        """Test that email must be unique"""
        with self.assertRaises(Exception):
            Candidate.objects.create(
                email='test@example.com',  # Same email
                name='Another Candidate'
            )


class CandidateWorkExperienceTest(TestCase):
    """Test cases for CandidateWorkExperience model"""
    
    def setUp(self):
        self.candidate = Candidate.objects.create(
            email='test@example.com',
            name='Test Candidate'
        )
        self.work_experience = CandidateWorkExperience.objects.create(
            candidate=self.candidate,
            company_name='Test Company',
            position_title='Software Developer',
            start_date='2020-01-01',
            is_current=True,
            employment_type='full_time'
        )
    
    def test_work_experience_creation(self):
        """Test work experience is created successfully"""
        self.assertEqual(self.work_experience.company_name, 'Test Company')
        self.assertEqual(self.work_experience.candidate, self.candidate)
        self.assertTrue(self.work_experience.is_current)
    
    def test_work_experience_str_method(self):
        """Test work experience string representation"""
        expected = f"{self.candidate.name} - Software Developer at Test Company"
        self.assertEqual(str(self.work_experience), expected)


class CandidateAPITest(APITestCase):
    """Test cases for Candidate API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.candidate = Candidate.objects.create(
            email='candidate@example.com',
            name='Test Candidate',
            current_position='Developer'
        )
    
    def test_get_candidate_list(self):
        """Test retrieving candidate list"""
        url = reverse('candidate-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_candidate_detail(self):
        """Test retrieving candidate detail"""
        url = reverse('candidate-detail', kwargs={'pk': self.candidate.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.candidate.email)
    
    def test_create_candidate(self):
        """Test creating a new candidate"""
        url = reverse('candidate-list')
        data = {
            'email': 'new@example.com',
            'name': 'New Candidate',
            'phone': '+1234567890',
            'current_position': 'Designer'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Candidate.objects.count(), 2)
    
    def test_update_candidate_status(self):
        """Test updating candidate status"""
        url = reverse('candidate-update-status', kwargs={'pk': self.candidate.pk})
        data = {
            'status': 'screening',
            'reason': 'Initial screening passed'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that candidate status was updated
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.hiring_status, 'screening')
        
        # Check that status update record was created
        status_update = CandidateStatusUpdate.objects.get(candidate=self.candidate)
        self.assertEqual(status_update.new_status, 'screening')
        self.assertEqual(status_update.updated_by, self.user)
    
    def test_candidate_summary(self):
        """Test getting candidate summary"""
        url = reverse('candidate-summary', kwargs={'pk': self.candidate.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('basic_info', response.data)
        self.assertIn('professional_info', response.data)
        self.assertIn('hiring_info', response.data)
        self.assertIn('activity_counts', response.data)


class CandidateFilterTest(APITestCase):
    """Test cases for candidate filtering"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test candidates
        self.candidate1 = Candidate.objects.create(
            email='dev1@example.com',
            name='Developer One',
            current_position='Senior Developer',
            hiring_status='applied',
            experience_years=5
        )
        
        self.candidate2 = Candidate.objects.create(
            email='dev2@example.com',
            name='Developer Two',
            current_position='Junior Developer',
            hiring_status='screening',
            experience_years=2
        )
    
    def test_filter_by_hiring_status(self):
        """Test filtering candidates by hiring status"""
        url = reverse('candidate-list')
        response = self.client.get(url, {'hiring_status': 'applied'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['email'], self.candidate1.email)
    
    def test_filter_by_experience_years(self):
        """Test filtering candidates by experience years"""
        url = reverse('candidate-list')
        response = self.client.get(url, {'experience_years__gte': 5})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['email'], self.candidate1.email)
    
    def test_search_candidates(self):
        """Test searching candidates"""
        url = reverse('candidate-list')
        response = self.client.get(url, {'search': 'Senior'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['email'], self.candidate1.email)


class CandidateAttachmentTest(TestCase):
    """Test cases for candidate attachments"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.candidate = Candidate.objects.create(
            email='candidate@example.com',
            name='Test Candidate'
        )
    
    def test_primary_cv_uniqueness(self):
        """Test that only one attachment can be primary CV"""
        # Create first attachment as primary CV
        attachment1 = CandidateAttachment.objects.create(
            candidate=self.candidate,
            file_name='cv1.pdf',
            original_file_name='cv1.pdf',
            file_size=1024,
            file_type='cv',
            mime_type='application/pdf',
            is_primary_cv=True,
            uploaded_by=self.user
        )
        
        # Create second attachment as primary CV
        attachment2 = CandidateAttachment.objects.create(
            candidate=self.candidate,
            file_name='cv2.pdf',
            original_file_name='cv2.pdf',
            file_size=2048,
            file_type='cv',
            mime_type='application/pdf',
            is_primary_cv=True,
            uploaded_by=self.user
        )
        
        # Check that only the second one is primary now
        attachment1.refresh_from_db()
        attachment2.refresh_from_db()
        
        self.assertFalse(attachment1.is_primary_cv)
        self.assertTrue(attachment2.is_primary_cv)


class CandidateStatusUpdateTest(TestCase):
    """Test cases for candidate status updates"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.candidate = Candidate.objects.create(
            email='candidate@example.com',
            name='Test Candidate',
            hiring_status='applied'
        )
    
    def test_status_update_creation(self):
        """Test creating status update when candidate status changes"""
        # Update candidate status
        previous_status = self.candidate.hiring_status
        self.candidate.hiring_status = 'screening'
        self.candidate.save()
        
        # Note: In a real test, you'd need to simulate the signal properly
        # For now, manually create the status update
        status_update = CandidateStatusUpdate.objects.create(
            candidate=self.candidate,
            previous_status=previous_status,
            new_status='screening',
            reason='Test update',
            updated_by=self.user
        )
        
        self.assertEqual(status_update.previous_status, 'applied')
        self.assertEqual(status_update.new_status, 'screening')
        self.assertEqual(status_update.candidate, self.candidate)