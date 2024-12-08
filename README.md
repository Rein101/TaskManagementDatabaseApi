# Task Management System

## Overview
The Task Management System is a web-based database. It is not interactive, but does import data in rows through HTTP cUrl or Postman. It is build on a design that an individual adds data into the general (junction table) and the system automatic registers the task based on it's flag (`_personal or _work`). In total the database has 3 tables:
   - `all_tasks`
   - `personal_tasks`
   - `work_tasks`
Using a database has it's advantage over a csv spreadsheet, the most being it's independence from the creator's memory and prevention from coercion and data insecurity.
     

### Key Features
- Create Tasks
- List tasks (all or based on the id provided)
- Monitor pending and overdue tasks
- Updating tasks by element
- Deleting tasks by task_id in the respective tables if required
- Automatic saving of data into the personal_tasks and work_tasks based on flag, while preserving the original task_id for reference

## Setup Instructions

### Prerequisites
- Python 3.13.0
- Visual Studio, any Web Browser, DataGrip 2024.4.3 and Postman
- Visual Environment
   - Create a Visual environment 
   - Activate it for use in the program
   - `python 3.13.0('venv':venv).\venv\Scripts\python.exe`
- SQLite module (installed as sqlite3)
- FLask module (installed as flask)
- datetime module (included in Python standard library)

### Installation
1. Clone or download the repository containing the following files:
   - `Task.py`
   - `Task_manager.py`
   - `database.py`
   - `app.py`

### Flow Chart, Schema and Design Pattern
   The task involved updating the task.py and task_manager.py into a database oriented program, integrating SQLite function like connect() e.t.c

   ## Work FLow of the entire system
   - The flowing is a work flow diagram of the thought process to accomplish the goal
   ```bash
   source_code/
   │
   │   ├── Task.py # to handle the foundation of the table by setting all attributes as known for further intergration
   │   ├── database.py # to create 3 tables using sqlite3 function
   │   ├── Task_manager.py # to perform data management by intergaring database.py and more sqlite3 functions
   │   ├── app.py # to integrate an API flask into the whole system
   │
   │ README.md # to document the workings of the system
      └── venv
   ```
   ## Schema used in the database
   The following is a table that includes all attributes used across all the tables: all_tasks, personal_tasks and work_tasks.
   - `database.py`

   |Column        |Data Type              |Description                                                                    |
   |--------------|-----------------------|-------------------------------------------------------------------------------|
   |id            |INTEGER PRIMARY KEY    |This is an autoincrementing value that joins the tables                        |
   |title         |TEXT NOT NULL          |This is the title of the task                                                  |
   |due_date      |TEXT NOT NULL          |This is the due date for performing the task named above                       |
   |flag          |TEXT NOT NULL          |This is either personal or work to link the related task to the intended table |
   |status        |TEXT DEFAULT "Pending" |This is either set to "Pending" or "Completed"                                 |
   |description   |TEXT                   |This is a short descrition (ideally no more that 15 characters) of the task.   |
   |priority      |TEXT DEFAULT 'low'     |Exists in the personal_tasks. Checks task is priority 'high','medium' or 'low' |
   |team_members  |TEXT                   |This is only relevant in the work_tasks table to allocate members of each task |


   ## Flask methods and their route (URL path) for each task performed in `app.py`

   |Action        |method        |URL path               |Description                                         |
   |--------------|--------------|-----------------------|----------------------------------------------------|
   |create_tasks  |POST          |`/tasks`               |creates a task and automatic assigns a unique id    |
   |list_tasks    |GET           |`/tasks`               |Lists all the tasks in the all_tasks table          |
   |get_task      |GET           |`/tasks/<int:task_id>` |Retrieves a row of data based on the task_id        |
   |update_task   |PUT           |`/tasks/<int:task_id>` |Updates an item in a column based on the task_id    |
   |delete_task   |DELETE        |`/tasks/<int:task_id>` |delete a row of data based on the task_id           |
   |get_pending...|GET           |`/tasks/`              |Lists all pending rows based on due_date and status |
   |get_overdue...|GET           |`/tasks/`              |Lists all overdue rows based on due_date and status |

