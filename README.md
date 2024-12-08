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

### Assumptions
- The operations were performed in 2024-12-08, hence `today = datetime.now().date() = "2024-12-08"`
- All the required images will be uploaded here with a permalink e.g. "https://github.com/Rein101/TaskManagementDatabaseApi/blob/92b62636e0ff7b9d1e18f0f27e17ff986d04dd36/images/delete_1_postman.png" in case the recipient will run the code from other software. To be able to see everything including the images, please run the `README.md` file on Git Hub.
- Since the `README.md` contains images, there is no need to download **DataGrip 2024.4.3 Software**. It is just meant to display the database and its tables and all operations done within each table.
- The recipient should receive all files, for smooth executions.


### Installation
1. Clone or download the repository containing the following files:
   - `images` **Folder**
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
   |get_pending...|GET           |`/tasks/pending`       |Lists all pending rows based on due_date and status |
   |get_overdue...|GET           |`/tasks/overdue`       |Lists all overdue rows based on due_date and status |




### Running the Program
```bash
python app.py
# Let's run the FLask document
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




## 1. Creating the tables: all_tasks, personal_tasks and work_tasks with `sqlite3` module

The tables were made in the `database.py` file, using the module `sqlite3` and its function. The following steps were implemented to achieve this result.
   1. Installing the `sqlite3` package
   2. Importing the module into python
   ``` bash
   python # First we import the sqlite3 module
   import sqlite3
   ```
   3. Create a variable `database` and assign it to the database name we want i.e. `Task.db`. The `db` stands for database.
   4. Create a `<Connection Object>` but using the ***sqlite3.connect(database)*** function. To assign this with a reasonable connection variable, we use `with...as`.

   5. Enclose step 4 within a function `data_connect()` to call as a module in the other files and initialize `try: ... except: ` to handle for OperationalErrors in the database. An example of an OperationalError is `unidentified column name`.
  ``` bash
   python
   database = "Task.db"
   def data_connect():
    try:
        with sqlite3.connect(database) as conn:
         ...

   except sqlite3.OperationalError as e:
        print("Table not created ", e)
   ```
   6.  Create a `<Cursor Object>` within the function. This is important because `Connection objects` do not perform applicable executions. The task is to create a table, so a Cursor object + `execute()` will do the job. `execute()` is a function of `cursor()`
   7.  Create a table. using the `cursor().execute()` function, we can now perform SQLite operations in Python. The first one is to create a table. We use the SQL function CREATE TABLE IF NOT EXISTS (*this ensures that the table is created if and only if the table doesn't already exist*). The table we are working on is named all_tasks and it will be the parent table or junction table for the whole database. It is called a Junction table because it links all the tables using a primary key `task_id`.
   ``` bash
   python
   database = "Task.db"
   def data_connect():
    try:
        with sqlite3.connect(database) as conn:
               cursor = conn.cursor()
               # Then using the cursor object, we can execute a table using execute() function and the SQL lexis CREATE TABLE
                        
               # First we create the general table with the attributes in the Task class
               cursor.execute("""CREATE TABLE IF NOT EXISTS all_tasks(
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           title TEXT NOT NULL,
                           due_date TEXT NOT NULL,
                           status TEXT DEFAULT "Pending" CHECK(status IN ('Pending', 'Completed')),
                           flag TEXT CHECK(flag IN ("personal", "work")),
                           description TEXT
                           )
                        """)
   ```
   8. All the heavy lifting is done. To create the other tables, we simply replicate the code above but only set to the column names that each table is required to have.
   ``` bash
   python
   ...
   cursor.execute(""" CREATE TABLE IF NOT EXISTS personal_tasks(
                        task_id INTEGER,
                        priority TEXT DEFAULT 'low' CHECK(priority IN ('high', 'medium', 'low')),
                        FOREIGN KEY (task_id) REFERENCES all_tasks(id)
                        )
            """)

   cursor.execute(""" CREATE TABLE IF NOT EXISTS work_tasks(
                        task_id INTEGER,
                        team_member TEXT,
                        FOREIGN KEY (task_id) REFERENCES all_tasks(id)
                        )
            """)
            # then we apply the changes using commit() on the connection object
   conn.commit()
   print("Tables are Successfully Created!")
   ...
   ```

Now the tables have been successfully created. It is necessary to look at them and test the work behind them. 
The tables created display the following tables:


- **all_tasks table**: contains id, title, due_date, status, flag and a description
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/56b0e2517ee1faa44921cb85d1927891e073416a/images/all_tasks_created.png)


- **personal_tasks table**: only contains two columns. The unique task_id and priority of the task
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/56b0e2517ee1faa44921cb85d1927891e073416a/images/personal_tasks_created.png)


- **work_tasks table**: only contains two columns. The unique task_id and the team_members added
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/56b0e2517ee1faa44921cb85d1927891e073416a/images/work_tasks_created.png)


As shown all tables are created, waiting for data to be uploaded.
## Database Functions

 - First, set `Postman Web` to the following settings:
   - ***Headers***: set `Content_type` to `application/json`
   - ***Body***: set to `raw`
   -  ***Method***: will be demonstrated below
   - ***URL path***: `http://127.0.0.1:5000/tasks` (the default path)

