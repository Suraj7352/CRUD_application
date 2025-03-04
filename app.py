import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Ensure this is secret for security purposes

DATABASE = 'todos.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Create user table and todos table
def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            );
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
    print("Database initialized.")


@app.route('/')
def home():
    if 'user_id' in session:
        user_id = session['user_id']
        with get_db() as db:
            todos = db.execute('SELECT * FROM todos WHERE user_id = ?', (user_id,)).fetchall()
        return render_template('index.html', todos=todos)
    return redirect(url_for('login'))


@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session:
        flash("You need to be logged in to add a todo.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        user_id = session['user_id']

        with get_db() as db:
            db.execute('INSERT INTO todos (title, description, user_id) VALUES (?, ?, ?)',
                       (title, description, user_id))
            db.commit()

        flash("Todo added successfully!", "success")
        return redirect(url_for('home'))

    return render_template('add.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with get_db() as db:
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password", "danger")
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        with get_db() as db:
            try:
                db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password_hash))
                db.commit()
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash("Username already taken. Please choose another one.", "danger")

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/update/<int:todo_id>', methods=['GET', 'POST'])
def update(todo_id):
    if 'user_id' not in session:
        flash("You need to be logged in to update a todo.", "danger")
        return redirect(url_for('login'))

    with get_db() as db:
        todo = db.execute('SELECT * FROM todos WHERE id = ? AND user_id = ?', (todo_id, session['user_id'])).fetchone()

    if todo is None:
        flash("Todo not found or you're not authorized to edit this todo.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        with get_db() as db:
            db.execute('UPDATE todos SET title = ?, description = ? WHERE id = ?', (title, description, todo_id))
            db.commit()

        flash("Todo updated successfully!", "success")
        return redirect(url_for('home'))

    return render_template('update.html', todo=todo)


@app.route('/delete/<int:todo_id>')
def delete(todo_id):
    if 'user_id' not in session:
        flash("You need to be logged in to delete a todo.", "danger")
        return redirect(url_for('login'))

    with get_db() as db:
        todo = db.execute('SELECT * FROM todos WHERE id = ? AND user_id = ?', (todo_id, session['user_id'])).fetchone()

    if todo is None:
        flash("Todo not found or you're not authorized to delete this todo.", "danger")
        return redirect(url_for('home'))

    with get_db() as db:
        db.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        db.commit()

    flash("Todo deleted successfully!", "success")
    return redirect(url_for('home'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    todos = []  # Initialize an empty list for todos
    
    if 'user_id' not in session:
        flash("You need to be logged in to search for todos.", "danger")
        return redirect(url_for('login'))  # Redirect to login if the user is not logged in
    
    if request.method == 'POST':
        query = request.form['query']
        
        # Perform search in the database based on the title or description
        with get_db() as db:
            todos = db.execute('''
                SELECT * FROM todos 
                WHERE (title LIKE ? OR description LIKE ?) 
                AND user_id = ?
            ''', ('%' + query + '%', '%' + query + '%', session['user_id'])).fetchall()

    return render_template('search.html', todos=todos)


if __name__ == '__main__':
    init_db()  # Initialize the database if it doesn't exist
    app.run(debug=False,host='0.0.0.0',port=8000)
