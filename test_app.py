"""
Unit Tests for Sally Chemtai Portfolio Application
Tests for routes, forms, email functionality, and database operations
"""

import unittest
import os
from datetime import datetime
from app import app, db, ContactMessage, ContactForm, sanitize_input


class TestConfig:
    """Test configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class BaseTestCase(unittest.TestCase):
    """Base test case setup"""
    
    def setUp(self):
        """Set up test client and database"""
        app.config.from_object(TestConfig)
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()


class TestRoutes(BaseTestCase):
    """Test application routes"""
    
    def test_home_page(self):
        """Test home page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_about_page(self):
        """Test about page loads"""
        response = self.client.get('/about')
        self.assertEqual(response.status_code, 200)
    
    def test_services_page(self):
        """Test services page loads"""
        response = self.client.get('/services')
        self.assertEqual(response.status_code, 200)
    
    def test_resume_page(self):
        """Test resume page loads"""
        response = self.client.get('/resume')
        self.assertEqual(response.status_code, 200)
    
    def test_contact_page_get(self):
        """Test contact page GET request"""
        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 200)
    
    def test_404_error_handling(self):
        """Test 404 error page"""
        response = self.client.get('/nonexistent')
        self.assertEqual(response.status_code, 404)
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'connected')


class TestContactForm(BaseTestCase):
    """Test contact form validation"""
    
    def test_valid_form_submission(self):
        """Test valid contact form submission"""
        with self.client:
            response = self.client.post('/contact', data={
                'name': 'John Doe',
                'email': 'john@example.com',
                'subject': 'Test Subject',
                'message': 'This is a test message with sufficient length'
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            
            # Verify message was saved
            with app.app_context():
                message = ContactMessage.query.filter_by(email='john@example.com').first()
                self.assertIsNotNone(message)
                self.assertEqual(message.name, 'John Doe')
    
    def test_missing_name_field(self):
        """Test form validation - missing name"""
        response = self.client.post('/contact', data={
            'name': '',
            'email': 'john@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message with sufficient length'
        })
        
        self.assertEqual(response.status_code, 200)
        # Form should not be submitted
    
    def test_invalid_email(self):
        """Test form validation - invalid email"""
        response = self.client.post('/contact', data={
            'name': 'John Doe',
            'email': 'invalid-email',
            'subject': 'Test Subject',
            'message': 'This is a test message with sufficient length'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_name_too_short(self):
        """Test form validation - name too short"""
        response = self.client.post('/contact', data={
            'name': 'J',
            'email': 'john@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message with sufficient length'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_invalid_characters_in_name(self):
        """Test form validation - invalid characters in name"""
        response = self.client.post('/contact', data={
            'name': 'John@Doe#123',
            'email': 'john@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message with sufficient length'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_subject_too_short(self):
        """Test form validation - subject too short"""
        response = self.client.post('/contact', data={
            'name': 'John Doe',
            'email': 'john@example.com',
            'subject': 'Hey',
            'message': 'This is a test message with sufficient length'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_message_too_short(self):
        """Test form validation - message too short"""
        response = self.client.post('/contact', data={
            'name': 'John Doe',
            'email': 'john@example.com',
            'subject': 'Test Subject',
            'message': 'Short'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_message_exceeds_max_length(self):
        """Test form validation - message too long"""
        long_message = 'a' * 2001
        response = self.client.post('/contact', data={
            'name': 'John Doe',
            'email': 'john@example.com',
            'subject': 'Test Subject',
            'message': long_message
        })
        
        self.assertEqual(response.status_code, 200)


class TestContactMessage(BaseTestCase):
    """Test ContactMessage model"""
    
    def test_create_contact_message(self):
        """Test creating a contact message"""
        with app.app_context():
            message = ContactMessage(
                name='Jane Doe',
                email='jane@example.com',
                subject='Test Subject',
                message='This is a test message',
                ip_address='127.0.0.1',
                user_agent='Mozilla/5.0'
            )
            db.session.add(message)
            db.session.commit()
            
            saved = ContactMessage.query.filter_by(email='jane@example.com').first()
            self.assertIsNotNone(saved)
            self.assertEqual(saved.name, 'Jane Doe')
    
    def test_message_to_dict(self):
        """Test ContactMessage.to_dict() method"""
        with app.app_context():
            message = ContactMessage(
                name='Test User',
                email='test@example.com',
                subject='Test',
                message='This is a test message',
                ip_address='127.0.0.1'
            )
            db.session.add(message)
            db.session.commit()
            
            msg_dict = message.to_dict()
            self.assertEqual(msg_dict['name'], 'Test User')
            self.assertEqual(msg_dict['email'], 'test@example.com')
            self.assertTrue('created_at' in msg_dict)
    
    def test_message_long_text_truncation(self):
        """Test message truncation in to_dict()"""
        with app.app_context():
            long_message = 'a' * 150
            message = ContactMessage(
                name='Test',
                email='test@example.com',
                subject='Test',
                message=long_message,
                ip_address='127.0.0.1'
            )
            db.session.add(message)
            db.session.commit()
            
            msg_dict = message.to_dict()
            self.assertTrue(msg_dict['message'].endswith('...'))
            self.assertEqual(len(msg_dict['message']), 103)  # 100 chars + '...'
    
    def test_message_timestamps(self):
        """Test message creation timestamp"""
        with app.app_context():
            before = datetime.utcnow()
            message = ContactMessage(
                name='Test',
                email='test@example.com',
                subject='Test',
                message='Test message',
                ip_address='127.0.0.1'
            )
            db.session.add(message)
            db.session.commit()
            after = datetime.utcnow()
            
            self.assertGreaterEqual(message.created_at, before)
            self.assertLessEqual(message.created_at, after)


class TestInputSanitization(BaseTestCase):
    """Test input sanitization"""
    
    def test_sanitize_xss_attack(self):
        """Test sanitization of XSS attacks"""
        xss_input = '<script>alert("XSS")</script>Test'
        cleaned = sanitize_input(xss_input)
        self.assertNotIn('<script>', cleaned)
        self.assertNotIn('alert', cleaned)
    
    def test_sanitize_html_tags(self):
        """Test sanitization removes HTML tags"""
        html_input = '<b>Bold</b> <i>Italic</i>'
        cleaned = sanitize_input(html_input)
        self.assertNotIn('<b>', cleaned)
        self.assertNotIn('</b>', cleaned)
    
    def test_sanitize_preserves_text(self):
        """Test sanitization preserves text content"""
        text_input = 'Hello, this is a clean message!'
        cleaned = sanitize_input(text_input)
        self.assertEqual(cleaned, text_input)
    
    def test_sanitize_empty_string(self):
        """Test sanitization of empty string"""
        result = sanitize_input('')
        self.assertEqual(result, '')
    
    def test_sanitize_none(self):
        """Test sanitization of None"""
        result = sanitize_input(None)
        self.assertIsNone(result)


class TestAPI(BaseTestCase):
    """Test API endpoints"""
    
    def test_contact_messages_count(self):
        """Test contact messages count API"""
        with app.app_context():
            # Create test messages
            for i in range(3):
                message = ContactMessage(
                    name=f'User {i}',
                    email=f'user{i}@example.com',
                    subject='Test',
                    message='Test message',
                    ip_address='127.0.0.1',
                    is_processed=(i % 2 == 0)
                )
                db.session.add(message)
            db.session.commit()
        
        response = self.client.get('/api/contact-messages/count')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data['total_messages'], 3)
        self.assertEqual(data['unprocessed_messages'], 1)
    
    def test_contact_messages_list(self):
        """Test contact messages list API"""
        with app.app_context():
            # Create test messages
            for i in range(5):
                message = ContactMessage(
                    name=f'User {i}',
                    email=f'user{i}@example.com',
                    subject='Test',
                    message='Test message',
                    ip_address='127.0.0.1'
                )
                db.session.add(message)
            db.session.commit()
        
        response = self.client.get('/api/contact-messages/list?limit=3')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(len(data['messages']), 3)
        self.assertEqual(data['total'], 3)
    
    def test_mark_message_processed(self):
        """Test mark message as processed API"""
        with app.app_context():
            message = ContactMessage(
                name='Test',
                email='test@example.com',
                subject='Test',
                message='Test message',
                ip_address='127.0.0.1',
                is_processed=False
            )
            db.session.add(message)
            db.session.commit()
            message_id = message.id
        
        response = self.client.post(f'/api/contact-messages/{message_id}/mark-processed')
        self.assertEqual(response.status_code, 200)
        
        with app.app_context():
            updated = ContactMessage.query.get(message_id)
            self.assertTrue(updated.is_processed)


class TestContextProcessors(BaseTestCase):
    """Test context processors"""
    
    def test_current_year_injection(self):
        """Test current_year is available in templates"""
        response = self.client.get('/')
        # The template should have access to current_year
        self.assertEqual(response.status_code, 200)
    
    def test_site_info_injection(self):
        """Test site_info is available in templates"""
        response = self.client.get('/')
        # The template should have access to site_info
        self.assertEqual(response.status_code, 200)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
