import os
import logging
import sys
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_wtf import FlaskForm, CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from wtforms import StringField, TextAreaField, EmailField
from wtforms.validators import DataRequired, Email, Length, Regexp
from dotenv import load_dotenv
import bleach

# Load environment variables
load_dotenv()

# Configure logging
def setup_logging():
    """Configure logging for different environments"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_file = os.environ.get('LOG_FILE', 'portfolio.log')
    
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s:%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')

# Configuration
class Config:
    """Base configuration"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///portfolio.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME'))
    
    # Security
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('CSRF_SECRET_KEY', 'csrf-secret-key-change-in-production')
    
    # Rate limiting
    RATELIMIT_STORAGE_URI = os.environ.get('REDIS_URL', 'memory://')
    
    # Site configuration
    SITE_NAME = 'Sally Chemtai Portfolio'
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'sallychemtai@gmail.com')
    PHONE_NUMBER = os.environ.get('PHONE_NUMBER', '+254 712 507368')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Select configuration based on environment
config_name = os.environ.get('FLASK_ENV', 'production')
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
app.config.from_object(config_map.get(config_name, ProductionConfig))

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)
csrf = CSRFProtect(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=app.config['RATELIMIT_STORAGE_URI']
)

# Forms
class ContactForm(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired(message='Please enter your name'),
        Length(min=2, max=100, message='Name must be between 2 and 100 characters'),
        Regexp(r'^[A-Za-z\s\-\'\.]+$', message='Name can only contain letters, spaces, hyphens, and apostrophes')
    ])
    email = EmailField('Email', validators=[
        DataRequired(message='Please enter your email address'),
        Email(message='Please enter a valid email address'),
        Length(max=100, message='Email must be less than 100 characters')
    ])
    subject = StringField('Subject', validators=[
        DataRequired(message='Please enter a subject'),
        Length(min=5, max=200, message='Subject must be between 5 and 200 characters')
    ])
    message = TextAreaField('Message', validators=[
        DataRequired(message='Please enter your message'),
        Length(min=10, max=2000, message='Message must be between 10 and 2000 characters')
    ])

# Models
class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, index=True)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    is_processed = db.Column(db.Boolean, default=False, index=True)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'subject': self.subject,
            'message': self.message[:100] + '...' if len(self.message) > 100 else self.message,
            'created_at': self.created_at.isoformat(),
            'ip_address': self.ip_address,
            'is_processed': self.is_processed
        }
    
    def __repr__(self):
        return f'<ContactMessage {self.id}: {self.email}>'

# Utility functions
def sanitize_input(text):
    """Sanitize user input to prevent XSS attacks"""
    if not text:
        return text
    return bleach.clean(text, tags=[], attributes={}, styles=[], strip=True)

def log_contact_message(name, email, subject, message, ip_address, user_agent):
    """Save contact message to database with sanitization"""
    try:
        sanitized_name = sanitize_input(name)
        sanitized_subject = sanitize_input(subject)
        sanitized_message = sanitize_input(message)
        
        new_message = ContactMessage(
            name=sanitized_name,
            email=email,  # Email is validated separately
            subject=sanitized_subject,
            message=sanitized_message,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(new_message)
        db.session.commit()
        app.logger.info(f"Contact message saved from {email}")
        return new_message.id
    except Exception as e:
        app.logger.error(f"Error saving contact message: {str(e)}")
        db.session.rollback()
        return None

def send_notification_email(name, email, subject, message, message_id):
    """Send email notification about new contact message"""
    try:
        html_body = f"""
        <html>
            <body>
                <h2>New Contact Form Submission</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Subject:</strong> {subject}</p>
                <p><strong>Message ID:</strong> {message_id}</p>
                <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <hr>
                <p><strong>Message:</strong></p>
                <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                    {bleach.clean(message, tags=[], attributes={}, styles=[], strip=True).replace(chr(10), '<br>')}
                </div>
                <hr>
                <p><small>This message was sent from your portfolio website contact form.</small></p>
            </body>
        </html>
        """
        
        msg = Message(
            subject=f"📧 Portfolio Contact: {subject}",
            recipients=[app.config['ADMIN_EMAIL']],
            html=html_body
        )
        mail.send(msg)
        app.logger.info(f"Notification email sent for message ID {message_id}")
        return True
    except Exception as e:
        app.logger.error(f"Error sending email: {str(e)}")
        return False

def send_auto_reply(email, name):
    """Send auto-reply to the user"""
    try:
        html_body = f"""
        <html>
            <body>
                <h2>Thank You for Contacting {app.config['SITE_NAME']}</h2>
                <p>Dear {name},</p>
                <p>Thank you for reaching out through my portfolio website. I have received your message and will get back to you as soon as possible.</p>
                <p>For urgent matters, you can reach me directly at {app.config['PHONE_NUMBER']}.</p>
                <hr>
                <p><strong>Sally Chemtai</strong><br>
                Virtual Assistant & Real Estate Officer<br>
                Nairobi, Kenya<br>
                Phone: {app.config['PHONE_NUMBER']}<br>
                Email: {app.config['ADMIN_EMAIL']}</p>
                <hr>
                <p><small>This is an automated response. Please do not reply to this email.</small></p>
            </body>
        </html>
        """
        
        msg = Message(
            subject=f"Thank you for contacting {app.config['SITE_NAME']}",
            recipients=[email],
            html=html_body
        )
        mail.send(msg)
        app.logger.info(f"Auto-reply sent to {email}")
        return True
    except Exception as e:
        app.logger.error(f"Error sending auto-reply: {str(e)}")
        return False

# Context processors
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.utcnow().year}

