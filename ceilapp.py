from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Session, ApplicationSettings
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ceilapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_default_users():
    # Create admin user if it doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        print("Created admin user")

    # Create teacher user if it doesn't exist
    if not User.query.filter_by(username='teacher').first():
        teacher = User(username='teacher', email='teacher@example.com', role='teacher')
        teacher.set_password('teacher123')
        db.session.add(teacher)
        print("Created teacher user")

    # Create student user if it doesn't exist
    if not User.query.filter_by(username='student').first():
        student = User(username='student', email='student@example.com', role='student')
        student.set_password('student123')
        db.session.add(student)
        print("Created student user")

    try:
        db.session.commit()
        print("Default users created successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default users: {e}")

def create_default_settings():
    if not ApplicationSettings.query.first():
        settings = ApplicationSettings(
            organization_name="CeilApp",
            organization_name_ar="سيلاب",
            registration_open=False
        )
        db.session.add(settings)
        try:
            db.session.commit()
            print("Default settings created successfully")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default settings: {e}")

# Create database tables and default data
with app.app_context():
    db.create_all()
    create_default_users()
    create_default_settings()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    # Check if registration is open
    settings = ApplicationSettings.query.first()
    if not settings or not settings.registration_open:
        flash('Registration is currently closed.', 'warning')
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not username or not email or not password:
            flash('All fields are required')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
            
        # Create new user with student role
        user = User(username=username, email=email, role='student')
        user.set_password(password)
        db.session.add(user)
        
        try:
            db.session.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.')
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Session Management Routes
@app.route('/sessions')
@login_required
def sessions():
    sessions = Session.query.all()
    return render_template('sessions.html', sessions=sessions)

@app.route('/session/add', methods=['POST'])
@login_required
def add_session():
    if not current_user.is_admin():
        flash('You do not have permission to add sessions', 'danger')
        return redirect(url_for('sessions'))
        
    try:
        code = request.form.get('code')
        name = request.form.get('name')
        name_ar = request.form.get('name_ar')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        
        if Session.query.filter_by(code=code).first():
            flash('Session code already exists', 'danger')
            return redirect(url_for('sessions'))
            
        session = Session(
            code=code,
            name=name,
            name_ar=name_ar,
            start_date=start_date,
            end_date=end_date
        )
        db.session.add(session)
        db.session.commit()
        flash('Session added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error adding session', 'danger')
        
    return redirect(url_for('sessions'))

@app.route('/session/<int:session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
        
    session = Session.query.get_or_404(session_id)
    return jsonify({
        'id': session.id,
        'code': session.code,
        'name': session.name,
        'name_ar': session.name_ar,
        'start_date': session.start_date.strftime('%Y-%m-%d'),
        'end_date': session.end_date.strftime('%Y-%m-%d')
    })

@app.route('/session/edit', methods=['POST'])
@login_required
def edit_session():
    if not current_user.is_admin():
        flash('You do not have permission to edit sessions', 'danger')
        return redirect(url_for('sessions'))
        
    try:
        session_id = request.form.get('session_id')
        session = Session.query.get_or_404(session_id)
        
        code = request.form.get('code')
        if code != session.code and Session.query.filter_by(code=code).first():
            flash('Session code already exists', 'danger')
            return redirect(url_for('sessions'))
            
        session.code = code
        session.name = request.form.get('name')
        session.name_ar = request.form.get('name_ar')
        session.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        session.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        
        db.session.commit()
        flash('Session updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating session', 'danger')
        
    return redirect(url_for('sessions'))

@app.route('/session/<int:session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        session = Session.query.get_or_404(session_id)
        db.session.delete(session)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Settings Management Routes
@app.route('/settings')
@login_required
def settings():
    if not current_user.is_admin():
        flash('You do not have permission to access settings', 'danger')
        return redirect(url_for('dashboard'))
        
    settings = ApplicationSettings.query.first()
    sessions = Session.query.all()
    return render_template('settings.html', settings=settings, sessions=sessions)

@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    if not current_user.is_admin():
        flash('You do not have permission to update settings', 'danger')
        return redirect(url_for('dashboard'))
        
    try:
        settings = ApplicationSettings.query.first()
        
        # Handle logo upload
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                settings.logo_path = f'/static/uploads/{filename}'
        
        # Update other settings
        settings.organization_name = request.form.get('organization_name')
        settings.organization_name_ar = request.form.get('organization_name_ar')
        settings.address = request.form.get('address')
        settings.address_ar = request.form.get('address_ar')
        settings.telephone = request.form.get('telephone')
        settings.email = request.form.get('email')
        settings.website = request.form.get('website')
        settings.facebook = request.form.get('facebook')
        settings.linkedin = request.form.get('linkedin')
        settings.youtube = request.form.get('youtube')
        settings.twitter = request.form.get('twitter')
        settings.current_session_id = request.form.get('current_session_id') or None
        settings.registration_open = 'registration_open' in request.form
        
        db.session.commit()
        flash('Settings updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating settings', 'danger')
        
    return redirect(url_for('settings'))

@app.context_processor
def inject_settings():
    settings = ApplicationSettings.query.first()
    return dict(settings=settings)

if __name__ == '__main__':
    app.run(debug=True) 