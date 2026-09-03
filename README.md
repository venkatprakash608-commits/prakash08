# TaskFlow - Modern Task Management & Tracker

A full-featured, responsive task management web application for creating, updating, organizing, and tracking tasks with real-time feedback, interactive Kanban boards, list views, analytics, and checklist progress.

---

## 🌟 Key Features

- **Multi-View Task Management**:
  - 📋 **Kanban Board**: Drag-and-drop tasks seamlessly between *To Do*, *In Progress*, *In Review*, and *Done* columns.
  - 📑 **List / Table View**: Fast tabular overview with inline status selectors, quick completion checkboxes, category tags, and due dates.
  - 📊 **Analytics Dashboard**: Real-time completion rates, priority distribution meters, category breakdowns, and chronological activity timeline logs.
- **Task Tracking & Details**:
  - **Checklists & Subtasks**: Create subtasks within tasks, toggle completion states, and monitor real-time completion progress bars.
  - **Overdue Detection**: Automatic tracking and visual highlighting for overdue tasks.
  - **Activity History**: Automatic logging of creation, status changes, updates, and deletions for every task.
- **Search, Filter & Sort**:
  - Instant live keyword search by title, description, or category.
  - Filter by status, priority (*Urgent*, *High*, *Medium*, *Low*), or category.
  - Sort by due date (earliest/latest), priority, or creation date.
- **Modern User Experience**:
  - 🌙 **Dark & Light Mode**: Seamless theme toggle saved to browser `localStorage`.
  - 📱 **Fully Responsive**: Adapts across desktops, laptops, tablets, and mobile devices.
  - ⚡ **Snappy Feedback**: Floating toast notifications and interactive modals.
  - 🚀 **Zero-Setup Database**: Uses embedded SQLite with automatic schema migration and sample data seeding on initial run.

---

## 🏗️ Architecture & Tech Stack

- **Backend**: Python 3.14, Flask, Flask-SQLAlchemy, SQLite
- **Frontend**: HTML5, CSS3 (CSS Variables, Flexbox/Grid), Vanilla JavaScript (HTML5 Drag and Drop API)
- **Icons & Typography**: Plus Jakarta Sans, Font Awesome 6
- **Testing**: Python `unittest` suite covering all RESTful endpoints, filters, and models

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+ (Python 3.14 verified)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Running Automated Tests
Run the test suite to verify all REST endpoints and business logic:
```bash
python test_app.py
```

---

## 📁 Project Structure

```
├── app.py                  # Flask server, REST API endpoints, routing & sample seeding
├── models.py               # SQLAlchemy models (Task, ActivityLog)
├── test_app.py             # Comprehensive automated unit tests
├── requirements.txt        # Python package dependencies
├── templates/
│   └── index.html          # Responsive single-page application layout
├── static/
│   ├── css/
│   │   └── style.css       # Clean design system, light/dark themes, Kanban styling
│   └── js/
│       └── app.js          # Client-side state, Drag-and-Drop, modals, & API calls
└── README.md               # Documentation & usage guide
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/tasks` | Get all tasks (supports `status`, `priority`, `category`, `search`, `sort_by`) |
| `POST` | `/api/tasks` | Create a new task with optional subtasks |
| `GET` | `/api/tasks/<id>` | Get task details and activity log history |
| `PUT` | `/api/tasks/<id>` | Update task title, description, priority, category, subtasks |
| `PATCH` | `/api/tasks/<id>/status` | Quick update status (for Kanban drag & drop) |
| `PATCH` | `/api/tasks/<id>/subtasks/<subtask_id>/toggle` | Toggle subtask completion status |
| `DELETE` | `/api/tasks/<id>` | Permanently delete task |
| `GET` | `/api/stats` | Analytics summary: counts, completion rates, category stats |
| `GET` | `/api/categories` | List of all unique task categories |
