import os
import logging
from datetime import datetime
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('portfolio.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
class Config:
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

app.config.from_object(Config)

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
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    is_processed = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
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
                    {message.replace(chr(10), '<br>')}
                </div>
                <hr>
                <p><small>This message was sent from your portfolio website contact form.</small></p>
            </body>
        </html>
        """
        
        msg = Message(
            subject=f"📧 Portfolio Contact: {subject}",
            recipients=[os.environ.get('ADMIN_EMAIL', 'sallychemtai@gmail.com')],
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
                <h2>Thank You for Contacting Sally Chemtai</h2>
                <p>Dear {name},</p>
                <p>Thank you for reaching out through my portfolio website. I have received your message and will get back to you as soon as possible.</p>
                <p>For urgent matters, you can reach me directly at +254 712 507368.</p>
                <hr>
                <p><strong>Sally Chemtai</strong><br>
                Virtual Assistant & Real Estate Officer<br>
                Nairobi, Kenya<br>
                Phone: +254 712 507368<br>
                Email: sallychemtai@gmail.com</p>
                <hr>
                <p><small>This is an automated response. Please do not reply to this email.</small></p>
            </body>
        </html>
        """
        
        msg = Message(
            subject="Thank you for contacting Sally Chemtai",
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
        'site_name': 'Sally Chemtai Portfolio',
        'site_description': 'Professional Virtual Assistant & Real Estate Officer',
        'admin_email': 'sallychemtai@gmail.com'
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
            'database': 'connected'
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
        db.create_all()
        app.logger.info("Database tables created successfully")
        
        # Create admin user if not exists
        # This can be expanded for admin panel later

if __name__ == '__main__':
    init_app()
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    app.logger.info(f"Starting Sally Chemtai Portfolio application on port {port}")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
    