### Running the Program
```bash
python app.py
```
- result
```cd
Tables are Successfully Created!
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
 * Restarting with stat
Tables are Successfully Created!
 * Debugger is active!
 * Debugger PIN: 514-261-056
 ```
`http://127.0.0.1:5000` : This is the link that leads to the web page where the output is contained. to print the result, append the URL paths stated above
## System Architecture

### 1. The SQL table formed using DataGrip 2024.4.3 or Postman
Since the tables were successfully created, there is a need to look at the tables, and test the working behind it.
the tables created display the following tables:
- all_tasks table
![image][images/all_tasks_created.png]

- personal_tasks table
![image](images\personal_tasks_created.png)

- work_tasks table
![image](images\work_tasks_created.png)


#### Main Menu Functions
1. **Create Task** (`create_task`)
   - Prompts for task type (personal/work)
   - Collects task details (title, due date, description)
   - For personal tasks: Sets priority level at either high,medium or low
   - For work tasks: Assigns team members
   ```python
   # Example usage
   
   task = create_task(task_manager)
   ```

2. **View Tasks** (`view_tasks`)
   - Displays all tasks in the system
   - Shows task details including Task ID, description, due date, and status

3. **Filter Tasks** (`get_tasks`)
   - Filters tasks by type (personal/work)
   - Displays filtered task list with details

4. **Delete Task** (`delete_task`)
   - Removes task by ID
   - Provides confirmation of deletion

5. **Save/Load Tasks** (`save_tasks_to_csv`/`load_tasks_from_csv`)
   - Persists tasks to CSV file
   - Loads tasks from existing CSV file. If there are no tasks, an error is printed

6. **View Pending/Overdue Tasks** (`view_pending_and_overdue_tasks`)
   - Shows tasks categorized by status
   - Identifies overdue tasks based on current date

### 2. Task Module (`task.py`)
Defines the base Task class and its subclasses:

#### Classes
- **Task**: Base class with common task properties
- **PersonalTask**: Extends Task with priority settings
- **WorkTask**: Extends Task with team member management

### 3. Task Manager Module (`task_manager.py`)
Handles task operations and storage:

#### Key Methods
- `add_task`: Adds new tasks to the system
- `get_tasks`: Retrieves filtered task lists
- `delete_task`: Removes tasks by ID
- `save_task`/`load_task`: Handles CSV file operations
- `get_pending_tasks`/`get_overdue_tasks`: Creates lists of filtered objects based on whether they are pending or overdue respectively, from `datatime.now().date()`

## Error Handling

The system implements error handling throughout:

1. **Input Validation**
   - Task type validation (personal/work)
   - Date format validation (YYYY-MM-DD)
   - Priority level validation (high/medium/low)

2. **File Operations**
   ```python
   # error handling in the task_manager.py
   try:
       with open(filename, 'r', newline='\n') as file:
           # File operations
   
   except FileNotFoundError:
       print(f"Error: The file '{filename}' does not exist.")
   except (ValueError, IndexError):
       print("Error: Invalid data format in the CSV file.")
    except Exception as e:
            print(f"An unexpected error occurred: {e}")
   
   ```

3. **Data Validation**
   - Task ID verification before deletion
   - Team member format validation
   - Description length validation (max 15 characters)

## Usage Examples

### Creating a Personal Task
```python
Enter your choice (1-8): 1
Enter task type (personal/work): personal
Enter task title: Buy groceries
Enter due date (YYYY-MM-DD): 2024-11-20
Enter task description: Weekly shopping
Enter priority (high/medium/low): high
```

### Creating a Work Task
```python
Enter your choice (1-8): 1
Enter task type (personal/work): work
Enter task title: Project meeting
Enter due date (YYYY-MM-DD): 2024-11-15
Enter task description: Team sync
Enter team members (comma-separated): John, Alice, Bob
```

### Viewing Filtered Tasks
```python
Enter your choice (1-8): 2
Enter task type to filter by (personal/work): personal
Task ID: 1, Task: Buy groceries, Due Date: 20-11-2024, Status: Pending, Priority: high
```

