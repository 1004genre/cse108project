from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__, instance_relative_config=True)
# Ensure instance folder exists for the SQLite database and other instance files
os.makedirs(app.instance_path, exist_ok=True)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
# Use a file inside the instance folder so it is not accidentally committed
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'enrollment.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----- Models -----
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'teacher', 'admin'
    
    enrollments = db.relationship('Enrollment', backref='student', lazy=True, foreign_keys='Enrollment.student_id')
    taught_courses = db.relationship('Course', backref='teacher', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    
    enrollments = db.relationship('Enrollment', backref='course', lazy=True, cascade='all, delete-orphan')

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    grade = db.Column(db.Integer, default=0)

# ----- Flask-Admin Setup -----
class SecureModelView(ModelView):
    def is_accessible(self):
        return session.get('role') == 'admin'
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('serve_index'))

class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return session.get('role') == 'admin'
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('serve_index'))

# flask-admin versions differ in supported kwargs; tolerate both constructors
try:
    admin = Admin(app, name='ACME Admin', template_mode='bootstrap3', index_view=SecureAdminIndexView())
except TypeError:
    # older/newer versions might not accept template_mode
    admin = Admin(app, name='ACME Admin', index_view=SecureAdminIndexView())
admin.add_view(SecureModelView(User, db.session))
admin.add_view(SecureModelView(Course, db.session))
admin.add_view(SecureModelView(Enrollment, db.session))

# ----- Initialize Database -----
def init_db():
    with app.app_context():
        db.create_all()
        
        # Check if data already exists
        if User.query.first() is None:
            # Create sample users
            users = [
                User(username='alizehjahan', password=generate_password_hash('password'), 
                     full_name='Alizeh Jahan', role='student'),
                User(username='isha', password=generate_password_hash('password'), 
                     full_name='Isha Mukherjee', role='student'),
                User(username='sivanipotta', password=generate_password_hash('password'), 
                     full_name='Dr Sivani Potta', role='teacher'),
                User(username='drjones', password=generate_password_hash('password'), 
                     full_name='Dr Rebecca Jones', role='teacher'),
                User(username='drsmith', password=generate_password_hash('password'), 
                     full_name='Dr Michael Smith', role='teacher'),
                User(username='admin', password=generate_password_hash('admin'), 
                     full_name='Administrator', role='admin'),
            ]
            
            for user in users:
                db.session.add(user)
            db.session.commit()
            
            # Create sample courses
            courses = [
                Course(name='Physics 121', teacher_id=4, time='TR 11:00-11:50 AM', capacity=10),
                Course(name='CS 106', teacher_id=3, time='MWF 2:00-2:50 PM', capacity=10),
                Course(name='Math 101', teacher_id=5, time='MWF 10:00-10:50 AM', capacity=8),
                Course(name='CS 162', teacher_id=3, time='TR 3:00-3:50 PM', capacity=4),
            ]
            
            for course in courses:
                db.session.add(course)
            db.session.commit()
            
            # Create sample enrollments
            enrollments = [
                Enrollment(student_id=1, course_id=1, grade=88),
                Enrollment(student_id=1, course_id=2, grade=92),
                Enrollment(student_id=2, course_id=1, grade=85),
                Enrollment(student_id=2, course_id=2, grade=90),
                Enrollment(student_id=2, course_id=3, grade=78),
                Enrollment(student_id=2, course_id=4, grade=95),
            ]
            
            for enrollment in enrollments:
                db.session.add(enrollment)
            db.session.commit()

# ----- Routes -----
@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.route("/style.css")
def serve_css():
    return send_from_directory(".", "style.css")

@app.route("/script.js")
def serve_js():
    return send_from_directory(".", "script.js")

