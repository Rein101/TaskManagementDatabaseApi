# import the relevant modules

from database import data_connect, database
from datetime import datetime
import sqlite3

class TaskManager:
    def __init__(self):
        data_connect()  # initialize the database
    
    def add_task_to_db(self, title, due_date, flag, description = None, priority='low', team_members=None):
        # we'll use the insert query
        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO all_tasks(title, due_date, status, flag, description) 
                           VALUES(?, ?, "Pending", ?, ?)""", (title, due_date, flag, description))
            conn.commit()
            task_id = cursor.lastrowid # get the id of the last inserted row and store it in the task_id variable for the flags

            # if the flag is personal, we want it to get into the personal_tasks table
            # if the flag is work, we want it to get into the work_tasks table
            if flag == 'personal':
                cursor.execute("""INSERT INTO personal_tasks(task_id, priority) 
                                VALUES(?, ?)""", (task_id, priority))
                
            elif flag == 'work' and team_members:
                for member in team_members:
                    cursor.execute("""INSERT INTO work_tasks(task_id, team_member) 
                                    VALUES(?, ?)""",(task_id, member))
            
            conn.commit()
            print(f"Row with id {task_id} was successfully added!")

    def list_tasks_from_db(self): # here we retrieve all the rows using fetchall
        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM all_tasks")
            rows = cursor.fetchall()
            return rows
        
    def load_task_by_id(self, task_id):
        # retrieve task by it's unique id
        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM all_tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            if row:
                return row
            else:
                return ("There is no such row in the table")
    
    def update_task_db(self, task_id, title = None, flag = None, due_date = None , status = None, description = None, priority = None, team_members = None):
         with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            # if each of these attributes is not None, let's update them to the value that's needed
            if title is not None:
                cursor.execute('UPDATE all_tasks SET title = ? WHERE id = ?', (title, task_id))
            if due_date is not None:
                cursor.execute('UPDATE all_tasks SET due_date = ? WHERE id = ?', (due_date, task_id))
            if status is not None:
                cursor.execute('UPDATE all_tasks SET status = ? WHERE id = ?', (status, task_id))
            if description is not None:
                cursor.execute('UPDATE all_tasks SET description = ? WHERE id = ?', (description, task_id))
            if priority is not None:
                cursor.execute('UPDATE personal_tasks SET priority = ? WHERE id = ?', (priority, task_id))
            if team_members is not None:
                for member in team_members:
                    cursor.execute('INSERT INTO work_tasks(task_id, team_members) VALUES(?,?,?)', (task_id, member))
            if flag is not None: 
                cursor.execute('UPDATE all_tasks SET flag = ? WHERE id = ?', (flag, task_id))  # update the flag
                cursor.execute('DELETE FROM personal_tasks WHERE task_id = ?', (task_id,)) # delete the row with the task_id assigned to unintended table
                cursor.execute('DELETE FROM work_tasks WHERE task_id = ?', (task_id,)) 
                if flag == 'personal' and priority is not None: # personal_tasks
                    cursor.execute('INSERT INTO personal_tasks (task_id, priority) VALUES (?, ?)', (task_id, priority))  # make sure it is inserted into the required table
                elif flag == 'work' and team_members is not None: # work_tasks
                    for member in team_members: 
                        cursor.execute('INSERT INTO work_tasks (task_id, team_member) VALUES (?, ?)', (task_id, member))# we need to also update the work_table incase
            
            conn.commit()
            print(f"Task {task_id} updated successfully!")
            # we are assured that the flag is set correctly now
            # end of update function

    def delete_task(self, task_id): 
        with sqlite3.connect(database) as conn: 
            cursor = conn.cursor() 
            cursor.execute('DELETE FROM all_tasks WHERE id = ?', (task_id,)) 
            cursor.execute('DELETE FROM personal_tasks WHERE task_id = ?', (task_id,)) 
            cursor.execute('DELETE FROM work_tasks WHERE task_id = ?', (task_id,)) 
            conn.commit() 
            print(f'Task {task_id} deleted successfully')

    def get_pending_tasks(self, due_date): 
        with sqlite3.connect(database) as conn: 
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM all_tasks WHERE status = "Pending"') 
            tasks = cursor.fetchall() 
            pending_tasks = [] 
            current_date = datetime.now().date()
            for task in tasks: 
                # first we convert to datetime from text using srtptime for datetime operations
                task_due_date = datetime.strptime(task[2], "%Y-%m-%d").date() # task[2] is the due_date entire column
                if task_due_date >= current_date: 
                    pending_tasks.append(task) 
            return pending_tasks
            
        
    def get_overdue_tasks(self): 
        with sqlite3.connect(database) as conn: 
            cursor = conn.cursor() 
            cursor.execute('SELECT * FROM all_tasks WHERE status = "Pending"') 
            tasks = cursor.fetchall() 
            overdue_tasks = []
            current_date = datetime.now().date()
            for task in tasks: 
                task_due_date = datetime.strptime(task[2], "%Y-%m-%d").date() 
                if task_due_date < current_date: 
                    overdue_tasks.append(task) 
            return overdue_tasks
        