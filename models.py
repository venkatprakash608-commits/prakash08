from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(30), default='todo')  # todo, in_progress, review, done
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    category = db.Column(db.String(50), default='General')
    due_date = db.Column(db.String(30), nullable=True)  # YYYY-MM-DD
    subtasks = db.Column(db.JSON, default=list)  # list of dicts: [{"id": int, "title": str, "completed": bool}]
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def to_dict(self):
        subs = self.subtasks or []
        total_subtasks = len(subs)
        completed_subtasks = sum(1 for s in subs if s.get('completed'))
        progress = int((completed_subtasks / total_subtasks * 100)) if total_subtasks > 0 else (100 if self.status == 'done' else 0)

        # Check if overdue
        is_overdue = False
        if self.due_date and self.status != 'done':
            try:
                due = datetime.strptime(self.due_date, '%Y-%m-%d').date()
                if due < utc_now().date():
                    is_overdue = True
            except ValueError:
                pass

        return {
            'id': self.id,
            'title': self.title,
            'description': self.description or '',
            'status': self.status,
            'priority': self.priority,
            'category': self.category or 'General',
            'due_date': self.due_date,
            'is_overdue': is_overdue,
            'subtasks': subs,
            'subtasks_total': total_subtasks,
            'subtasks_completed': completed_subtasks,
            'progress_percent': progress,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, nullable=True)
    task_title = db.Column(db.String(200), default='')
    action = db.Column(db.String(50), nullable=False)  # created, updated, status_change, deleted
    details = db.Column(db.Text, default='')
    timestamp = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'task_title': self.task_title,
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
        }
