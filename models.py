from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='student')  # 'admin', 'teacher', or 'student'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_student(self):
        return self.role == 'student'

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Session {self.code}>'

class ApplicationSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_name = db.Column(db.String(200), nullable=False)
    organization_name_ar = db.Column(db.String(200), nullable=False)
    logo_path = db.Column(db.String(255))
    address = db.Column(db.Text)
    address_ar = db.Column(db.Text)
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(255))
    facebook = db.Column(db.String(255))
    linkedin = db.Column(db.String(255))
    youtube = db.Column(db.String(255))
    twitter = db.Column(db.String(255))
    current_session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    registration_open = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with Session
    current_session = db.relationship('Session', foreign_keys=[current_session_id])

    def __repr__(self):
        return f'<ApplicationSettings {self.organization_name}>' 