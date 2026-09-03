import unittest
import json
from app import create_app
from models import db, Task, ActivityLog

class TaskFlowTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing with in-memory SQLite
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_index_route(self):
        """Test home page loads successfully"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'TaskFlow', response.data)

    def test_create_task_success(self):
        """Test creating a new task with subtasks"""
        payload = {
            'title': 'Build Login Page',
            'description': 'Create responsive login form with validation',
            'status': 'todo',
            'priority': 'high',
            'category': 'Development',
            'due_date': '2026-10-15',
            'subtasks': [
                {'id': 1, 'title': 'Design input fields', 'completed': False},
                {'id': 2, 'title': 'Add form validation', 'completed': False}
            ]
        }
        response = self.client.post(
            '/api/tasks',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('task', data)
        self.assertEqual(data['task']['title'], 'Build Login Page')
        self.assertEqual(data['task']['priority'], 'high')
        self.assertEqual(data['task']['subtasks_total'], 2)
        self.assertEqual(data['task']['progress_percent'], 0)

        # Check activity log was created
        with self.app.app_context():
            log = ActivityLog.query.filter_by(task_id=data['task']['id']).first()
            self.assertIsNotNone(log)
            self.assertEqual(log.action, 'created')

    def test_create_task_validation_failure(self):
        """Test task creation fails when title is missing or blank"""
        payload = {
            'title': '   ',
            'status': 'todo'
        }
        response = self.client.post(
            '/api/tasks',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)

    def test_get_tasks_and_filters(self):
        """Test fetching tasks with filters and search"""
        # Create 3 tasks
        tasks_data = [
            {'title': 'Write Documentation', 'status': 'todo', 'priority': 'low', 'category': 'Docs'},
            {'title': 'Fix Bug #102', 'status': 'in_progress', 'priority': 'urgent', 'category': 'Bugfix'},
            {'title': 'Deploy to Production', 'status': 'done', 'priority': 'high', 'category': 'DevOps'}
        ]
        for t in tasks_data:
            self.client.post('/api/tasks', data=json.dumps(t), content_type='application/json')

        # Get all tasks
        res = self.client.get('/api/tasks')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data['tasks']), 3)

        # Filter by status
        res_filtered = self.client.get('/api/tasks?status=in_progress')
        filtered_data = res_filtered.get_json()
        self.assertEqual(len(filtered_data['tasks']), 1)
        self.assertEqual(filtered_data['tasks'][0]['title'], 'Fix Bug #102')

        # Filter by priority
        res_priority = self.client.get('/api/tasks?priority=urgent')
        self.assertEqual(len(res_priority.get_json()['tasks']), 1)

        # Search by keyword
        res_search = self.client.get('/api/tasks?search=Documentation')
        self.assertEqual(len(res_search.get_json()['tasks']), 1)
        self.assertEqual(res_search.get_json()['tasks'][0]['title'], 'Write Documentation')

    def test_get_single_task_and_activities(self):
        """Test fetching a single task includes its activity logs"""
        create_res = self.client.post(
            '/api/tasks',
            data=json.dumps({'title': 'Review PR', 'status': 'todo', 'priority': 'medium'}),
            content_type='application/json'
        )
        task_id = create_res.get_json()['task']['id']

        res = self.client.get(f'/api/tasks/{task_id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['task']['id'], task_id)
        self.assertIn('activities', data)
        self.assertTrue(len(data['activities']) >= 1)

    def test_update_task(self):
        """Test updating a task's details"""
        create_res = self.client.post(
            '/api/tasks',
            data=json.dumps({'title': 'Initial Title', 'priority': 'low'}),
            content_type='application/json'
        )
        task_id = create_res.get_json()['task']['id']

        update_payload = {
            'title': 'Updated Title',
            'description': 'Updated description',
            'priority': 'urgent',
            'category': 'Work'
        }
        res = self.client.put(
            f'/api/tasks/{task_id}',
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['task']['title'], 'Updated Title')
        self.assertEqual(data['task']['priority'], 'urgent')
        self.assertEqual(data['task']['category'], 'Work')

    def test_patch_task_status(self):
        """Test quick status update (Kanban drag-drop endpoint)"""
        create_res = self.client.post(
            '/api/tasks',
            data=json.dumps({'title': 'Task to move', 'status': 'todo'}),
            content_type='application/json'
        )
        task_id = create_res.get_json()['task']['id']

        res = self.client.patch(
            f'/api/tasks/{task_id}/status',
            data=json.dumps({'status': 'in_progress'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['task']['status'], 'in_progress')

        # Invalid status check
        bad_res = self.client.patch(
            f'/api/tasks/{task_id}/status',
            data=json.dumps({'status': 'invalid_status'}),
            content_type='application/json'
        )
        self.assertEqual(bad_res.status_code, 400)

    def test_subtask_toggle(self):
        """Test toggling subtasks marks completed and updates progress"""
        create_res = self.client.post(
            '/api/tasks',
            data=json.dumps({
                'title': 'Task with Subtasks',
                'subtasks': [
                    {'id': 101, 'title': 'Step 1', 'completed': False},
                    {'id': 102, 'title': 'Step 2', 'completed': False}
                ]
            }),
            content_type='application/json'
        )
        task_id = create_res.get_json()['task']['id']

        # Toggle Step 1 to completed
        res = self.client.patch(f'/api/tasks/{task_id}/subtasks/101/toggle')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['task']['subtasks_completed'], 1)
        self.assertEqual(data['task']['progress_percent'], 50)

        # Toggle Step 2 to completed
        res2 = self.client.patch(f'/api/tasks/{task_id}/subtasks/102/toggle')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2['task']['subtasks_completed'], 2)
        self.assertEqual(data2['task']['progress_percent'], 100)

    def test_delete_task(self):
        """Test deleting a task"""
        create_res = self.client.post(
            '/api/tasks',
            data=json.dumps({'title': 'Task to be deleted'}),
            content_type='application/json'
        )
        task_id = create_res.get_json()['task']['id']

        res = self.client.delete(f'/api/tasks/{task_id}')
        self.assertEqual(res.status_code, 200)

        # Verify it no longer exists
        get_res = self.client.get(f'/api/tasks/{task_id}')
        self.assertEqual(get_res.status_code, 404)

    def test_stats_calculation(self):
        """Test stats endpoint returns correct counts and completion rate"""
        # Create 2 done, 1 in_progress, 1 todo
        tasks = [
            {'title': 'T1', 'status': 'done', 'priority': 'high', 'category': 'Work'},
            {'title': 'T2', 'status': 'done', 'priority': 'medium', 'category': 'Work'},
            {'title': 'T3', 'status': 'in_progress', 'priority': 'urgent', 'category': 'Personal'},
            {'title': 'T4', 'status': 'todo', 'priority': 'low', 'category': 'Dev'}
        ]
        for t in tasks:
            self.client.post('/api/tasks', data=json.dumps(t), content_type='application/json')

        res = self.client.get('/api/stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['total_tasks'], 4)
        self.assertEqual(data['status_counts']['done'], 2)
        self.assertEqual(data['status_counts']['in_progress'], 1)
        self.assertEqual(data['status_counts']['todo'], 1)
        self.assertEqual(data['completion_rate'], 50)
        self.assertEqual(data['category_counts']['Work'], 2)
        self.assertEqual(data['category_counts']['Personal'], 1)
        self.assertEqual(data['category_counts']['Dev'], 1)

if __name__ == '__main__':
    unittest.main()
