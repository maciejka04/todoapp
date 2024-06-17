import pymssql
import configparser
import os
from flask import Flask, render_template, request, redirect, url_for

class ConfigLoader:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file)
        return config

    def get(self, section, option):
        return self.config.get(section, option)


class Database:
    def __init__(self, config):
        self.server = config.get('Database', 'server')
        self.user = config.get('Database', 'user')
        self.password = config.get('Database', 'password')
        self.database = config.get('Database', 'database')

    def connect(self):
        return pymssql.connect(self.server, self.user, self.password, self.database)

    def execute_query(self, query, params=()):
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

    def execute_non_query(self, query, params=()):
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()

class ToDoApp:
    def __init__(self, db):
        self.db = db
        self.app = Flask(__name__)
        self.app.add_url_rule('/', view_func=self.home, methods=['POST', 'GET'])
        self.app.add_url_rule('/delete/<int:task_id>', view_func=self.delete_task, methods=['POST'])
        self.app.add_url_rule('/highest_priority_tasks', view_func=self.highest_priority_tasks, methods=['GET'])
        self.app.add_url_rule('/edit/<int:task_id>', view_func=self.edit_task, methods=['POST', 'GET'])

    def home(self):
        last_task = None
        all_tasks = []
        search = None
        total_tasks_count = 0

        try:
            if request.method == 'POST':
                task_name = request.form['task_name']
                task_priority = request.form['task_priority']
                self.db.execute_non_query(
                    "INSERT INTO dbo.To_do_app (task_name, task_priority) VALUES (%s, %s)",
                    (task_name, task_priority)
                )

            last_task = self.db.execute_query(
                "SELECT TOP 1 * FROM dbo.To_do_app ORDER BY task_time DESC"
            )[0]

            if request.method == 'GET':
                search = request.args.get('search')

            if search:
                query = '%' + search + '%'
                all_tasks = self.db.execute_query(
                    "SELECT * FROM dbo.To_do_app WHERE task_name LIKE %s ORDER BY task_time DESC",
                    (query,)
                )
            else:
                all_tasks = self.db.execute_query(
                    "SELECT * FROM dbo.To_do_app ORDER BY task_time DESC"
                )
            total_tasks_count = (lambda tasks: len(tasks))(all_tasks)

        except Exception as e:
            print("Error executing query:", e)

        return render_template('home.html', last_task=last_task, all_tasks=all_tasks, search=search, total_tasks_count=total_tasks_count)

    def delete_task(self, task_id):
        try:
            if request.method == 'POST':
                self.db.execute_non_query(
                    "DELETE FROM dbo.To_do_app WHERE task_id = %s",
                    (task_id,)
                )
                print("Task removed successfully!")
        except Exception as e:
            print("Error executing query:", e)
        return redirect(url_for('home'))

    def highest_priority_tasks(self):
        highest_priority_tasks = []
        all_tasks = []
        total_tasks_count = 0
        highest_priority_count = 0
        try:
            highest_priority_tasks = self.db.execute_query(
                "SELECT * FROM dbo.To_do_app WHERE task_priority = 2"
            )
            all_tasks = self.db.execute_query(
                "SELECT * FROM dbo.To_do_app ORDER BY task_time DESC"
            )
            total_tasks_count = (lambda tasks: len(tasks))(all_tasks)

            highest_priority_count = (lambda tasks: len(tasks))(highest_priority_tasks)

        except Exception as e:
            print("Error executing query:", e)
        return render_template('home.html', highest_priority_tasks=highest_priority_tasks, all_tasks=all_tasks, total_tasks_count=total_tasks_count, highest_priority_count=highest_priority_count)

    def edit_task(self, task_id):
        try:
            if request.method == 'POST':
                task_name = request.form['task_name']
                task_priority = request.form['task_priority']
                self.db.execute_non_query(
                    "UPDATE dbo.To_do_app SET task_name = %s, task_priority=%s WHERE task_id=%s",
                    (task_name, task_priority, task_id)
                )
            if request.method == 'GET':
                task = self.db.execute_query(
                    "SELECT * FROM dbo.To_do_app WHERE task_id=%s",
                    (task_id,)
                )[0]
                return render_template('edit.html', task=task)
        except Exception as e:
            print("Error executing query:", e)
        return redirect(url_for('home'))

    def run(self):
        self.app.run(debug=True, use_reloader=False)

if __name__ == '__main__':
    config_loader = ConfigLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.conf'))
    db = Database(config_loader)
    todo_app = ToDoApp(db)
    todo_app.run()