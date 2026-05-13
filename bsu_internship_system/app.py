

from flask import Flask, request, jsonify, session, send_from_directory, redirect, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pymysql, pymysql.cursors, os, datetime, functools

# ─────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'bsu-ojt-secret-2024-lipa'

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXT = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─────────────────────────────────────────
# MySQL Configuration
# Update these values to match your MySQL server, or set environment variables.
# ─────────────────────────────────────────
DB_CONFIG = {
    'host':        os.environ.get('MYSQL_HOST',     'localhost'),
    'port':        int(os.environ.get('MYSQL_PORT', 3306)),
    'user':        os.environ.get('MYSQL_USER',     'root'),
    'password':    os.environ.get('MYSQL_PASSWORD', ''),
    'database':    os.environ.get('MYSQL_DB',       'bsu_ojt'),
    'charset':     'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit':  False,
}

# ─────────────────────────────────────────
# CORS helper
# ─────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return '', 204

# ─────────────────────────────────────────
# DB Helper
# ─────────────────────────────────────────
def get_db():
    return pymysql.connect(**DB_CONFIG)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ─────────────────────────────────────────
# Auth decorators
# ─────────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Unauthorized'}), 401
            if session.get('role') not in roles:
                return jsonify({'error': 'Forbidden'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ─────────────────────────────────────────
# DATABASE SCHEMA (MySQL syntax)
# ─────────────────────────────────────────
SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS departments (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        code       VARCHAR(20) NOT NULL UNIQUE,
        name       VARCHAR(200) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS programs (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        dept_id        INT NOT NULL,
        code           VARCHAR(30) NOT NULL UNIQUE,
        name           VARCHAR(200) NOT NULL,
        required_hours INT DEFAULT 486,
        created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (dept_id) REFERENCES departments(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS offices (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        name        VARCHAR(200) NOT NULL UNIQUE,
        description TEXT,
        category    VARCHAR(100) DEFAULT 'University Office',
        slots       INT DEFAULT 5,
        address     VARCHAR(200) DEFAULT 'BSU Lipa Campus',
        is_active   TINYINT(1) DEFAULT 1,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS users (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        full_name     VARCHAR(200) NOT NULL,
        email         VARCHAR(200) NOT NULL UNIQUE,
        password_hash VARCHAR(256) NOT NULL,
        role          ENUM('student','facilitator','admin') NOT NULL,
        sr_code       VARCHAR(50),
        dept_id       INT,
        program_id    INT,
        status        ENUM('active','inactive','suspended') DEFAULT 'active',
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (dept_id)    REFERENCES departments(id) ON DELETE SET NULL,
        FOREIGN KEY (program_id) REFERENCES programs(id)   ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS applications (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        student_id     INT NOT NULL,
        office_id      INT NOT NULL,
        facilitator_id INT,
        status         ENUM('pending','approved','rejected','ongoing','completed') DEFAULT 'pending',
        remarks        TEXT,
        applied_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id)     REFERENCES users(id)   ON DELETE CASCADE,
        FOREIGN KEY (office_id)      REFERENCES offices(id),
        FOREIGN KEY (facilitator_id) REFERENCES users(id)   ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS documents (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        student_id     INT NOT NULL,
        application_id INT,
        doc_type       VARCHAR(100) NOT NULL,
        filename       VARCHAR(300) NOT NULL,
        original_name  VARCHAR(300) NOT NULL,
        file_size      INT,
        status         ENUM('pending','approved','rejected') DEFAULT 'pending',
        uploaded_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id)     REFERENCES users(id)        ON DELETE CASCADE,
        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS evaluations (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        application_id INT NOT NULL,
        evaluator_id   INT NOT NULL,
        score          FLOAT,
        attendance     INT   DEFAULT 0,
        performance    FLOAT DEFAULT 0,
        attitude       FLOAT DEFAULT 0,
        skills         FLOAT DEFAULT 0,
        comments       TEXT,
        evaluated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
        FOREIGN KEY (evaluator_id)   REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS ojt_hours (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        application_id INT NOT NULL,
        date           DATE NOT NULL,
        hours_rendered FLOAT DEFAULT 0,
        time_in        VARCHAR(10),
        time_out       VARCHAR(10),
        remarks        TEXT,
        logged_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS attendance (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        application_id INT NOT NULL,
        student_id     INT NOT NULL,
        date           DATE NOT NULL,
        status         VARCHAR(20) NOT NULL DEFAULT 'present',
        time_in        VARCHAR(10),
        time_out       VARCHAR(10),
        hours_rendered FLOAT DEFAULT 0,
        remarks        TEXT,
        logged_by      INT,
        created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id)     REFERENCES users(id),
        FOREIGN KEY (logged_by)      REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

]

# Indexes created separately with existence check (MySQL has no CREATE INDEX IF NOT EXISTS)
INDEX_STATEMENTS = [
    ("idx_att_app",     "attendance", "application_id"),
    ("idx_att_student", "attendance", "student_id"),
    ("idx_att_date",    "attendance", "date"),
]

SEED_STATEMENTS = [
    # Departments
    "INSERT IGNORE INTO departments (code,name) VALUES ('CABE','College of Accountancy, Business and Economics')",
    "INSERT IGNORE INTO departments (code,name) VALUES ('CTE','College of Teacher Education')",
    "INSERT IGNORE INTO departments (code,name) VALUES ('CAS','College of Arts and Sciences')",
    "INSERT IGNORE INTO departments (code,name) VALUES ('CET','College of Engineering Technology')",
    "INSERT IGNORE INTO departments (code,name) VALUES ('CICS','College of Informatics and Computing Sciences')",
    # Programs
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSBA-HRM','BS in Business Administration - Human Resource Management',300 FROM departments WHERE code='CABE'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSBA-MM','BS in Business Administration - Marketing Management',300 FROM departments WHERE code='CABE'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSBA-OM','BS in Business Administration - Operations Management',300 FROM departments WHERE code='CABE'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSMA','BS in Management Accounting',300 FROM departments WHERE code='CABE'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BPA','Bachelor in Public Administration',300 FROM departments WHERE code='CABE'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSED-ENG','BS in Secondary Education - English',300 FROM departments WHERE code='CTE'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSED-MATH','BS in Secondary Education - Mathematics',300 FROM departments WHERE code='CTE'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSED-SCI','BS in Secondary Education - Sciences',300 FROM departments WHERE code='CTE'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSPSY','BS in Psychology',300 FROM departments WHERE code='CAS'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BACOMM','BA in Communication',300 FROM departments WHERE code='CAS'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BCET','Bachelor of Computer Engineering Technology',486 FROM departments WHERE code='CET'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BEET','Bachelor of Electrical Engineering Technology',486 FROM departments WHERE code='CET'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BELECET','Bachelor of Electronics Engineering Technology',486 FROM departments WHERE code='CET'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BICET','Bachelor of Instrumentation and Control Engineering Technology',486 FROM departments WHERE code='CET'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSIT-BA','BS in Information Technology - Business Analytics',486 FROM departments WHERE code='CICS'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSIT-NT','BS in Information Technology - Network Technology',486 FROM departments WHERE code='CICS'",
    "INSERT IGNORE INTO programs (dept_id,code,name,required_hours) SELECT id,'BSIT-SM','BS in Information Technology - Service Management',486 FROM departments WHERE code='CICS'",
    # Offices
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Extension Service Office','Handles extension and community outreach programs of BSU Lipa Campus.','University Office',5)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Gender and Development Office','Promotes gender equality and women\\'s rights programs within the campus.','University Office',4)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Office of Guidance and Counseling','Provides psychological guidance, counseling, and career development services.','University Office',3)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Office of the Culture and Arts','Manages cultural programs, arts events, and student creative activities.','University Office',4)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Office of Sports and Development','Oversees athletic programs, sports competitions, and physical fitness activities.','University Office',5)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('On-The-Job Training Office','Coordinates and monitors OJT placements for all students of BSU Lipa.','University Office',6)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Registrar\\'s Office','Manages student academic records, enrollment, and official documents.','University Office',5)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Research Office','Facilitates faculty and student research initiatives and publications.','University Office',4)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Resource Generation Office','Handles revenue-generating projects and resource mobilization for the campus.','University Office',3)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Sustainable Development Office','Promotes sustainable practices, environmental programs, and green initiatives.','University Office',4)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Testing and Admission Office','Manages student admissions, entrance examinations, and enrollment processes.','University Office',5)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('ICT Services','Provides information and communications technology support for BSU Lipa.','University Office',8)",
    "INSERT IGNORE INTO offices (name,description,category,slots) VALUES ('Office of Library Services','Manages the campus library, e-resources, and information literacy programs.','University Office',5)",
]

def init_db():
    """Create tables, seed data, and set real password hashes."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for stmt in SCHEMA_STATEMENTS:
                cur.execute(stmt)
            # Create indexes safely — MySQL has no CREATE INDEX IF NOT EXISTS
            for idx_name, tbl, col in INDEX_STATEMENTS:
                cur.execute("""
                    SELECT COUNT(*) AS cnt FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                      AND table_name = %s AND index_name = %s
                """, (tbl, idx_name))
                if cur.fetchone()['cnt'] == 0:
                    cur.execute(f"CREATE INDEX {idx_name} ON {tbl}({col})")
            for stmt in SEED_STATEMENTS:
                cur.execute(stmt)

        # Seed default users
        seed_users = [
            ('System Administrator', 'admin@batstate-u.edu.ph',       'admin',       'ADM-001', 'CABE', None),
            ('Ms. Maria Santos',     'mjsantos@batstate-u.edu.ph',    'facilitator', 'FAC-001', 'CABE', None),
            ('Juan Dela Cruz',       '24-36106@g.batstate-u.edu.ph',  'student',     '24-36106','CABE','BSBA-HRM'),
            ('Ana Reyes',            '24-10021@g.batstate-u.edu.ph',  'student',     '24-10021','CABE','BSBA-HRM'),
        ]
        with conn.cursor() as cur:
            for full_name, email, role, sr_code, dept_code, prog_code in seed_users:
                cur.execute("SELECT id FROM users WHERE email=%s", (email,))
                if cur.fetchone():
                    continue
                dept_id = prog_id = None
                if dept_code:
                    cur.execute("SELECT id FROM departments WHERE code=%s", (dept_code,))
                    r = cur.fetchone()
                    dept_id = r['id'] if r else None
                if prog_code:
                    cur.execute("SELECT id FROM programs WHERE code=%s", (prog_code,))
                    r = cur.fetchone()
                    prog_id = r['id'] if r else None
                cur.execute("""
                    INSERT IGNORE INTO users
                        (full_name, email, password_hash, role, sr_code, dept_id, program_id, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'active')
                """, (full_name, email, 'placeholder', role, sr_code, dept_id, prog_id))

        # Set real password hashes
        pw_map = {
            'admin@batstate-u.edu.ph':           'admin123',
            'mjsantos@batstate-u.edu.ph':        'facilitator123',
            '24-36106@g.batstate-u.edu.ph':      'student123',
            '24-10021@g.batstate-u.edu.ph':      'student123',
        }
        with conn.cursor() as cur:
            for email, pw in pw_map.items():
                cur.execute("UPDATE users SET password_hash=%s WHERE email=%s",
                            (generate_password_hash(pw), email))

        conn.commit()
        print("✅ MySQL Database initialized.")
    finally:
        conn.close()

# ─────────────────────────────────────────
# SERVE HTML PAGES
# ─────────────────────────────────────────
@app.route('/')
def root():
    return redirect('/login')

@app.route('/login')
def page_login():
    return render_template('login.html')

@app.route('/register')
def page_register():
    return render_template('register.html')

@app.route('/dashboard')
def page_dashboard():
    return render_template('dashboard.html')

@app.route('/admin_dashboard')
def page_admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/facilitator_dashboard')
def page_facilitator_dashboard():
    return render_template('facilitator_dashboard.html')

@app.route('/apply')
def page_apply():
    return render_template('apply.html')

@app.route('/status')
def page_status():
    return render_template('status.html')

@app.route('/upload')
def page_upload():
    return render_template('upload.html')

@app.route('/profile')
def page_profile():
    return render_template('profile.html')

@app.route('/attendance')
def page_attendance():
    return render_template('attendance.html')

@app.route('/my_attendance')
def page_my_attendance():
    return render_template('my_attendance.html')

@app.route('/index')
def page_index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/uploads/<filename>')
@login_required
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()
    role     = (data.get('role') or '').strip()

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE email=%s AND status='active'",
                (email,)
            )
            user = cur.fetchone()
    finally:
        conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials. Please try again.'}), 401

    session['user_id'] = user['id']
    session['role']    = user['role']
    session['name']    = user['full_name']

    return jsonify({
        'message': 'Login successful',
        'user': {
            'id':        user['id'],
            'full_name': user['full_name'],
            'email':     user['email'],
            'role':      user['role'],
            'sr_code':   user['sr_code'],
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully.'})

@app.route('/api/auth/register', methods=['POST'])
def register():
    d          = request.get_json()
    full_name  = (d.get('full_name') or '').strip()
    email      = (d.get('email') or '').strip().lower()
    password   = (d.get('password') or '').strip()
    role       = (d.get('role') or '').strip()
    sr_code    = (d.get('sr_code') or '').strip()
    dept_id    = d.get('dept_id')
    program_id = d.get('program_id')

    if not all([full_name, email, password, role]):
        return jsonify({'error': 'Full name, email, password, and role are required.'}), 400
    if role not in ('student', 'facilitator', 'admin'):
        return jsonify({'error': 'Invalid role specified.'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters.'}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                return jsonify({'error': 'An account with this email already exists.'}), 409

            status = 'active' if role == 'admin' else 'inactive'
            cur.execute("""
                INSERT INTO users
                    (full_name, email, password_hash, role, sr_code, dept_id, program_id, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (full_name, email, generate_password_hash(password), role,
                  sr_code or None, dept_id or None, program_id or None, status))
            conn.commit()
            cur.execute("SELECT * FROM users WHERE id=%s", (cur.lastrowid,))
            u = cur.fetchone()
    except pymysql.IntegrityError as ex:
        conn.rollback()
        return jsonify({'error': str(ex)}), 409
    finally:
        conn.close()

    return jsonify({
        'message': 'Account created. Admins can log in immediately. Others await approval.',
        'user': {'id': u['id'], 'full_name': u['full_name'], 'email': u['email'], 'role': u['role']}
    }), 201

@app.route('/api/auth/me', methods=['GET'])
@login_required
def me():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.*, d.name AS dept_name, p.name AS program_name
                FROM users u
                LEFT JOIN departments d ON d.id = u.dept_id
                LEFT JOIN programs    p ON p.id = u.program_id
                WHERE u.id = %s
            """, (session['user_id'],))
            user = cur.fetchone()
    finally:
        conn.close()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user)

# FIX 1 — This route (and the ones below) were defined AFTER app.run()
# in the original file, so Flask never registered them.
@app.route('/api/auth/profile', methods=['PUT'])
@login_required
def update_profile():
    d   = request.get_json()
    uid = session['user_id']
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if d.get('new_password'):
                cur.execute("SELECT password_hash FROM users WHERE id=%s", (uid,))
                user = cur.fetchone()
                if not user or not check_password_hash(user['password_hash'], d.get('current_password', '')):
                    return jsonify({'error': 'Current password is incorrect.'}), 400
                cur.execute(
                    "UPDATE users SET full_name=%s, password_hash=%s WHERE id=%s",
                    (d.get('full_name', ''), generate_password_hash(d['new_password']), uid)
                )
            else:
                cur.execute("UPDATE users SET full_name=%s WHERE id=%s",
                            (d.get('full_name', ''), uid))
            conn.commit()
            cur.execute("""
                SELECT u.*, d.name AS dept_name, p.name AS program_name
                FROM users u
                LEFT JOIN departments d ON d.id=u.dept_id
                LEFT JOIN programs    p ON p.id=u.program_id
                WHERE u.id=%s
            """, (uid,))
            u = cur.fetchone()
    finally:
        conn.close()
    return jsonify(u)

# ─────────────────────────────────────────
# OFFICES
# ─────────────────────────────────────────
@app.route('/api/offices', methods=['GET'])
def get_offices():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM offices WHERE is_active=1 ORDER BY name")
            offices = cur.fetchall()
    finally:
        conn.close()
    return jsonify(offices)

@app.route('/api/offices', methods=['POST'])
@role_required('admin')
def create_office():
    d = request.get_json()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO offices (name,description,category,slots,address) VALUES (%s,%s,%s,%s,%s)",
                (d['name'], d.get('description',''), d.get('category','University Office'),
                 d.get('slots',5), d.get('address','BSU Lipa Campus'))
            )
            conn.commit()
            cur.execute("SELECT * FROM offices WHERE id=%s", (cur.lastrowid,))
            o = cur.fetchone()
    except pymysql.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Office already exists.'}), 409
    finally:
        conn.close()
    return jsonify(o), 201

@app.route('/api/offices/<int:oid>', methods=['PUT'])
@role_required('admin')
def update_office(oid):
    d = request.get_json()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""UPDATE offices SET name=%s, description=%s, category=%s,
                           slots=%s, address=%s, is_active=%s WHERE id=%s""",
                        (d['name'], d.get('description',''), d.get('category','University Office'),
                         d.get('slots',5), d.get('address','BSU Lipa Campus'),
                         d.get('is_active',1), oid))
            conn.commit()
            cur.execute("SELECT * FROM offices WHERE id=%s", (oid,))
            o = cur.fetchone()
    finally:
        conn.close()
    return jsonify(o)

@app.route('/api/offices/<int:oid>', methods=['DELETE'])
@role_required('admin')
def delete_office(oid):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE offices SET is_active=0 WHERE id=%s", (oid,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'message': 'Office deactivated.'})

# ─────────────────────────────────────────
# USERS
# ─────────────────────────────────────────
@app.route('/api/users', methods=['GET'])
@role_required('admin', 'facilitator')
def get_users():
    role_filter = request.args.get('role')
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if role_filter:
                cur.execute("""
                    SELECT u.*, d.name AS dept_name, p.name AS program_name
                    FROM users u
                    LEFT JOIN departments d ON d.id=u.dept_id
                    LEFT JOIN programs    p ON p.id=u.program_id
                    WHERE u.role=%s ORDER BY u.full_name
                """, (role_filter,))
            else:
                cur.execute("""
                    SELECT u.*, d.name AS dept_name, p.name AS program_name
                    FROM users u
                    LEFT JOIN departments d ON d.id=u.dept_id
                    LEFT JOIN programs    p ON p.id=u.program_id
                    ORDER BY u.role, u.full_name
                """)
            users = cur.fetchall()
    finally:
        conn.close()
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
@role_required('admin')
def create_user():
    d = request.get_json()
    if not all(d.get(k) for k in ['full_name','email','password','role']):
        return jsonify({'error': 'full_name, email, password, role are required.'}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (full_name, email, password_hash, role, sr_code, dept_id, program_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (d['full_name'], d['email'].lower(), generate_password_hash(d['password']),
                  d['role'], d.get('sr_code'), d.get('dept_id'), d.get('program_id')))
            conn.commit()
            cur.execute("SELECT * FROM users WHERE id=%s", (cur.lastrowid,))
            u = cur.fetchone()
    except pymysql.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Email already exists.'}), 409
    finally:
        conn.close()
    return jsonify(u), 201

@app.route('/api/users/<int:uid>', methods=['PUT'])
@role_required('admin')
def update_user(uid):
    d = request.get_json()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if list(d.keys()) == ['status']:
                cur.execute("UPDATE users SET status=%s WHERE id=%s", (d['status'], uid))
            elif d.get('password'):
                cur.execute("""UPDATE users SET full_name=%s, email=%s, role=%s, sr_code=%s,
                               dept_id=%s, program_id=%s, status=%s, password_hash=%s WHERE id=%s""",
                            (d['full_name'], d['email'].lower(), d['role'], d.get('sr_code'),
                             d.get('dept_id'), d.get('program_id'), d.get('status','active'),
                             generate_password_hash(d['password']), uid))
            else:
                cur.execute("""UPDATE users SET full_name=%s, email=%s, role=%s, sr_code=%s,
                               dept_id=%s, program_id=%s, status=%s WHERE id=%s""",
                            (d.get('full_name',''), d.get('email','').lower(), d.get('role','student'),
                             d.get('sr_code'), d.get('dept_id'), d.get('program_id'),
                             d.get('status','active'), uid))
            conn.commit()
            cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
            u = cur.fetchone()
    finally:
        conn.close()
    return jsonify(u)

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@role_required('admin')
def delete_user(uid):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET status='inactive' WHERE id=%s", (uid,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'message': 'User deactivated.'})

# ─────────────────────────────────────────
# DEPARTMENTS & PROGRAMS
# ─────────────────────────────────────────
@app.route('/api/departments', methods=['GET'])
def get_departments():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM departments ORDER BY code")
            depts = cur.fetchall()
    finally:
        conn.close()
    return jsonify(depts)

@app.route('/api/departments', methods=['POST'])
@role_required('admin')
def create_department():
    d = request.get_json()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO departments (code,name) VALUES (%s,%s)",
                        (d['code'].upper(), d['name']))
            conn.commit()
            cur.execute("SELECT * FROM departments WHERE id=%s", (cur.lastrowid,))
            dept = cur.fetchone()
    except pymysql.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Department code already exists.'}), 409
    finally:
        conn.close()
    return jsonify(dept), 201

@app.route('/api/departments/<int:did>', methods=['DELETE'])
@role_required('admin')
def delete_department(did):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM departments WHERE id=%s", (did,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'message': 'Department deleted.'})

@app.route('/api/programs', methods=['GET'])
def get_programs():
    dept_id = request.args.get('dept_id')
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if dept_id:
                cur.execute("""
                    SELECT p.*, d.name AS dept_name FROM programs p
                    JOIN departments d ON d.id=p.dept_id
                    WHERE p.dept_id=%s ORDER BY p.code
                """, (dept_id,))
            else:
                cur.execute("""
                    SELECT p.*, d.name AS dept_name FROM programs p
                    JOIN departments d ON d.id=p.dept_id ORDER BY p.code
                """)
            progs = cur.fetchall()
    finally:
        conn.close()
    return jsonify(progs)

@app.route('/api/programs', methods=['POST'])
@role_required('admin')
def create_program():
    d = request.get_json()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO programs (dept_id,code,name,required_hours) VALUES (%s,%s,%s,%s)",
                (d['dept_id'], d['code'].upper(), d['name'], d.get('required_hours',486))
            )
            conn.commit()
            cur.execute("SELECT * FROM programs WHERE id=%s", (cur.lastrowid,))
            prog = cur.fetchone()
    except pymysql.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Program code already exists.'}), 409
    finally:
        conn.close()
    return jsonify(prog), 201

@app.route('/api/programs/<int:pid>', methods=['DELETE'])
@role_required('admin')
def delete_program(pid):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM programs WHERE id=%s", (pid,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'message': 'Program deleted.'})

# ─────────────────────────────────────────
# APPLICATIONS
# ─────────────────────────────────────────
@app.route('/api/applications', methods=['GET'])
@login_required
def get_applications():
    conn = get_db()
    role = session['role']
    uid  = session['user_id']
    try:
        with conn.cursor() as cur:
            if role == 'student':
                cur.execute("""
                    SELECT a.*, o.name AS office_name, o.category,
                           u.full_name AS facilitator_name
                    FROM applications a
                    JOIN offices o ON o.id=a.office_id
                    LEFT JOIN users u ON u.id=a.facilitator_id
                    WHERE a.student_id=%s ORDER BY a.applied_at DESC
                """, (uid,))
            elif role == 'facilitator':
                cur.execute("""
                    SELECT a.*, o.name AS office_name,
                           s.full_name AS student_name, s.sr_code,
                           d.name AS dept_name
                    FROM applications a
                    JOIN offices o ON o.id=a.office_id
                    JOIN users s ON s.id=a.student_id
                    LEFT JOIN departments d ON d.id=s.dept_id
                    WHERE a.facilitator_id=%s OR a.status='pending'
                    ORDER BY a.applied_at DESC
                """, (uid,))
            else:
                cur.execute("""
                    SELECT a.*, o.name AS office_name,
                           s.full_name AS student_name, s.sr_code,
                           f.full_name AS facilitator_name,
                           d.name AS dept_name
                    FROM applications a
                    JOIN offices o ON o.id=a.office_id
                    JOIN users s ON s.id=a.student_id
                    LEFT JOIN users f ON f.id=a.facilitator_id
                    LEFT JOIN departments d ON d.id=s.dept_id
                    ORDER BY a.applied_at DESC
                """)
            apps = cur.fetchall()
    finally:
        conn.close()
    return jsonify(apps)

@app.route('/api/applications', methods=['POST'])
@role_required('student')
def create_application():
    d         = request.get_json()
    office_id = d.get('office_id')
    if not office_id:
        return jsonify({'error': 'office_id is required.'}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM applications WHERE student_id=%s AND office_id=%s AND status NOT IN ('rejected')",
                (session['user_id'], office_id)
            )
            if cur.fetchone():
                return jsonify({'error': 'You have already applied to this office.'}), 409

            cur.execute("SELECT * FROM offices WHERE id=%s", (office_id,))
            office = cur.fetchone()
            if not office or office['slots'] <= 0:
                return jsonify({'error': 'No slots available for this office.'}), 400

            cur.execute(
                "INSERT INTO applications (student_id, office_id) VALUES (%s,%s)",
                (session['user_id'], office_id)
            )
            app_id = cur.lastrowid
            cur.execute("UPDATE offices SET slots=slots-1 WHERE id=%s", (office_id,))
            conn.commit()
            cur.execute("""
                SELECT a.*, o.name AS office_name FROM applications a
                JOIN offices o ON o.id=a.office_id WHERE a.id=%s
            """, (app_id,))
            result = cur.fetchone()
    finally:
        conn.close()
    return jsonify(result), 201

@app.route('/api/applications/<int:aid>', methods=['PUT'])
@role_required('facilitator', 'admin')
def update_application(aid):
    d              = request.get_json()
    new_status     = d.get('status')
    remarks        = d.get('remarks', '')
    facilitator_id = session['user_id'] if session['role'] == 'facilitator' else d.get('facilitator_id')

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""UPDATE applications SET status=%s, remarks=%s,
                           facilitator_id=%s, updated_at=NOW() WHERE id=%s""",
                        (new_status, remarks, facilitator_id, aid))
            conn.commit()
            cur.execute("""
                SELECT a.*, o.name AS office_name,
                       s.full_name AS student_name, s.sr_code
                FROM applications a
                JOIN offices o ON o.id=a.office_id
                JOIN users s ON s.id=a.student_id
                WHERE a.id=%s
            """, (aid,))
            result = cur.fetchone()
    finally:
        conn.close()
    return jsonify(result)

# ─────────────────────────────────────────
# DOCUMENTS
# ─────────────────────────────────────────
@app.route('/api/documents', methods=['GET'])
@login_required
def get_documents():
    conn = get_db()
    uid  = session['user_id']
    role = session['role']
    try:
        with conn.cursor() as cur:
            if role == 'student':
                cur.execute(
                    "SELECT * FROM documents WHERE student_id=%s ORDER BY uploaded_at DESC", (uid,)
                )
            else:
                cur.execute("""
                    SELECT d.*, u.full_name AS student_name, u.sr_code
                    FROM documents d JOIN users u ON u.id=d.student_id
                    ORDER BY d.uploaded_at DESC
                """)
            docs = cur.fetchall()
    finally:
        conn.close()
    return jsonify(docs)

@app.route('/api/documents', methods=['POST'])
@role_required('student')
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided.'}), 400
    file     = request.files['file']
    doc_type = request.form.get('doc_type', 'General')
    app_id   = request.form.get('application_id')

    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: pdf, doc, docx, jpg, jpeg, png'}), 400

    original = secure_filename(file.filename)
    ts       = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    saved    = f"{session['user_id']}_{ts}_{original}"
    path     = os.path.join(UPLOAD_DIR, saved)
    file.save(path)
    size = os.path.getsize(path)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents
                    (student_id, application_id, doc_type, filename, original_name, file_size)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (session['user_id'], app_id, doc_type, saved, original, size))
            conn.commit()
            cur.execute("SELECT * FROM documents WHERE id=%s", (cur.lastrowid,))
            doc = cur.fetchone()
    finally:
        conn.close()
    return jsonify(doc), 201

@app.route('/api/documents/<int:did>', methods=['PUT'])
@role_required('facilitator', 'admin')
def update_document_status(did):
    d    = request.get_json()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE documents SET status=%s WHERE id=%s",
                        (d.get('status','pending'), did))
            conn.commit()
            cur.execute("SELECT * FROM documents WHERE id=%s", (did,))
            doc = cur.fetchone()
    finally:
        conn.close()
    return jsonify(doc)

# ─────────────────────────────────────────
# EVALUATIONS
# ─────────────────────────────────────────
@app.route('/api/evaluations', methods=['GET'])
@login_required
def get_evaluations():
    conn = get_db()
    uid  = session['user_id']
    role = session['role']
    try:
        with conn.cursor() as cur:
            if role == 'student':
                cur.execute("""
                    SELECT e.*, u.full_name AS evaluator_name
                    FROM evaluations e
                    JOIN applications a ON a.id=e.application_id
                    JOIN users u ON u.id=e.evaluator_id
                    WHERE a.student_id=%s
                """, (uid,))
            else:
                cur.execute("""
                    SELECT e.*, s.full_name AS student_name, s.sr_code,
                           ev.full_name AS evaluator_name, o.name AS office_name
                    FROM evaluations e
                    JOIN applications a ON a.id=e.application_id
                    JOIN users s ON s.id=a.student_id
                    JOIN users ev ON ev.id=e.evaluator_id
                    JOIN offices o ON o.id=a.office_id
                    ORDER BY e.evaluated_at DESC
                """)
            evals = cur.fetchall()
    finally:
        conn.close()
    return jsonify(evals)

@app.route('/api/evaluations', methods=['POST'])
@role_required('facilitator', 'admin')
def create_evaluation():
    d     = request.get_json()
    score = round((d.get('attendance',0) + d.get('performance',0) +
                   d.get('attitude',0)   + d.get('skills',0)) / 4, 2)
    conn  = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO evaluations
                    (application_id, evaluator_id, score, attendance,
                     performance, attitude, skills, comments)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (d['application_id'], session['user_id'], score,
                  d.get('attendance',0), d.get('performance',0),
                  d.get('attitude',0), d.get('skills',0), d.get('comments','')))
            conn.commit()
            cur.execute("SELECT * FROM evaluations WHERE id=%s", (cur.lastrowid,))
            ev = cur.fetchone()
    finally:
        conn.close()
    return jsonify(ev), 201

# ─────────────────────────────────────────
# OJT HOURS
# ─────────────────────────────────────────
@app.route('/api/hours', methods=['GET'])
@login_required
def get_hours():
    app_id = request.args.get('application_id')
    conn   = get_db()
    try:
        with conn.cursor() as cur:
            if app_id:
                cur.execute(
                    "SELECT * FROM ojt_hours WHERE application_id=%s ORDER BY date DESC", (app_id,)
                )
                hours = cur.fetchall()
                cur.execute(
                    "SELECT SUM(hours_rendered) AS total FROM ojt_hours WHERE application_id=%s", (app_id,)
                )
                total = cur.fetchone()['total'] or 0
            else:
                cur.execute("SELECT * FROM ojt_hours ORDER BY date DESC")
                hours = cur.fetchall()
                total = 0
    finally:
        conn.close()
    return jsonify({'hours': hours, 'total': total})

@app.route('/api/hours', methods=['POST'])
@role_required('student')
def log_hours():
    d    = request.get_json()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # FIX 3: logged_at now always written (was missing from original INSERT)
            cur.execute("""
                INSERT INTO ojt_hours
                    (application_id, date, hours_rendered, time_in, time_out, remarks, logged_at)
                VALUES (%s,%s,%s,%s,%s,%s,NOW())
            """, (d['application_id'], d['date'], d.get('hours_rendered',8),
                  d.get('time_in'), d.get('time_out'), d.get('remarks','')))
            conn.commit()
            cur.execute("SELECT * FROM ojt_hours WHERE id=%s", (cur.lastrowid,))
            h = cur.fetchone()
    finally:
        conn.close()
    return jsonify(h), 201

# ─────────────────────────────────────────
# STATS
# ─────────────────────────────────────────
@app.route('/api/stats', methods=['GET'])
@role_required('admin', 'facilitator')
def get_stats():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            def cnt(q):
                cur.execute(q)
                return list(cur.fetchone().values())[0]

            stats = {
                'total_students':     cnt("SELECT COUNT(*) FROM users WHERE role='student' AND status='active'"),
                'total_facilitators': cnt("SELECT COUNT(*) FROM users WHERE role='facilitator' AND status='active'"),
                'total_offices':      cnt("SELECT COUNT(*) FROM offices WHERE is_active=1"),
                'pending_apps':       cnt("SELECT COUNT(*) FROM applications WHERE status='pending'"),
                'approved_apps':      cnt("SELECT COUNT(*) FROM applications WHERE status='approved'"),
                'ongoing_apps':       cnt("SELECT COUNT(*) FROM applications WHERE status='ongoing'"),
                'completed_apps':     cnt("SELECT COUNT(*) FROM applications WHERE status='completed'"),
                'total_docs':         cnt("SELECT COUNT(*) FROM documents"),
                'docs_pending':       cnt("SELECT COUNT(*) FROM documents WHERE status='pending'"),
            }
    finally:
        conn.close()
    return jsonify(stats)

@app.route('/api/my/stats', methods=['GET'])
@role_required('student')
def my_stats():
    uid  = session['user_id']
    conn = get_db()
    try:
        with conn.cursor() as cur:
            def cnt(q, p=()):
                cur.execute(q, p)
                return list(cur.fetchone().values())[0] or 0

            stats = {
                'total_applications': cnt("SELECT COUNT(*) FROM applications WHERE student_id=%s", (uid,)),
                'pending':            cnt("SELECT COUNT(*) FROM applications WHERE student_id=%s AND status='pending'", (uid,)),
                'approved':           cnt("SELECT COUNT(*) FROM applications WHERE student_id=%s AND status='approved'", (uid,)),
                'docs_uploaded':      cnt("SELECT COUNT(*) FROM documents WHERE student_id=%s", (uid,)),
                'total_hours':        cnt("""
                    SELECT COALESCE(SUM(h.hours_rendered),0)
                    FROM ojt_hours h
                    JOIN applications a ON a.id=h.application_id
                    WHERE a.student_id=%s""", (uid,)),
            }
    finally:
        conn.close()
    return jsonify(stats)

# ─────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────
@app.route('/api/attendance', methods=['GET'])
@login_required
def get_attendance():
    conn       = get_db()
    role       = session['role']
    uid        = session['user_id']
    app_id     = request.args.get('application_id')
    student_id = request.args.get('student_id')
    date       = request.args.get('date')
    month      = request.args.get('month')

    query = """
        SELECT att.*,
               u.full_name  AS student_name,
               u.sr_code,
               lb.full_name AS logged_by_name,
               a.office_id,
               o.name       AS office_name
        FROM attendance att
        JOIN users u  ON u.id = att.student_id
        JOIN applications a ON a.id = att.application_id
        JOIN offices o ON o.id = a.office_id
        LEFT JOIN users lb ON lb.id = att.logged_by
        WHERE 1=1
    """
    params = []

    if role == 'student':
        query += " AND att.student_id = %s"
        params.append(uid)
    elif student_id:
        query += " AND att.student_id = %s"
        params.append(student_id)

    if app_id:
        query += " AND att.application_id = %s"
        params.append(app_id)
    if date:
        query += " AND att.date = %s"
        params.append(date)
    if month:
        # FIX: MySQL uses DATE_FORMAT, not LIKE — safe parameterized approach
        query += " AND DATE_FORMAT(att.date, '%%Y-%%m') = %s"
        params.append(month)

    query += " ORDER BY att.date DESC, u.full_name"

    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

            summary = None
            if app_id:
                cur.execute("""
                    SELECT
                        COUNT(*)                                                        AS total_days,
                        SUM(CASE WHEN status='present'  THEN 1 ELSE 0 END)             AS present,
                        SUM(CASE WHEN status='absent'   THEN 1 ELSE 0 END)             AS absent,
                        SUM(CASE WHEN status='late'     THEN 1 ELSE 0 END)             AS late,
                        SUM(CASE WHEN status='half-day' THEN 1 ELSE 0 END)             AS half_day,
                        SUM(CASE WHEN status='excused'  THEN 1 ELSE 0 END)             AS excused,
                        SUM(hours_rendered)                                            AS total_hours
                    FROM attendance WHERE application_id=%s
                """, (app_id,))
                summary = cur.fetchone() or {}
    finally:
        conn.close()

    return jsonify({'records': rows, 'summary': summary})


@app.route('/api/attendance', methods=['POST'])
@role_required('facilitator', 'admin')
def log_attendance():
    data    = request.get_json()
    records = data if isinstance(data, list) else [data]
    conn    = get_db()
    inserted = []
    import datetime as dt

    try:
        with conn.cursor() as cur:
            for rec in records:
                app_id     = rec.get('application_id')
                student_id = rec.get('student_id')
                date       = rec.get('date')
                status     = rec.get('status', 'present')
                time_in    = rec.get('time_in')
                time_out   = rec.get('time_out')
                remarks    = rec.get('remarks', '')

                if not all([app_id, student_id, date]):
                    continue

                hours = rec.get('hours_rendered', 0)
                if time_in and time_out and not hours:
                    try:
                        ti    = dt.datetime.strptime(time_in,  '%H:%M')
                        to    = dt.datetime.strptime(time_out, '%H:%M')
                        hours = max(0, round((to - ti).total_seconds() / 3600, 2))
                    except Exception:
                        hours = 0

                if status == 'half-day':
                    hours = min(hours, 4)
                elif status == 'absent':
                    hours = 0

                cur.execute(
                    "SELECT id FROM attendance WHERE application_id=%s AND student_id=%s AND date=%s",
                    (app_id, student_id, date)
                )
                existing = cur.fetchone()
                now_str  = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if existing:
                    cur.execute("""
                        UPDATE attendance SET status=%s, time_in=%s, time_out=%s,
                            hours_rendered=%s, remarks=%s, logged_by=%s, created_at=%s
                        WHERE id=%s
                    """, (status, time_in, time_out, hours, remarks,
                          session['user_id'], now_str, existing['id']))
                    inserted.append(existing['id'])
                else:
                    cur.execute("""
                        INSERT INTO attendance
                            (application_id, student_id, date, status, time_in, time_out,
                             hours_rendered, remarks, logged_by, created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (app_id, student_id, date, status, time_in, time_out,
                          hours, remarks, session['user_id'], now_str))
                    inserted.append(cur.lastrowid)

        conn.commit()
        results = []
        with conn.cursor() as cur:
            for rid in inserted:
                cur.execute("SELECT * FROM attendance WHERE id=%s", (rid,))
                r = cur.fetchone()
                if r:
                    results.append(r)
    finally:
        conn.close()

    return jsonify(results), 201


@app.route('/api/attendance/<int:att_id>', methods=['PUT'])
@role_required('facilitator', 'admin')
def update_attendance(att_id):
    d        = request.get_json()
    import datetime as dt
    time_in  = d.get('time_in')
    time_out = d.get('time_out')
    status   = d.get('status', 'present')
    hours    = d.get('hours_rendered', 0)

    if time_in and time_out and not hours:
        try:
            ti    = dt.datetime.strptime(time_in,  '%H:%M')
            to    = dt.datetime.strptime(time_out, '%H:%M')
            hours = max(0, round((to - ti).total_seconds() / 3600, 2))
        except Exception:
            hours = 0
    if status == 'absent':
        hours = 0

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE attendance SET status=%s, time_in=%s, time_out=%s,
                    hours_rendered=%s, remarks=%s, logged_by=%s
                WHERE id=%s
            """, (status, time_in, time_out, hours,
                  d.get('remarks',''), session['user_id'], att_id))
            conn.commit()
            cur.execute("SELECT * FROM attendance WHERE id=%s", (att_id,))
            r = cur.fetchone()
    finally:
        conn.close()
    return jsonify(r)


@app.route('/api/attendance/<int:att_id>', methods=['DELETE'])
@role_required('facilitator', 'admin')
def delete_attendance(att_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM attendance WHERE id=%s", (att_id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'message': 'Attendance record deleted.'})


@app.route('/api/attendance/summary', methods=['GET'])
@role_required('facilitator', 'admin')
def attendance_summary():
    """
    FIX 2: original used .format() to inject `month` directly into SQL — SQL injection risk.
    Now uses a parameterized query with a conditional JOIN filter.
    """
    month = request.args.get('month', '')
    conn  = get_db()
    try:
        with conn.cursor() as cur:
            if month:
                cur.execute("""
                    SELECT
                        u.id             AS student_id,
                        u.full_name      AS student_name,
                        u.sr_code,
                        d.name           AS dept_name,
                        o.name           AS office_name,
                        a.id             AS application_id,
                        a.status         AS app_status,
                        COUNT(att.id)                                               AS total_days,
                        SUM(CASE WHEN att.status='present'  THEN 1 ELSE 0 END)     AS present,
                        SUM(CASE WHEN att.status='absent'   THEN 1 ELSE 0 END)     AS absent,
                        SUM(CASE WHEN att.status='late'     THEN 1 ELSE 0 END)     AS late,
                        SUM(CASE WHEN att.status='half-day' THEN 1 ELSE 0 END)     AS half_day,
                        SUM(CASE WHEN att.status='excused'  THEN 1 ELSE 0 END)     AS excused,
                        COALESCE(SUM(att.hours_rendered), 0)                       AS total_hours
                    FROM applications a
                    JOIN users u   ON u.id  = a.student_id
                    JOIN offices o ON o.id  = a.office_id
                    LEFT JOIN departments d ON d.id = u.dept_id
                    LEFT JOIN attendance att
                        ON att.application_id = a.id
                        AND DATE_FORMAT(att.date, '%%Y-%%m') = %s
                    WHERE a.status IN ('approved','ongoing','completed')
                    GROUP BY a.id, u.id
                    ORDER BY u.full_name
                """, (month,))
            else:
                cur.execute("""
                    SELECT
                        u.id             AS student_id,
                        u.full_name      AS student_name,
                        u.sr_code,
                        d.name           AS dept_name,
                        o.name           AS office_name,
                        a.id             AS application_id,
                        a.status         AS app_status,
                        COUNT(att.id)                                               AS total_days,
                        SUM(CASE WHEN att.status='present'  THEN 1 ELSE 0 END)     AS present,
                        SUM(CASE WHEN att.status='absent'   THEN 1 ELSE 0 END)     AS absent,
                        SUM(CASE WHEN att.status='late'     THEN 1 ELSE 0 END)     AS late,
                        SUM(CASE WHEN att.status='half-day' THEN 1 ELSE 0 END)     AS half_day,
                        SUM(CASE WHEN att.status='excused'  THEN 1 ELSE 0 END)     AS excused,
                        COALESCE(SUM(att.hours_rendered), 0)                       AS total_hours
                    FROM applications a
                    JOIN users u   ON u.id  = a.student_id
                    JOIN offices o ON o.id  = a.office_id
                    LEFT JOIN departments d ON d.id = u.dept_id
                    LEFT JOIN attendance att ON att.application_id = a.id
                    WHERE a.status IN ('approved','ongoing','completed')
                    GROUP BY a.id, u.id
                    ORDER BY u.full_name
                """)
            rows = cur.fetchall()
    finally:
        conn.close()
    return jsonify(rows)


# ─────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    uid  = session['user_id']
    role = session['role']
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if role == 'student':
                cur.execute("""
                    SELECT 'application' AS type, a.status AS detail,
                           o.name AS subject, a.updated_at AS ts
                    FROM applications a JOIN offices o ON o.id=a.office_id
                    WHERE a.student_id=%s AND a.status != 'pending'
                    UNION ALL
                    SELECT 'document', d.status, d.doc_type, d.uploaded_at
                    FROM documents d WHERE d.student_id=%s AND d.status != 'pending'
                    ORDER BY ts DESC LIMIT 10
                """, (uid, uid))
            else:
                cur.execute("""
                    SELECT 'application' AS type, a.status AS detail,
                           u.full_name AS subject, a.applied_at AS ts
                    FROM applications a JOIN users u ON u.id=a.student_id
                    WHERE a.status='pending'
                    ORDER BY ts DESC LIMIT 10
                """)
            rows = cur.fetchall()
    finally:
        conn.close()
    return jsonify(rows)


# ─────────────────────────────────────────
# STUDENT DETAIL  (facilitator/admin)
# ─────────────────────────────────────────
@app.route('/api/students/<int:uid>', methods=['GET'])
@role_required('facilitator', 'admin')
def get_student_detail(uid):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.*, d.name AS dept_name, p.name AS program_name
                FROM users u
                LEFT JOIN departments d ON d.id=u.dept_id
                LEFT JOIN programs    p ON p.id=u.program_id
                WHERE u.id=%s AND u.role='student'
            """, (uid,))
            user = cur.fetchone()
            if not user:
                return jsonify({'error': 'Student not found'}), 404

            cur.execute("""
                SELECT a.*, o.name AS office_name FROM applications a
                JOIN offices o ON o.id=a.office_id
                WHERE a.student_id=%s ORDER BY a.applied_at DESC
            """, (uid,))
            apps = cur.fetchall()

            cur.execute(
                "SELECT * FROM documents WHERE student_id=%s ORDER BY uploaded_at DESC", (uid,)
            )
            docs = cur.fetchall()

            cur.execute("""
                SELECT COALESCE(SUM(h.hours_rendered),0) AS total
                FROM ojt_hours h
                JOIN applications a ON a.id=h.application_id
                WHERE a.student_id=%s
            """, (uid,))
            hours = cur.fetchone()['total']

            cur.execute("""
                SELECT COUNT(*) AS days,
                       SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) AS present,
                       SUM(CASE WHEN status='absent'  THEN 1 ELSE 0 END) AS absent,
                       SUM(CASE WHEN status='late'    THEN 1 ELSE 0 END) AS late,
                       COALESCE(SUM(hours_rendered),0) AS total_hours
                FROM attendance WHERE student_id=%s
            """, (uid,))
            att_summary = cur.fetchone()
    finally:
        conn.close()

    return jsonify({
        'user':         user,
        'applications': apps,
        'documents':    docs,
        'hours':        hours,
        'attendance':   att_summary or {},
    })


# ─────────────────────────────────────────
# RUN — must be at the very bottom, after ALL routes are defined.
# FIX 1: In the original file, app.run() was placed in the middle of
# the file. Flask registers routes as decorators are evaluated, so every
# @app.route below app.run() was silently skipped. Moving it here ensures
# every route (/api/auth/profile, /api/notifications, /api/students/<id>)
# is properly registered before the server starts.
# ─────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("  BSU OJT System — Flask + MySQL Backend")
    print("  http://localhost:5000")
    print("="*50)
    print("\n  Default Accounts:")
    print("  Admin:       admin@batstate-u.edu.ph      / admin123")
    print("  Facilitator: mjsantos@batstate-u.edu.ph   / facilitator123")
    print("  Student:     24-36106@g.batstate-u.edu.ph / student123\n")
    app.run(debug=True, port=5000)