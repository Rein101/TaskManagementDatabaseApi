from flask import Flask, request, jsonify
from Task_manager import TaskManager

app = Flask(__name__)
task_manager = TaskManager()

@app.route('/tasks', methods = ['POST']) # to create we use post method
def create_task():
    data = request.get_json()
    title = data['title']
    due_date = data['due_date']
    flag = data['flag']
    description = data.get('description')
    priority = data.get('priority','low')
    team_members = data.get('team_members', [])
    task_manager.add_task_to_db(title, due_date, flag, description, priority, team_members)
    return jsonify({'message': 'Task created successfully'}), 201

@app.route('/tasks', methods=['GET'])
def list_tasks():
    tasks = task_manager.list_tasks_from_db()
    return jsonify(tasks), 200

@app.route('/tasks/<int:task_id>', methods = ['GET'])
def get_task(task_id):
    task = task_manager.load_task_by_id(task_id)
    return jsonify(task), 200

@app.route('/tasks/<int:task_id>', methods = ['PUT'])
def update_task(task_id):
    data = request.get_json()
    title = data.get('title')
    due_date = data.get('due_date')
    status = data.get('status')
    flag = data.get('flag')
    description = data.get('description')
    priority = data.get('priority')
    team_members = data.get('team_members')
    task_manager.update_task_db(task_id, title, due_date, flag, status, description, priority, team_members)
    return jsonify({'message': 'Task created successfully'}), 200

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task_manager.delete_task(task_id)
    return jsonify({'message':'Task deleted successfully!'}), 200

@app.route('/tasks/pending', methods = ['GET'])
def get_pending_tasks():
    tasks = task_manager.get_pending_tasks()
    return jsonify(tasks), 200

@app.route('/tasks/overdue', methods = ['GET'])
def get_overdue_tasks():
    tasks = task_manager.get_overdue_tasks()
    return jsonify(tasks), 200

if __name__ == "__main__": # initialize
    app.run(debug=True)

