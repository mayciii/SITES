# BSU Internship Tracking System
**Batangas State University — Lipa Campus**
Student OJT Tracking & Evaluation System

---

## Tech Stack
- **Backend:** Python Flask 3.x
- **Database:** MySql (auto-created on first run)
- **Frontend:** HTML5, CSS3, Vanilla JS (no framework needed)

---

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the server
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## Default Accounts

| Role        | Email                              | Password        |
|-------------|------------------------------------|-----------------|
| Admin       | admin@batstate-u.edu.ph            | admin123        |
| Facilitator | mjsantos@batstate-u.edu.ph         | facilitator123  |
| Student     | 24-36106@g.batstate-u.edu.ph       | student123      |
| Student     | 24-10021@g.batstate-u.edu.ph       | student123      |

---

## Partner Offices (13 BSU Lipa Offices)

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

## API Endpoints

### Auth
| Method | Endpoint         | Description       |
|--------|-----------------|-------------------|
| POST   | /api/auth/login  | Login             |
| POST   | /api/auth/logout | Logout            |
| GET    | /api/auth/me     | Get current user  |

### Offices
| Method | Endpoint           | Role         |
|--------|--------------------|--------------|
| GET    | /api/offices       | All          |
| POST   | /api/offices       | Admin        |
| PUT    | /api/offices/:id   | Admin        |
| DELETE | /api/offices/:id   | Admin        |

### Users
| Method | Endpoint          | Role              |
|--------|-------------------|-------------------|
| GET    | /api/users        | Admin, Facilitator|
| POST   | /api/users        | Admin             |
| PUT    | /api/users/:id    | Admin             |
| DELETE | /api/users/:id    | Admin             |

### Applications
| Method | Endpoint               | Role                    |
|--------|------------------------|-------------------------|
| GET    | /api/applications      | All (filtered by role)  |
| POST   | /api/applications      | Student                 |
| PUT    | /api/applications/:id  | Facilitator, Admin      |

### Documents
| Method | Endpoint            | Role               |
|--------|---------------------|--------------------|
| GET    | /api/documents      | All (filtered)     |
| POST   | /api/documents      | Student (upload)   |
| PUT    | /api/documents/:id  | Facilitator, Admin |

### Departments & Programs
| Method | Endpoint              | Role  |
|--------|-----------------------|-------|
| GET    | /api/departments      | All   |
| POST   | /api/departments      | Admin |
| DELETE | /api/departments/:id  | Admin |
| GET    | /api/programs         | All   |
| POST   | /api/programs         | Admin |
| DELETE | /api/programs/:id     | Admin |

### Stats
| Method | Endpoint      | Role               |
|--------|---------------|--------------------|
| GET    | /api/stats    | Admin, Facilitator |
| GET    | /api/my/stats | Student            |

---

## File Structure
```
bsu-ojt-backend/
├── app.py               ← Flask application + all routes
├── bsu_ojt.db           ← SQLite database (auto-created)
├── requirements.txt
├── uploads/             ← Uploaded student documents
└── static/
    ├── css/
    │   └── style.css
    ├── js/
    │   └── api.js       ← API client + shared utilities
    ├── index.html
    ├── login.html
    ├── dashboard.html
    ├── apply.html
    ├── status.html
    ├── upload.html
    ├── profile.html
    ├── admin_dashboard.html
    └── facilitator_dashboard.html
```
