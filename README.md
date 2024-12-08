# Task Management System

## Overview
The Task Management System is a web-based database. It is not interactive but does import data in rows through HTTP curl or Postman. It is built on a design in which an individual adds data into the general (junction table) and the system automatically registers the task based on its flag (`_personal or _work`). In total, the database has 3 tables:
   - `all_tasks`
   - `personal_tasks`
   - `work_tasks`

Using a database has its advantages over a `CSV` spreadsheet, the most being its independence from the creator's memory and prevention of coercion and data insecurity.
     

### Key Features
- Create Tasks
- List tasks (all or based on the task_id provided)
- Monitor pending and overdue tasks
- Updating tasks by element
- Deleting tasks by task_id in the respective tables if required
- Automatic saving of data into the personal_tasks and work_tasks based on the flag, while preserving the original task_id for reference

## Setup Instructions

### Prerequisites
- Python 3.13.0
- Visual Studio, any Web Browser, DataGrip 2024.4.3 and Postman Agent
- Visual Environment
   - Create a Visual environment 
   - Activate it for use in the program
   - `python 3.13.0('venv':venv).\venv\Scripts\python.exe`
- SQLite module (installed as sqlite3)
- FLask module (installed as flask)
- DateTime module (included in Python standard library)

### Installation
1. Clone or download the repository containing the following files:
   - `Task.py`
   - `Task_manager.py`
   - `database.py`
   - `app.py`

### Flow Chart, Schema, and Design Pattern
   The task involved updating the task.py and task_manager.py into a database-oriented program, integrating SQLite functions like connect() e.t.c

   ## Workflow of the entire system
   - The flowing is a workflow diagram of the thought process to accomplish the goal
   ```bash
   source_code/
   │
   │   ├── Task.py # to handle the foundation of the table by setting all attributes as known for further integration
   │   ├── database.py # to create 3 tables using sqlite3 function
   │   ├── Task_manager.py # to perform data management by integrating database.py and more sqlite3 functions
   │   ├── app.py # to integrate an API flask into the whole system
   │
   │ README.md # to document the workings of the system
      └── venv
   ```
   ## Schema used in the database
   The following table includes all attributes used across all the tables: all_tasks, personal_tasks, and work_tasks.
   - `database.py`

   |Column        |Data Type              |Description                                                                    |
   |--------------|-----------------------|-------------------------------------------------------------------------------|
   |id            |INTEGER PRIMARY KEY    |This is an autoincrementing value that joins the tables                        |
   |title         |TEXT NOT NULL          |This is the title of the task                                                  |
   |due_date      |TEXT NOT NULL          |This is the due date for performing the task named above                       |
   |flag          |TEXT NOT NULL          |This is either personal or work to link the related task to the intended table |
   |status        |TEXT DEFAULT "Pending" |This is either set to "Pending" or "Completed"                                 |
   |description   |TEXT                   |This is a short description (ideally no more than 15 characters) of the task.   |
   |priority      |TEXT DEFAULT 'low'     |Exists in the personal_tasks. Checks task is a priority 'high', 'medium' or 'low' |
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
``` cd
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
`http://127.0.0.1:5000`: This is the link that leads to the web page where the output is contained. To print the result, append the URL paths stated above
## System Architecture

### 1. The SQL table was formed using DataGrip 2024.4.3 or Postman
Since the tables were successfully created, it is necessary to look at them and test the work behind them. 
The tables created display the following tables:
- **all_tasks table**: contains id, title, due_date, status, flag and a description
![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/56b0e2517ee1faa44921cb85d1927891e073416a/images/all_tasks_created.png)

- **personal_tasks table**: only contains two columns. The unique task_id and priority of the task
![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/56b0e2517ee1faa44921cb85d1927891e073416a/images/personal_tasks_created.png)

- **work_tasks table**: only contains two columns. The unique task_id and the team_members added
![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/56b0e2517ee1faa44921cb85d1927891e073416a/images/work_tasks_created.png)

As shown all tables are created, waiting for data to be uploaded.
#### Database Functions
1. **To Create a task and load it into the database**
   - First, set Postman to the following settings:
      - ***Headers***: set `Content_type` to `application/json`
      - ***Body***: set to `raw`
      - ***Method***: POST
      - ***URL path***: `http://127.0.0.1:5000/tasks`       
   - Secondly, to upload data, paste this in the body. the data is input with dictionaries as follows:
        ```bash
        {
       "title": "Test Task",
       "due_date": "2024-12-31",
       "flag": "personal",
       "description": "This is a test task",
       "priority": "high"
         }
        ```

   The outcome should be as follows in Postman Web.
      ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/1e6f4aede3a4841768d4c6cb3b422fc187edf168/images/task_created.png)

   To check if the tables are updated, we open DataGrip and check. Keep in mind the data is of different flags so we expect the personal_tasks and work_tasts to automatically hold these data inputs. after creating new tasks, these are the output tables.
      ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/1e6f4aede3a4841768d4c6cb3b422fc187edf168/images/more_tasks_inputed.png)

   **For work_tasks**:
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/d9eb67eee35975cf51d78a835f1d222db7171f16/images/work_tasks_loaded2.png)

   Notice that the tast_id repeats itself. This is because the inputted two lists and the system allocated each element to it's row while preserving the task+id as intended. the following was the input.
   **Work Task1**
   ```bash
   {
    "title": "Project Meeting",
    "due_date": "2024-12-14",
    "flag": "work",
    "description": "Meeting to discuss the Q4 project deliverables",
    "team_members": ["Alice", "Bob"]
   }
   ```

   **Work Task2**
   ```bash
   {
    "title": "Code Review",
    "due_date": "2024-12-18",
    "flag": "work",
    "description": "Review the new feature implementation",
    "team_members": ["Charlie", "Dave"]
   }
   ```

   **For Personal_tasks**:
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/d9eb67eee35975cf51d78a835f1d222db7171f16/images/personal_tasks_loaded.png)

   Tasks are created successfully!

2. **List rows from the database**
   We call the GET method in Postman, and a list of all our entries will be listed in the Postman interface. alternatively, we can settle for the table displayed in the DataGrip interface to show an ordered table of rows.
     ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/262e2d2761901a814c8ecf07e79762c4b0a0d295/images/syntax_all_tasks_listing.png)

   
3. **Retrieve a row from the database**
    To retrieve a row of data, we use the GET method and  use the URL path `/tasks/<int:task_id>`. The task_id is relevant because it is the reference of our extraction. using task_id = 4 will output a list of the row with task_id of 4. The int: just shows that the task is an integer. It is shown as follows.
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/932bc34ecce5618af07a539c2a6d81306978cb84/images/get_task_4_1.png)
   Even though the input was a json object, the output will always be a list. This operation can only be done one by one.
   
4. **To Update Elements in the database**
   To update an element in any row of any table, we use the method PUT and the URL path `/tasks/<int:task_id>`. Just like in retrieving the row, Updating an element requires the task_id to access the row we need to update.
7. **Delete rows of dates from the database**

8. **Get Pending and Overdue Tasks from the database**

   
   
   
  
