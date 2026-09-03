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
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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

@app.route('/')
def home():
    return jsonify({"message": "TaskFlow API is Live!"})

@app.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([t.to_dict() for t in tasks])

@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.json
    task = Task(
        title=data.get('title'),
        description=data.get('description',''),
        status=data.get('status','pending')
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201

@app.route('/tasks/<int:id>', methods=['PUT', 'DELETE'])
def update_delete_task(id):
    task = Task.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(task)
        db.session.commit()
        return jsonify({"message":"Deleted"})
    data = request.json
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.status = data.get('status', task.status)
    db.session.commit()
    return jsonify(task.to_dict())

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()