### 1. To Create a task and load it into the database

   - First, set Postman to the following settings:
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


   To check if the tables are updated, we open DataGrip and check. Keep in mind the data is of different flags so we expect the personal_tasks and work_tasts to automatically hold these data inputs. After creating new tasks, these are the output tables.


   **all_tasks**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/1e6f4aede3a4841768d4c6cb3b422fc187edf168/images/more_tasks_inputed.png)



   **work_tasks**:
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/d9eb67eee35975cf51d78a835f1d222db7171f16/images/work_tasks_loaded2.png)


   Notice that the tast_id repeats itself. This is because the inputted two lists and the system allocated each element to its row while preserving the task+id as intended. the following was the input.



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


   `201 CREATED`: Task created successfully!


### 2. List rows from the database

   We call the GET method in Postman, and a list of all our entries will be listed in the Postman interface. alternatively, we can settle for the table displayed in the DataGrip interface to show an ordered table of rows.

   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/262e2d2761901a814c8ecf07e79762c4b0a0d295/images/syntax_all_tasks_listing.png)


### 3. Retrieve a row from the database
   To retrieve a row of data, we use the GET method and  use the URL path `/tasks/<int:task_id>`. The task_id is relevant because it is the reference of our extraction. using task_id = 4 will output a list of the rows with task_id of 4. The int: just shows that the task is an integer. It is shown as follows.

   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/932bc34ecce5618af07a539c2a6d81306978cb84/images/get_task_4_1.png)


   Even though the input was a json object, the output will always be a list. This operation can only be done one by one.
   To test our error handling, I checked for task_id = 1 (I will explain why it is not in the data), and this was the output.


   ```bash
   python
   def load_task_by_id(self, task_id):
        # retrieve task by its unique task_id
        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM all_tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            if row:
                return row
            else:
                return ("There is no such row in the table")
   ```
   The output:

   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/91bfb9ed39f1284b51983cf18c2ead3a88bf886e/images/error_handling_unregistered_task.png)

   The output is as intended, since row == False i.e. the row does not exist.

   `200 OK`


