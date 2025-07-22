
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contacts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)  # Changed from 25 to 100 for more realistic email lengths
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# to create table 
with app.app_context():  # Fixed typo: app_app_context to app_context
    db.create_all()

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
    if request.method == 'POST':
        name = request.form.get('name')  # Fixed: get() is a method, not a dictionary access
        email = request.form.get('email')
        message = request.form.get('message')
        
        if not name or not email or not message:  # Fixed typo: 'massage' to 'message'
            flash('All fields are required!', 'error') 
            return redirect(url_for('contact'))

        # save data to the database
        new_message = ContactMessage(name=name, email=email, message=message)  # Fixed class name and parameters
        db.session.add(new_message)
        db.session.commit()

        flash('Your message has been sent!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')


if __name__ == '__main__':
    app.run(debug=True)