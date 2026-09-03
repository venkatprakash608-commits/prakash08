import os
from datetime import datetime, date, timedelta, timezone
from flask import Flask, render_template, request, jsonify
from models import db, Task, ActivityLog

def create_app(test_config=None):
    app = Flask(__name__)
    
    # Configuration
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tasks.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_initial_data()

    # --- Web Routes ---
    @app.route('/')
    def index():
        return render_template('index.html')

    # --- API Routes ---
    @app.route('/api/tasks', methods=['GET'])
    def get_tasks():
        query = Task.query

        # Filters
        status = request.args.get('status')
        if status and status != 'all':
            query = query.filter_by(status=status)

        priority = request.args.get('priority')
        if priority and priority != 'all':
            query = query.filter_by(priority=priority)

        category = request.args.get('category')
        if category and category != 'all':
            query = query.filter_by(category=category)

        search = request.args.get('search')
        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                (Task.title.ilike(search_term)) | 
                (Task.description.ilike(search_term)) |
                (Task.category.ilike(search_term))
            )

        # Sorting
        sort_by = request.args.get('sort_by', 'created_desc')
        if sort_by == 'due_date_asc':
            query = query.order_by(Task.due_date.asc().nulls_last(), Task.id.desc())
        elif sort_by == 'due_date_desc':
            query = query.order_by(Task.due_date.desc().nulls_last(), Task.id.desc())
        elif sort_by == 'title_asc':
            query = query.order_by(Task.title.asc())
        elif sort_by == 'priority_desc':
            # urgent > high > medium > low
            priority_order = db.case(
                {
                    'urgent': 4,
                    'high': 3,
                    'medium': 2,
                    'low': 1
                },
                value=Task.priority,
                else_=0
            ).desc()
            query = query.order_by(priority_order, Task.id.desc())
        else: # created_desc
            query = query.order_by(Task.created_at.desc(), Task.id.desc())

        tasks = query.all()
        return jsonify({'tasks': [t.to_dict() for t in tasks]})

    @app.route('/api/tasks', methods=['POST'])
    def create_task():
        data = request.get_json() or {}
        title = data.get('title', '').strip()
        if not title:
            return jsonify({'error': 'Task title is required'}), 400

        subtasks = data.get('subtasks', [])
        # Ensure subtasks have id and status
        clean_subtasks = []
        for i, s in enumerate(subtasks, start=1):
            if isinstance(s, dict) and s.get('title'):
                clean_subtasks.append({
                    'id': s.get('id', i),
                    'title': s['title'].strip(),
                    'completed': bool(s.get('completed', False))
                })

        new_task = Task(
            title=title,
            description=data.get('description', '').strip(),
            status=data.get('status', 'todo'),
            priority=data.get('priority', 'medium'),
            category=data.get('category', 'General').strip() or 'General',
            due_date=data.get('due_date') or None,
            subtasks=clean_subtasks
        )
        db.session.add(new_task)
        db.session.commit()

        # Log activity
        log = ActivityLog(
            task_id=new_task.id,
            task_title=new_task.title,
            action='created',
            details=f"Created with status '{new_task.status}' and priority '{new_task.priority}'."
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({'task': new_task.to_dict(), 'message': 'Task created successfully'}), 201

    @app.route('/api/tasks/<int:task_id>', methods=['GET'])
    def get_task(task_id):
        task = db.get_or_404(Task, task_id)
        logs = ActivityLog.query.filter_by(task_id=task_id).order_by(ActivityLog.timestamp.desc()).all()
        return jsonify({
            'task': task.to_dict(),
            'activities': [l.to_dict() for l in logs]
        })

    @app.route('/api/tasks/<int:task_id>', methods=['PUT'])
    def update_task(task_id):
        task = db.get_or_404(Task, task_id)
        data = request.get_json() or {}

        title = data.get('title', '').strip()
        if not title:
            return jsonify({'error': 'Task title cannot be empty'}), 400

        old_status = task.status
        old_priority = task.priority

        task.title = title
        task.description = data.get('description', '').strip()
        task.status = data.get('status', task.status)
        task.priority = data.get('priority', task.priority)
        task.category = data.get('category', task.category).strip() or 'General'
        task.due_date = data.get('due_date') or None
        
        if 'subtasks' in data:
            clean_subtasks = []
            for i, s in enumerate(data['subtasks'], start=1):
                if isinstance(s, dict) and s.get('title'):
                    clean_subtasks.append({
                        'id': s.get('id', i),
                        'title': s['title'].strip(),
                        'completed': bool(s.get('completed', False))
                    })
            task.subtasks = clean_subtasks

        task.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        # Log change
        changes = []
        if old_status != task.status:
            changes.append(f"status: {old_status} -> {task.status}")
        if old_priority != task.priority:
            changes.append(f"priority: {old_priority} -> {task.priority}")
        detail_msg = f"Updated task. " + (", ".join(changes) if changes else "Details modified.")

        log = ActivityLog(
            task_id=task.id,
            task_title=task.title,
            action='updated',
            details=detail_msg
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({'task': task.to_dict(), 'message': 'Task updated successfully'})

    @app.route('/api/tasks/<int:task_id>/status', methods=['PATCH'])
    def update_task_status(task_id):
        task = db.get_or_404(Task, task_id)
        data = request.get_json() or {}
        new_status = data.get('status')
        if not new_status or new_status not in ['todo', 'in_progress', 'review', 'done']:
            return jsonify({'error': 'Valid status (todo, in_progress, review, done) is required'}), 400

        old_status = task.status
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)

        # If moved to done, optional auto-completion of subtasks if requested
        if new_status == 'done' and data.get('complete_subtasks', False) and task.subtasks:
            updated_subtasks = []
            for s in task.subtasks:
                sub = dict(s)
                sub['completed'] = True
                updated_subtasks.append(sub)
            task.subtasks = updated_subtasks

        db.session.commit()

        log = ActivityLog(
            task_id=task.id,
            task_title=task.title,
            action='status_change',
            details=f"Status moved from '{old_status}' to '{new_status}'."
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({'task': task.to_dict(), 'message': f"Task status updated to '{new_status}'"})

    @app.route('/api/tasks/<int:task_id>/subtasks/<int:subtask_id>/toggle', methods=['PATCH'])
    def toggle_subtask(task_id, subtask_id):
        task = db.get_or_404(Task, task_id)
        subs = task.subtasks or []
        updated = False
        target_subtask = None

        new_subs = []
        for s in subs:
            sub = dict(s)
            if sub.get('id') == subtask_id:
                sub['completed'] = not sub.get('completed', False)
                updated = True
                target_subtask = sub
            new_subs.append(sub)

        if not updated:
            return jsonify({'error': 'Subtask not found'}), 404

        task.subtasks = new_subs
        task.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        status_text = 'completed' if target_subtask.get('completed') else 'reopened'
        log = ActivityLog(
            task_id=task.id,
            task_title=task.title,
            action='subtask_toggled',
            details=f"Subtask '{target_subtask.get('title')}' was {status_text}."
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({'task': task.to_dict(), 'message': f"Subtask marked as {status_text}"})

    @app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
    def delete_task(task_id):
        task = db.get_or_404(Task, task_id)
        title = task.title

        log = ActivityLog(
            task_id=None,
            task_title=title,
            action='deleted',
            details=f"Task #{task_id} '{title}' was deleted."
        )
        db.session.add(log)
        db.session.delete(task)
        db.session.commit()

        return jsonify({'message': f"Task '{title}' deleted successfully", 'id': task_id})

    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        tasks = Task.query.all()
        total = len(tasks)

        status_counts = {'todo': 0, 'in_progress': 0, 'review': 0, 'done': 0}
        priority_counts = {'low': 0, 'medium': 0, 'high': 0, 'urgent': 0}
        category_counts = {}
        overdue_count = 0
        today = date.today()

        for t in tasks:
            # Status
            if t.status in status_counts:
                status_counts[t.status] += 1
            # Priority
            if t.priority in priority_counts:
                priority_counts[t.priority] += 1
            # Category
            cat = t.category or 'General'
            category_counts[cat] = category_counts.get(cat, 0) + 1
            # Overdue
            if t.due_date and t.status != 'done':
                try:
                    d = datetime.strptime(t.due_date, '%Y-%m-%d').date()
                    if d < today:
                        overdue_count += 1
                except ValueError:
                    pass

        done_count = status_counts['done']
        completion_rate = int(round((done_count / total) * 100)) if total > 0 else 0

        # Recent activities (last 15)
        recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(15).all()

        return jsonify({
            'total_tasks': total,
            'status_counts': status_counts,
            'priority_counts': priority_counts,
            'category_counts': category_counts,
            'overdue_count': overdue_count,
            'completion_rate': completion_rate,
            'recent_activities': [l.to_dict() for l in recent_logs]
        })

    @app.route('/api/categories', methods=['GET'])
    def get_categories():
        categories = db.session.query(Task.category).distinct().all()
        cats = sorted(list({c[0] for c in categories if c[0]}))
        if 'General' not in cats:
            cats.insert(0, 'General')
        return jsonify({'categories': cats})

    return app


def seed_initial_data():
    if Task.query.first() is not None:
        return  # already seeded

    today = date.today()
    sample_tasks = [
        {
            'title': 'Design high-fidelity UI wireframes',
            'description': 'Create Figma wireframes and design system components for the user dashboard and task boards.',
            'status': 'done',
            'priority': 'high',
            'category': 'Design',
            'due_date': (today - timedelta(days=2)).strftime('%Y-%m-%d'),
            'subtasks': [
                {'id': 1, 'title': 'Draft component library (buttons, cards, badges)', 'completed': True},
                {'id': 2, 'title': 'Create Kanban drag layout mockup', 'completed': True},
                {'id': 3, 'title': 'Review with team for accessibility & contrast', 'completed': True},
            ]
        },
        {
            'title': 'Implement user authentication & session management',
            'description': 'Set up secure login, registration, password hashing, and token/cookie management.',
            'status': 'in_progress',
            'priority': 'urgent',
            'category': 'Development',
            'due_date': (today + timedelta(days=2)).strftime('%Y-%m-%d'),
            'subtasks': [
                {'id': 1, 'title': 'Database schema for users and roles', 'completed': True},
                {'id': 2, 'title': 'Implement bcrypt password hashing', 'completed': True},
                {'id': 3, 'title': 'JWT token generation & validation', 'completed': False},
                {'id': 4, 'title': 'Session expiration and refresh logic', 'completed': False},
            ]
        },
        {
            'title': 'Build interactive Kanban board with drag-and-drop',
            'description': 'Allow users to seamlessly drag task cards between To Do, In Progress, In Review, and Done columns.',
            'status': 'in_progress',
            'priority': 'high',
            'category': 'Development',
            'due_date': (today + timedelta(days=4)).strftime('%Y-%m-%d'),
            'subtasks': [
                {'id': 1, 'title': 'Set up HTML5 drag events & ghost card preview', 'completed': True},
                {'id': 2, 'title': 'Send asynchronous PATCH status updates', 'completed': False},
                {'id': 3, 'title': 'Add optimistic UI rollback on failure', 'completed': False},
            ]
        },
        {
            'title': 'Conduct weekly team roadmap review',
            'description': 'Review quarterly sprint milestones, unblock pending deliverables, and assign next week tasks.',
            'status': 'todo',
            'priority': 'medium',
            'category': 'Management',
            'due_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
            'subtasks': [
                {'id': 1, 'title': 'Prepare slide deck & burndown chart', 'completed': False},
                {'id': 2, 'title': 'Send calendar invitations & agenda', 'completed': True},
            ]
        },
        {
            'title': 'Audit server security and dependency vulnerabilities',
            'description': 'Run security scanning, audit requirements, and update outdated packages to patched releases.',
            'status': 'review',
            'priority': 'urgent',
            'category': 'DevOps',
            'due_date': (today - timedelta(days=1)).strftime('%Y-%m-%d'),  # intentionally overdue to demonstrate tracker
            'subtasks': [
                {'id': 1, 'title': 'Run pip audit and check CVE reports', 'completed': True},
                {'id': 2, 'title': 'Configure strict CSP headers', 'completed': True},
                {'id': 3, 'title': 'Verify SSL/TLS certificate renewal setup', 'completed': False},
            ]
        },
        {
            'title': 'Write comprehensive API integration documentation',
            'description': 'Document RESTful endpoints, request payloads, response models, and status codes in Swagger/OpenAPI format.',
            'status': 'todo',
            'priority': 'low',
            'category': 'Documentation',
            'due_date': (today + timedelta(days=7)).strftime('%Y-%m-%d'),
            'subtasks': [
                {'id': 1, 'title': 'Document Task CRUD endpoints', 'completed': False},
                {'id': 2, 'title': 'Document Analytics & stats calculation schema', 'completed': False},
            ]
        }
    ]

    for item in sample_tasks:
        task = Task(
            title=item['title'],
            description=item['description'],
            status=item['status'],
            priority=item['priority'],
            category=item['category'],
            due_date=item['due_date'],
            subtasks=item['subtasks']
        )
        db.session.add(task)
    db.session.commit()

    # Add initial activity log entries
    for t in Task.query.all():
        log = ActivityLog(
            task_id=t.id,
            task_title=t.title,
            action='created',
            details=f"Initial seeded task created with status '{t.status}'."
        )
        db.session.add(log)
    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    print("Task Manager Server running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000, host='127.0.0.1')