#### Managing Tasks
```python
# Viewing All Tasks
Enter task type (personal/work/all): all
Task ID: 1, Task: Dentist Appointment, Due Date: 20-11-2024, Status: Pending, Priority: high
Task ID: 2, Task: Client Presentation, Due Date: 15-11-2024, Status: Pending, Team: John, Alice, Bob, Sarah

# Filtering Personal Tasks
Enter task type to filter by (personal/work): personal
Task ID: 1, Task: Dentist Appointment, Due Date: 20-11-2024, Status: Pending, Priority: high

# Filtering Work Tasks
Enter task type to filter by (personal/work): work
Task ID: 2, Task: Client Presentation, Due Date: 15-11-2024, Status: Pending, Team: John, Alice, Bob, Sarah
```

### 2. Task Priority Management

#### High Priority Personal Tasks
```python
Enter task type (personal/work): personal
Enter task title: Tax Return
Enter due date (YYYY-MM-DD): 2024-12-31
Enter task description: File taxes
Enter priority (high/medium/low): high

# Later viewing high priority tasks
Task ID: 3, Task: Tax Return, Due Date: 31-12-2024, Status: Pending, Priority: high
```

#### Team Task Management
```python
Enter your choice (1-8): 1
# Creating a team project task
Enter task type (personal/work): work
Enter task title: Sprint Planning
Enter due date (YYYY-MM-DD): 2024-11-18
Enter task description: Q4 Goals
Enter team members (comma-separated): Dev Team, Product Owner, Scrum Master

# Creating a subtask
Enter task type (personal/work): work
Enter task title: User Stories
Enter due date (YYYY-MM-DD): 2024-11-16
Enter task description: Story points
Enter team members (comma-separated): Dev Team
```

### 3. Task Status and Timeline Management

#### Checking Pending Tasks
```python
# View Pending Tasks
Enter your choice (1-8): 6
Pending Tasks:
Task ID: 1, Task: Dentist Appointment, Due Date: 20-11-2024, Status: Pending, Priority: high
Task ID: 2, Task: Client Presentation, Due Date: 15-11-2024, Status: Pending, Team: John, Alice, Bob, Sarah
```

#### Checking Overdue Tasks
```python
# View Overdue Tasks
Enter your choice (1-8): 7
Overdue Tasks:
Task ID: 4, Task: Weekly Report, Due Date: 13-11-2024, Status: Pending, Team: Manager, Analyst
```

### 4. File Operations

#### Saving Tasks to CSV
```python
# Save current tasks
Enter your choice (1-8): 4
Tasks saved to task_list.csv.

# CSV Format Example:
Task_ID,Description,Due Date,Type,Priority
1,Dentist Appointment,2024-11-20,personal,high
2,Client Presentation,2024-11-15,work,"John, Alice, Bob, Sarah"
```

#### Loading Tasks from CSV
```python
# Load tasks from file
Enter your choice (1-8): 5
Tasks loaded from task_list.csv.
```

### 5. Error Handling Examples

#### Invalid Date Format
```python
Enter task type (personal/work): personal
Enter task title: Gym Session
Enter due date (YYYY-MM-DD): 20-11-2024
Error: Invalid date format. Please use YYYY-MM-DD format.
```

#### Invalid Priority Level
```python
Enter task type (personal/work): personal
Enter task title: Reading
Enter due date (YYYY-MM-DD): 2024-11-20
Enter priority (high/medium/low): urgent
Error: Not a Valid Priority!
```

#### Invalid Task ID for Deletion
```python
Enter task ID to delete: 999
No task found with ID 999.
```

## Best Practices

1. **Regular Saving**
   - Save tasks regularly using the save option
   - Load from CSV when restarting the application

2. **Task Organization**
   - Use clear descriptions
   - Set appropriate priorities for personal tasks
   - Include all relevant team members for work tasks
     
3. **Grammatical errors in Priority and Task Type**
    -Write the commands correctly for optimum output

## Troubleshooting

Common issues and solutions:

1. **File Not Found Error**
   - Ensure CSV file exists in the correct directory
   - Check file permissions

2. **Invalid Date Format**
   - Use YYYY-MM-DD format
   - Ensure dates are valid

3. **Task Not Found**
   - Verify task ID exists
   - Refresh task list if recently modified



[def]: images\all_tasks_created.png