### 4. To Update Elements in the database
   To update an element in any row of any table, we use the method PUT and the URL path `/tasks/<int:task_id>`. Just like in retrieving the row, Updating an element requires the task_id to access the row we need to update. We can update individual elements or entire rows, as long as the task_id is well set. To test this, we do the following:


   **In Postman Web**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/91bfb9ed39f1284b51983cf18c2ead3a88bf886e/images/update_4_postman.png)

   **The output in the all_tasks table**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/91bfb9ed39f1284b51983cf18c2ead3a88bf886e/images/update_4_table.png)

   As shown, the task updated is of row 4, and its values have been updated. To update entire rows, the following is done:

   **In Postman Web**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/3c7f29d850b2869f736597ecd037893dd9bae891/images/entire_row_update_postman.png)

   **The output in the all_tasks table for `task_id = 2`**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/3c7f29d850b2869f736597ecd037893dd9bae891/images/entire_row_update_alltasks.png)


   Since the update was a personal task, we should expect a change in the personal_tasks table as follows.


   **The output in the personal_tasks table `task_id = 2`**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/3c7f29d850b2869f736597ecd037893dd9bae891/images/entire_row_update_personal.png)

   `200 OK`: Task Created Successfully


### 5. Delete rows of dates from the database
   To delete tasks from the database, we must use the method DELETE and use the URL `/tasks/<int:task_id>` to specify the row (task_id) to delete. In the database, the first elements take on task_id = 2. This is because there was a task in row 1, which was later deleted. This is to demonstrate the effectiveness of the delete command because it is both advantageous and reasonable to maintain the original unique task_id for each row. Hence the data starts at row 2 for the user or team to identify which rows have been deleted and inquire the reasons behind it to maintain the integrity of the data. The following is a demonstration of that.

  
   **In Postman Web**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/92b62636e0ff7b9d1e18f0f27e17ff986d04dd36/images/delete_5_postman.png)


   **The output in the all_tasks table**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/92b62636e0ff7b9d1e18f0f27e17ff986d04dd36/images/delete_5_alltables.png)

   As you can see, the task_id moves from 4 to 6. This is very important so that a team member or the creator may know that the task assigned task_id 5 has been deleted successfully.
   Since the update was a work task, we should expect a change in the work_tasks table as follows.


   **The output in the work_tasks table**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/92b62636e0ff7b9d1e18f0f27e17ff986d04dd36/images/delete_5_worktask.png)
   The work task was successfully deleted.

   `200 OK`