# ----- API: Authentication -----
@app.route("/api/login", methods=["POST"])
def login():
    try:
        # Accept JSON (from fetch) or form-encoded fallback (from plain form submit)
        data = request.get_json(silent=True)
        if not data:
            # request.form is empty for JSON; this handles form submissions too
            data = request.form.to_dict() if request.form else {}

        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()

        # Log the attempt (never log the password)
        app.logger.info("Login attempt for username='%s'", username)

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['role'] = user.role

            app.logger.info("Login success for username='%s' (id=%s)", username, user.id)

            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role
                }
            })

        app.logger.warning("Login failed for username='%s': invalid credentials", username)
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

    except Exception as e:
        # Log exception details for debugging
        app.logger.exception("Exception during login for username='%s': %s", data.get('username') if isinstance(data, dict) else 'unknown', e)
        return jsonify({'success': False, 'error': 'Server error'}), 500

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route("/api/current-user", methods=["GET"])
def current_user():
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user': {
                'id': session['user_id'],
                'username': session['username'],
                'full_name': session['full_name'],
                'role': session['role']
            }
        })
    return jsonify({'logged_in': False})

# ----- API: Courses -----
@app.route("/api/courses", methods=["GET"])
def get_courses():
    courses = Course.query.all()
    result = []
    
    for course in courses:
        enrolled_count = Enrollment.query.filter_by(course_id=course.id).count()
        result.append({
            'id': course.id,
            'name': course.name,
            'teacher': course.teacher.full_name,
            'time': course.time,
            'enrolled': enrolled_count,
            'capacity': course.capacity
        })
    
    return jsonify(result)

@app.route("/api/my-courses", methods=["GET"])
def get_my_courses():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    role = session['role']
    
    if role == 'student':
        enrollments = Enrollment.query.filter_by(student_id=user_id).all()
        result = []
        
        for enrollment in enrollments:
            course = enrollment.course
            enrolled_count = Enrollment.query.filter_by(course_id=course.id).count()
            result.append({
                'id': course.id,
                'name': course.name,
                'teacher': course.teacher.full_name,
                'time': course.time,
                'enrolled': enrolled_count,
                'capacity': course.capacity,
                'grade': enrollment.grade
            })
        
        return jsonify(result)
    
    elif role == 'teacher':
        courses = Course.query.filter_by(teacher_id=user_id).all()
        result = []
        
        for course in courses:
            enrolled_count = Enrollment.query.filter_by(course_id=course.id).count()
            result.append({
                'id': course.id,
                'name': course.name,
                'teacher': course.teacher.full_name,
                'time': course.time,
                'enrolled': enrolled_count,
                'capacity': course.capacity
            })
        
        return jsonify(result)
    
    return jsonify([])

@app.route("/api/enroll", methods=["POST"])
def enroll():
    if 'user_id' not in session or session['role'] != 'student':
        return jsonify({'error': 'Not authorized'}), 401
    
    data = request.get_json()
    course_id = data.get('course_id')
    
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    enrolled_count = Enrollment.query.filter_by(course_id=course_id).count()
    if enrolled_count >= course.capacity:
        return jsonify({'error': 'Course is full'}), 400
    
    existing = Enrollment.query.filter_by(student_id=session['user_id'], course_id=course_id).first()
    if existing:
        return jsonify({'error': 'Already enrolled'}), 400
    
    enrollment = Enrollment(student_id=session['user_id'], course_id=course_id, grade=0)
    db.session.add(enrollment)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route("/api/course/<int:course_id>/students", methods=["GET"])
def get_course_students(course_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'error': 'Not authorized'}), 401
    
    course = Course.query.get(course_id)
    if not course or course.teacher_id != session['user_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    result = []
    
    for enrollment in enrollments:
        result.append({
            'enrollment_id': enrollment.id,
            'student_name': enrollment.student.full_name,
            'grade': enrollment.grade
        })
    
    return jsonify(result)

@app.route("/api/enrollment/<int:enrollment_id>/grade", methods=["PUT"])
def update_grade(enrollment_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'error': 'Not authorized'}), 401
    
    enrollment = Enrollment.query.get(enrollment_id)
    if not enrollment:
        return jsonify({'error': 'Enrollment not found'}), 404
    
    if enrollment.course.teacher_id != session['user_id']:
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json()
    new_grade = data.get('grade')
    
    enrollment.grade = new_grade
    db.session.commit()
    
    return jsonify({'success': True})

if __name__ == "__main__":
    init_db()
    app.run(debug=True)


# Ensure DB is initialized once before handling requests (compatible with older Flask)
def _ensure_db_once():
    if not getattr(app, '_db_initialized', False):
        init_db()
        app._db_initialized = True

# Register using before_request so it's compatible with different Flask versions
app.before_request(_ensure_db_once)