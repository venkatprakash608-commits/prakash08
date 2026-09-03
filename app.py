from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import os

app = Flask(__name__)
CORS(app)

database_url = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
db = SQLAlchemy(app)

def utcnow():
    return datetime.now(timezone.utc)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(50), default='pending')
    is_archived = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'is_archived': self.is_archived
        }

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer)
    task_title = db.Column(db.String(200))
    action = db.Column(db.String(50))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=utcnow)

def log_activity(task_id, task_title, action, details):
    try:
        log = ActivityLog(
            task_id=task_id,
            task_title=task_title,
            action=action,
            details=details,
            timestamp=utcnow()
        )
        db.session.add(log)
    except Exception:
        pass

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    title = data.get('title', 'Untitled')
    status = data.get('status', 'pending')
    task = Task(title=title, status=status)
    db.session.add(task)
    db.session.commit()
    task_id = task.id
    task_title = task.title

    log_activity(task_id, task_title, "CREATE", f"Status: {status}")

    return jsonify(task.to_dict()), 201

# Root route - serves the SPA
@app.route('/')
def index():
    return "<h1>TaskFlow Live!</h1><p>App running! <a href='/api/tasks'>View API</a></p>"

# API: List Tasks
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    query = Task.query

    # Archival status
    include_archived = request.args.get('archived', 'false').lower() == 'true'
    if not include_archived:
        query = query.filter(Task.is_archived == False)

    # Status filter
    status = request.args.get('status')
    if status and status.lower() != 'all':
        query = query.filter(Task.status == status)

    tasks = query.all()
    return jsonify([t.to_dict() for t in tasks])

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