### 6. Get Pending and Overdue Tasks from the database
   Lastly, we can check whether a task is pending or overdue. It is important to note that to check for these 2 functions, the task must be pending and their dates must be >= or < today's date respectively. So for tasks marked "Completed" in the status, they are not meant to be included in the output of these two functions. The method must be GET (to extract) and the URL path `/tasks/pending` and `/tasks/pending` respectively. The output is a list of elements that meet the condition set on the due_date column. The following demonstrations illustrate these two functions.


   ``` bash
   python # get_pending_tasks() and get_overdue_tasks() in Task_manager.py
   def get_pending_tasks(self): 
        with sqlite3.connect(database) as conn: 
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM all_tasks WHERE status = "Pending"') # fetch all pending tasks to know which is still pending according to date 
            tasks = cursor.fetchall() 
            pending_tasks = [] 
            current_date = datetime.now().date()
            for task in tasks: 
                # First we convert to datetime from text using srtptime for datetime operations
                task_due_date = datetime.strptime(task[2], "%Y-%m-%d").date() # task[2] is the due_date entire column
                if task_due_date >= current_date: 
                    pending_tasks.append(task) 
            return pending_tasks
            
        
    def get_overdue_tasks(self): 
        with sqlite3.connect(database) as conn: 
            cursor = conn.cursor() 
            cursor.execute('SELECT * FROM all_tasks WHERE status = "Pending"') # fetch all pending tasks to know which are overdue according to today's date
            tasks = cursor.fetchall() 
            overdue_tasks = []
            current_date = datetime.now().date()
            for task in tasks: 
                task_due_date = datetime.strptime(task[2], "%Y-%m-%d").date() 
                if task_due_date < current_date: 
                    overdue_tasks.append(task) 
            return overdue_tasks
   ```

   **Explanation**:

   `datetime.now().date()`: Returns today's date.

   `pending_tasks = []` and `overdue_tasks = []`: Empty lists that we wish to store the pending and overdue tasks respectively, if any.

   `datetime.strptime(task[2], "%Y-%m-%d")`: This is a datetime function that converts due_date elements from the text to a date with the format YYYY-MM-DD. `task[2]` represents the third column which is the column of due dates. this code is meant to convert text to date so that we can compare each element in column 3 with today's date and identify whether the task is still pending or is **both** pending and overdue.

   The output is as follows:
   **In Postman Web**

   ***Pending tasks***
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/92b62636e0ff7b9d1e18f0f27e17ff986d04dd36/images/pending_tasks.png)

   According to the data, there are three pending tasks in the database. Notice their date is not yet reached from today, and the status of each element in the list is "Pending". It is also important to notice that the output is the list with variable_name `pending_tasks = []`


   ***Overdue task***
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/92b62636e0ff7b9d1e18f0f27e17ff986d04dd36/images/overdue_tasks.png)

   According to the data, there are no overdue tasks in the database. That is because the due dates have not been met from today as previously noted. the output, therefore, is an empty list with variable_name `overdue_tasks = []`. If we add a task with a past task and set it at "Pending", then we would get an element. let's perform the necessary steps.

   
   *1. Create the task and set methods = POST and URL path = "/tasks"*

   ``` bash
   {
    "title": "Winter SHopping",
    "due_date": "2024-11-15",
    "flag": "personal",
    "description": "Shopping to prepare for the coming winter!",
    "priority": "high"
   }
   ```


   **all_tasks**
   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/5f400774ab6d5e7f256ece3810b816c4c541faf6/images/add_overdue_alltasks.png)

   The task is successfully added with task_id of 7. This is important because we are going to cross-reference the task_id in the next step.


   *2. To test if the task is overdue or not. Set methods = GET and URL path = "/tasks/overdue"*

   ![image](https://github.com/Rein101/TaskManagementDatabaseApi/blob/b309aa1c6a92a703d996996935dc86c9c6125c48/images/postman_overdue_output.png)

   Voila!! The task with task_id 7 has been registered into the overdue list, and now we can see the task that was supposed to be done before today.

   `200 OK`: Program executed accordingly.

## Conclusion:
Implementing databases(Relational) is far better than dealing with spreadsheets because the data is more secure, more accessible and less likely to disappear when the Computer's RAM is corrupted since it is not dependent on memory. It is also advantageous because it creates a system where non-shared columns can exist outside of the main table but still contribute to the entire database. It is also noted that it is better and more interactive to use an API server, to avoid memory dependence, and to display the output more interactively compared to using `interface.py` as used in the previous task.

### Points of Learning.

#### 1. `sqlite3` and its functions.

- `CREATE TABLE`: creates a CSV data within the database.

- `INSERT INTO table_name VALUES(?,?...), (a, b,...)`: adds data into a table called `table_name` the elements `a,b,...`

- `SELECT * FROM table_name`: retrieves the elements from `table_name`.

   - It is usually followed by a cursor function:

        - `rows = cursor.fetchall()`: retrieves all the rows from the table.

        - `rows = cursor.fetchmany(size = 5)`: retrieves 5 rows from the table. `size` represents the number of rows to retrieve.
  
        - `rows = cursor.fetchone()`: retrieves only one element, usually denoted by task_id i.e.`... WHERE task_id = ?'),(id,)`.
   
#### References:
1. Lecture notes and Lab practices.
2. https://www.sqlitetutorial.net/sqlite-python/creating-database/
3. https://datagy.io/python-sqlite-tutorial/?form=MG0AV3


#### 2. API and Rest Flask
The scheme started above. How to initialize a FLask() function. the different methods i.e. `POST`, `GET` ,`PUT`, `DELETE` which represent the **CRUD** abbreviation respectively.

**C - CREATE** 

**R - RETRIEVE/EXTRACT** 

**U - UPDATE**

**D - DELETE**

#### References:
1. Lecture notes and Lab practices.
2. https://realpython.com/flask-connexion-rest-api/?form=MG0AV3#initiate-your-flask-project



