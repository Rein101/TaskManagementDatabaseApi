# first we import the sqlite3 module
import sqlite3

database = "Task.db"
# then we make a connection object for the SQLite database Task.db using the connect() function
# I use with in this case to close the database as a connection object
def data_connect():
    try:
        with sqlite3.connect(database) as conn:
            # then we create a cursor object in order to create the table we want
            cursor = conn.cursor()
            # then using the cursor object, we can execute a table using execute() function and the SQL lexis CREATE TABLE
            
            # first we create the general table with the attributes in Task class
            cursor.execute(""" CREATE TABLE IF NOT EXISTS all_tasks(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        due_date TEXT NOT NULL,
                        status TEXT DEFAULT "Pending" CHECK(status IN ('Pending', 'Completed')),
                        flag TEXT CHECK(flag IN ("personal", "work")),
                        description TEXT
                        )
            """)
            # secondly, we create the personal tasks data. It should have their unique task_id, the respective priority, due_date, status and description
            cursor.execute(""" CREATE TABLE IF NOT EXISTS personal_tasks(
                        task_id INTEGER,
                        priority TEXT DEFAULT 'low' CHECK(priority IN ('high','medium','low')),
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

    except sqlite3.OperationalError as e:
        print("Table not created ", e)