@app.context_processor
def inject_site_info():
    return {
        'site_name': app.config['SITE_NAME'],
        'site_description': 'Professional Virtual Assistant & Real Estate Officer',
        'admin_email': app.config['ADMIN_EMAIL'],
        'phone_number': app.config['PHONE_NUMBER']
    }

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/resume')
def resume():
    return render_template('resume.html')

@app.route('/contact', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def contact():
    form = ContactForm()
    
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        subject = form.subject.data
        message = form.message.data
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')

        # Save to database
        message_id = log_contact_message(name, email, subject, message, ip_address, user_agent)
        
        if not message_id:
            flash('Your message could not be saved due to a server error. Please try again later.', 'danger')
            return redirect(url_for('contact'))

        # Send notifications
        email_sent = send_notification_email(name, email, subject, message, message_id)
        auto_reply_sent = send_auto_reply(email, name)

        if email_sent:
            flash('Your message has been sent successfully! I will get back to you soon.', 'success')
        else:
            flash('Your message was saved but we encountered an issue sending the notification. We will still get back to you soon.', 'warning')
            
        if not auto_reply_sent:
            app.logger.warning(f"Auto-reply failed for {email}")

        return redirect(url_for('contact'))

    # Log form errors for debugging
    if form.errors:
        app.logger.warning(f"Form validation errors: {form.errors}")

    return render_template('contact.html', form=form)

# API routes for potential future use
@app.route('/api/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'version': '1.0.0'
        }), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'disconnected',
            'error': str(e)
        }), 500

@app.route('/api/contact-messages/count')
@limiter.limit("30 per minute")
def contact_messages_count():
    """Get count of contact messages (for admin use)"""
    try:
        total_count = ContactMessage.query.count()
        unprocessed_count = ContactMessage.query.filter_by(is_processed=False).count()
        
        return jsonify({
            'total_messages': total_count,
            'unprocessed_messages': unprocessed_count,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        app.logger.error(f"Error getting message count: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/contact-messages/list')
@limiter.limit("30 per minute")
def contact_messages_list():
    """Get list of recent contact messages (for admin use)"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 100)  # Max 100 at a time
        
        messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'messages': [msg.to_dict() for msg in messages],
            'total': len(messages),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        app.logger.error(f"Error getting messages: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/contact-messages/<int:message_id>/mark-processed', methods=['POST'])
@limiter.limit("30 per minute")
def mark_message_processed(message_id):
    """Mark a message as processed"""
    try:
        message = ContactMessage.query.get_or_404(message_id)
        message.is_processed = True
        db.session.commit()
        
        app.logger.info(f"Message {message_id} marked as processed")
        return jsonify({
            'success': True,
            'message': message.to_dict(),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        app.logger.error(f"Error marking message as processed: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning(f"404 error: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f"500 error: {str(e)}")
    db.session.rollback()
    return render_template('500.html'), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    app.logger.warning(f"Rate limit exceeded from {request.remote_addr}")
    flash('Too many requests. Please try again later.', 'warning')
    return redirect(url_for('contact'))

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

# Template filters
@app.template_filter('format_datetime')
def format_datetime(value, format='%B %d, %Y at %I:%M %p'):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value.strftime(format)

@app.template_filter('truncate_text')
def truncate_text(text, length=100):
    if len(text) <= length:
        return text
    return text[:length] + '...'

# Before request handlers
@app.before_request
def log_request_info():
    if request.endpoint and 'static' not in request.endpoint:
        app.logger.info(f"{request.method} {request.url} - {request.remote_addr}")

# Application startup
def init_app():
    """Initialize application with required setup"""
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created/verified successfully")
        except Exception as e:
            app.logger.error(f"Error initializing database: {str(e)}")
            raise

if __name__ == '__main__':
    init_app()
    debug_mode = app.config['DEBUG']
    port = int(os.environ.get('PORT', 5000))
    
    app.logger.info(f"Starting {app.config['SITE_NAME']} on port {port}")
    app.logger.info(f"Environment: {app.config['ENV']}")
    app.logger.info(f"Debug mode: {debug_mode}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
    