import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, EmailField
from wtforms.validators import DataRequired, Email, Length
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Configuration
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///contacts.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true',
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME')),
    RECAPTCHA_PUBLIC_KEY=os.environ.get('RECAPTCHA_PUBLIC_KEY'),
    RECAPTCHA_PRIVATE_KEY=os.environ.get('RECAPTCHA_PRIVATE_KEY')
)

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)

# Forms
class ContactForm(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    email = EmailField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=100)
    ])
    subject = StringField('Subject', validators=[
        DataRequired(),
        Length(min=5, max=200)
    ])
    message = TextAreaField('Message', validators=[
        DataRequired(),
        Length(min=10, max=2000)
    ])

# Models
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))

# Create tables
with app.app_context():
    db.create_all()

# Utility functions
def log_contact_message(name, email, subject, message, ip_address):
    try:
        new_message = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message,
            ip_address=ip_address
        )
        db.session.add(new_message)
        db.session.commit()
        return True
    except Exception as e:
        app.logger.error(f"Error saving contact message: {str(e)}")
        db.session.rollback()
        return False

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
def contact():
    form = ContactForm()
    
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        subject = form.subject.data
        message = form.message.data
        ip_address = request.remote_addr

        # Save to database
        if not log_contact_message(name, email, subject, message, ip_address):
            flash('Your message could not be saved. Please try again later.', 'danger')
            return redirect(url_for('contact'))

        # Send email
        try:
            msg = Message(
                subject=f"New Contact: {subject}",
                recipients=[os.environ.get('ADMIN_EMAIL', 'sebbywakis@gmail.com')],
                body=f"""\
Name: {name}
Email: {email}
IP Address: {ip_address}
Time: {datetime.utcnow()}

Message:
{message}
"""
            )
            mail.send(msg)
            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            app.logger.error(f"Error sending email: {str(e)}")
            flash('Your message was saved but could not be sent. We will contact you soon.', 'warning')
            return redirect(url_for('contact'))

    return render_template('contact.html', form=form)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'true').lower() == 'true')



