# BatStateU-TNEU Lipa SITES
### Student Internship Tracking and Evaluation System
**Batangas State University — TNEU | Lipa Campus**

---

## 📋 Project Description

**Lipa SITES** is a web-based OJT (On-the-Job Training) management platform built for Batangas State University Lipa Campus. It digitizes the entire student internship lifecycle — replacing manual paper-based processes with an efficient, real-time digital system accessible to **Students**, **Facilitators**, and **Administrators**.

---

## 🚀 Features

### 👨‍🎓 Student
- Register and log in with SR Code
- Browse available OJT offices and check slot availability
- Submit OJT applications and track status in real time
- Upload all 6 required OJT documents with per-document approval tracking
- View attendance logs and OJT hours rendered vs. 486-hour requirement
- View evaluation scores and facilitator comments

### 👨‍🏫 Facilitator
- Review and approve or reject student applications
- Approve or reject uploaded documents per student
- Log daily attendance (Present / Absent / Late / Half-Day) with time-in and time-out
- Submit student evaluations with scores for Attendance, Performance, Attitude, and Skills
- Send status notifications to students
- View all assigned students, OJT hours, and attendance summaries

### 🛡️ Admin
- Full user management — create, edit, activate, deactivate accounts
- Manage OJT office listings (add, update, remove, control slots)
- Oversee all applications, documents, and attendance records system-wide
- View system-wide statistics and reports on the admin dashboard

---

## 🛠️ Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3 · Flask Framework          |
| Database    | MySQL · PyMySQL Driver              |
| Frontend    | HTML5 · CSS3 · Vanilla JavaScript   |
| Auth        | Flask Sessions · Werkzeug Hashing   |
| Security    | Role-Based Access Control (RBAC)    |
| Environment | python-dotenv (.env file)           |

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/mayciii/SITES.git
cd SITES/bsu_internship_system
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create your `.env` file
Create a `.env` file in the `bsu_internship_system` folder:
```
SECRET_KEY=bsu-ojt-secret-2024-lipa
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=bsu_ojt
```

### 4. Make sure MySQL is running
The system will automatically create all tables and seed default data on first run.

### 5. Run the server
```bash
python app.py
```

### 6. Open in browser
```
http://localhost:5000
```

---

## 🗄️ Database Design

The system uses **MySQL** with **8 relational tables** linked via foreign keys:

| Table           | Description                                              |
|-----------------|----------------------------------------------------------|
| `users`         | All user accounts (Student, Facilitator, Admin)          |
| `departments`   | BSU Lipa college departments                             |
| `programs`      | Academic programs per department                         |
| `offices`       | Available OJT offices with slot counts                   |
| `applications`  | Student OJT applications per office                      |
| `documents`     | Uploaded student OJT documents                           |
| `evaluations`   | Facilitator evaluations per student application          |
| `attendance`    | Daily attendance logs per student                        |

---

## 👤 Default Accounts

| Role        | Email                              | Password        |
|-------------|------------------------------------|-----------------| 
| Admin       | admin@batstate-u.edu.ph            | admin123        |
| Facilitator | mjsantos@batstate-u.edu.ph         | facilitator123  |
| Student     | 24-36106@g.batstate-u.edu.ph       | student123      |
| Student     | 24-10021@g.batstate-u.edu.ph       | student123      |

> ⚠️ Change these credentials before deploying to production.

---

## 🏢 OJT Partner Offices (13 BSU Lipa Offices)

1. Extension Service Office
2. Gender and Development Office
3. Office of Guidance and Counseling
4. Office of the Culture and Arts
5. Office of Sports and Development
6. On-The-Job Training Office
7. Registrar's Office
8. Research Office
9. Resource Generation Office
10. Sustainable Development Office
11. Testing and Admission Office
12. ICT Services
13. Office of Library Services

---

## 📁 Required OJT Documents

Students must upload all 6 of the following documents:

1. Medical Certificate
2. Parent's Consent
3. Waiver
4. Resume / CV
5. Endorsement Letter
6. Insurance Certificate

---

## 📂 Project Structure

```
bsu_internship_system/
├── app.py                  # Main Flask application & all API routes
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not committed to Git)
├── .gitignore              # Git ignore rules
├── static/
│   ├── css/
│   │   └── style.css       # Main stylesheet (BSU red & white theme)
│   ├── js/
│   │   └── api.js          # Frontend API helper functions
│   └── img/
│       └── bsu-lipa.jpg    # Campus hero image
├── templates/
│   ├── login.html              # Login page
│   ├── register.html           # Registration page
│   ├── dashboard.html          # Student dashboard
│   ├── apply.html              # Browse & apply for OJT offices
│   ├── status.html             # Application status tracker
│   ├── upload.html             # Document upload page
│   ├── my_attendance.html      # Student attendance view
│   ├── evaluation.html         # Student evaluation results
│   ├── profile.html            # Profile & settings
│   ├── facilitator_dashboard.html    # Facilitator dashboard
│   ├── facilitator_evaluation.html   # Submit student evaluations
│   ├── attendance.html               # Facilitator attendance tracker
│   └── admin_dashboard.html          # Admin control panel
└── uploads/                # Uploaded student documents (not committed to Git)
```

---

## 🔐 Security Notes

- Passwords are hashed using **Werkzeug's** `generate_password_hash`
- All database queries use **parameterized statements** (no SQL injection)
- Sensitive credentials are stored in `.env` and never committed to GitHub
- Session-based authentication with **role-based access control**
- `.gitignore` excludes `.env`, `uploads/`, `*.db`, and `__pycache__/`

---

## 📡 API Endpoints

| Method | Endpoint                  | Access              | Description                        |
|--------|---------------------------|---------------------|------------------------------------|
| POST   | `/api/auth/login`         | Public              | Login and create session            |
| POST   | `/api/auth/register`      | Public              | Register new account                |
| GET    | `/api/auth/me`            | Authenticated       | Get current user info               |
| GET    | `/api/offices`            | Public              | List all active OJT offices         |
| GET    | `/api/applications`       | Authenticated       | Get applications (role-filtered)    |
| POST   | `/api/applications`       | Student             | Submit new OJT application          |
| PUT    | `/api/applications/<id>`  | Facilitator / Admin | Approve or reject application       |
| POST   | `/api/documents`          | Student             | Upload OJT document                 |
| PUT    | `/api/documents/<id>`     | Facilitator / Admin | Update document status              |
| GET    | `/api/evaluations`        | Authenticated       | Get evaluations (role-filtered)     |
| POST   | `/api/evaluations`        | Facilitator / Admin | Submit student evaluation           |
| GET    | `/api/attendance`         | Authenticated       | Get attendance records              |
| POST   | `/api/attendance`         | Facilitator / Admin | Log attendance records              |
| GET    | `/api/my/stats`           | Student             | Get personal dashboard stats        |
| GET    | `/api/stats`              | Admin / Facilitator | Get system-wide statistics          |

---

## 📦 Dependencies

```
flask
pymysql
werkzeug
python-dotenv
```

Install all with:
```bash
pip install -r requirements.txt
```

---

## 🎓 About

**BatStateU-TNEU Lipa SITES** was developed as a semestral project for  
**IT 222 – Advanced Database Management System**  
College of Informatics and Computing Sciences  
Batangas State University — TNEU, Lipa Campus  
IT 222 – Advanced Database Management System

---

*Built with ❤️ for BSU Lipa Campus OJT Students*
