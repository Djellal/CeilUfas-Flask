from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Session, ApplicationSettings, Role, State, Municipality
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from functools import wraps

# Load environment variables from .env file
load_dotenv()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

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
    # Create default roles if they don't exist
    admin_role = Role.query.filter_by(name='Admin').first()
    if not admin_role:
        admin_role = Role(name='Admin', color='danger')
        db.session.add(admin_role)
        print("Created Admin role")

    teacher_role = Role.query.filter_by(name='Teacher').first()
    if not teacher_role:
        teacher_role = Role(name='Teacher', color='primary')
        db.session.add(teacher_role)
        print("Created Teacher role")

    student_role = Role.query.filter_by(name='Student').first()
    if not student_role:
        student_role = Role(name='Student', color='success')
        db.session.add(student_role)
        print("Created Student role")

    # Create admin user if it doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', role_id=admin_role.id)
        admin.set_password('admin123')
        db.session.add(admin)
        print("Created admin user")

    # Create teacher user if it doesn't exist
    if not User.query.filter_by(username='teacher').first():
        teacher = User(username='teacher', email='teacher@example.com', role_id=teacher_role.id)
        teacher.set_password('teacher123')
        db.session.add(teacher)
        print("Created teacher user")

    # Create student user if it doesn't exist
    if not User.query.filter_by(username='student').first():
        student = User(username='student', email='student@example.com', role_id=student_role.id)
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
            organization_name="Ceil UFAS1",
            organization_name_ar="سيلاب",
            registration_open=True,
            current_session_id=None,
            logo_path=None,
            address="Université Sétif -1- Campus El Bez, Ex-Faculté de Droit (Actuellement Département d'Agronomie)",
            address_ar="الجامعة الجزائرية الوطنية المستقلة - الحرم الجامعي الأول - منطقة البز, القسم القديم للقانون (الآن قسم الزراعة)",
            telephone="(+213) 036.62.09.96",
            email="ceil@univ-setif.dz",
            website="https://ceil.univ-setif.dz",
            facebook="https://www.facebook.com/CEIL.SETIF1UNIVERSITY",
            linkedin="https://www.linkedin.com/school/universite-ferhat-abbas-setif",
            youtube="https://www.youtube.com/channel/UCjU0ehPWCFlvCHrfgUt3DOQ",
            twitter="https://twitter.com/UnivFerhatAbbas",
            
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
        user = User(username=username, email=email, role_id=student_role.id)
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

@app.route('/users')
@login_required
def users():
    if not current_user.role.name == 'Admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    search = request.args.get('search', '')
    role_id = request.args.get('role', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Build query
    query = User.query

    # Apply filters
    if search:
        query = query.filter(
            db.or_(
                User.name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    if role_id:
        query = query.filter(User.role_id == role_id)
    
    if status == 'active':
        query = query.filter(User.is_active == True)
    elif status == 'inactive':
        query = query.filter(User.is_active == False)

    # Get pagination
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    users = pagination.items

    # Get all roles for filter dropdown
    roles = Role.query.all()

    return render_template('users.html', users=users, roles=roles, pagination=pagination)

@app.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
def update_user(user_id):
    if not current_user.role.name == 'Admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Update user information
    user.name = request.form.get('name')
    user.email = request.form.get('email')
    user.role_id = request.form.get('role_id', type=int)
    user.is_active = 'is_active' in request.form
    
    try:
        db.session.commit()
        flash('User updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating user. Please try again.', 'danger')
    
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.role.name == 'Admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting the last admin
    if user.role.name == 'Admin' and User.query.filter_by(role_id=user.role_id).count() <= 1:
        flash('Cannot delete the last admin user.', 'danger')
        return redirect(url_for('users'))
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user. Please try again.', 'danger')
    
    return redirect(url_for('users'))

# Location Management Routes
@app.route('/locations')
@login_required
@admin_required
def locations():
    states = State.query.all()
    municipalities = Municipality.query.all()
    return render_template('locations.html', states=states, municipalities=municipalities)

@app.route('/states/add', methods=['POST'])
@login_required
@admin_required
def add_state():
    try:
        code = request.form.get('code')
        name = request.form.get('name')
        name_ar = request.form.get('name_ar')

        # Validate required fields
        if not all([code, name, name_ar]):
            flash('All fields are required', 'danger')
            return redirect(url_for('locations'))

        # Check if code already exists
        if State.query.filter_by(code=code).first():
            flash('State code already exists', 'danger')
            return redirect(url_for('locations'))

        # Create new state
        state = State(code=code, name=name, name_ar=name_ar)
        db.session.add(state)
        db.session.commit()

        flash('State added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding state: {str(e)}', 'danger')
    return redirect(url_for('locations'))

@app.route('/states/<int:state_id>/update', methods=['POST'])
@login_required
@admin_required
def update_state(state_id):
    try:
        state = State.query.get_or_404(state_id)
        
        # Update fields
        state.code = request.form.get('code')
        state.name = request.form.get('name')
        state.name_ar = request.form.get('name_ar')

        db.session.commit()
        flash('State updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating state: {str(e)}', 'danger')
    return redirect(url_for('locations'))

@app.route('/states/<int:state_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_state(state_id):
    try:
        state = State.query.get_or_404(state_id)
        
        # Check if state has municipalities
        if state.municipalities:
            flash('Cannot delete state with associated municipalities', 'danger')
            return redirect(url_for('locations'))
        
        db.session.delete(state)
        db.session.commit()
        flash('State deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting state: {str(e)}', 'danger')
    return redirect(url_for('locations'))

@app.route('/municipalities/add', methods=['POST'])
@login_required
@admin_required
def add_municipality():
    try:
        name = request.form.get('name')
        name_ar = request.form.get('name_ar')
        state_id = request.form.get('state_id')

        # Validate required fields
        if not all([name, name_ar, state_id]):
            flash('All fields are required', 'danger')
            return redirect(url_for('locations'))

        # Create new municipality
        municipality = Municipality(name=name, name_ar=name_ar, state_id=state_id)
        db.session.add(municipality)
        db.session.commit()

        flash('Municipality added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding municipality: {str(e)}', 'danger')
    return redirect(url_for('locations'))

@app.route('/municipalities/<int:municipality_id>/update', methods=['POST'])
@login_required
@admin_required
def update_municipality(municipality_id):
    try:
        municipality = Municipality.query.get_or_404(municipality_id)
        
        # Update fields
        municipality.name = request.form.get('name')
        municipality.name_ar = request.form.get('name_ar')
        municipality.state_id = request.form.get('state_id')

        db.session.commit()
        flash('Municipality updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating municipality: {str(e)}', 'danger')
    return redirect(url_for('locations'))

@app.route('/municipalities/<int:municipality_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_municipality(municipality_id):
    try:
        municipality = Municipality.query.get_or_404(municipality_id)
        db.session.delete(municipality)
        db.session.commit()
        flash('Municipality deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting municipality: {str(e)}', 'danger')
    return redirect(url_for('locations'))

if __name__ == '__main__':
    app.run(debug=True) 