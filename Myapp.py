from flask import Flask, abort, render_template, url_for, flash, redirect, request
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_bcrypt import Bcrypt
from models import db, User, Todo
from forms import RegistrationForm, LoginForm, TodoForm
import os
from werkzeug.utils import secure_filename
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "62913a7dac3933f87a84626fcdeaaf9e2653f0a000843efd9bf2b31ba4767402"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/todo_images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Use Session.get() for SQLAlchemy 2.0 compatibility

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Home route
@app.route("/")
def home():
    return render_template("home.html", title="Home")

# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('login'))
    return render_template("register.html", title="Register", form=form)

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template("login.html", title="Login", form=form)

# Logout route
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))
@app.route("/todo", methods=['GET', 'POST'])
@login_required
def todo():
    form = TodoForm()
    
    if form.validate_on_submit():
        print("Form is valid!")  # Debugging line
        
        image_file = None
        if form.image.data:
            file = form.image.data
            if allowed_file(file.filename):  # Check if the file type is allowed
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_file = filename

        todo = Todo(
            title=form.title.data,
            content=form.content.data,
            image_file=image_file,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            author=current_user
        )
        try:
            db.session.add(todo)
            db.session.commit()
            flash('Todo created!', 'success')
            print("Task saved successfully!")  # Debugging line
            return redirect(url_for('todo'))
        except Exception as e:
            print(f"Error committing to the database: {e}")  # Debugging line
            db.session.rollback()  # Rollback if there's an error
    else:
        print("Form is not valid")  # Debugging line
        print(form.errors)  # Print the form errors to identify issues

    todos = Todo.query.filter_by(user_id=current_user.id).order_by(Todo.start_date.desc()).all()
    return render_template('todo.html', title='Todo List', form=form, todos=todos)
# Edit todo route
@app.route("/todo/<int:todo_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        abort(403)  # Forbidden access
    form = TodoForm()
    if form.validate_on_submit():
        todo.title = form.title.data
        todo.content = form.content.data
        todo.start_date = form.start_date.data
        todo.end_date = form.end_date.data
        if form.image.data:
            file = form.image.data
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                todo.image_file = filename
        db.session.commit()
        flash('Your task has been updated!', 'success')
        return redirect(url_for('todo'))
    elif request.method == 'GET':
        form.title.data = todo.title
        form.content.data = todo.content
        form.start_date.data = todo.start_date
        form.end_date.data = todo.end_date
    return render_template('edit_todo.html', title='Edit Task', form=form)

# Delete todo route
@app.route("/todo/<int:todo_id>/delete", methods=['POST'])
@login_required
def delete_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        abort(403)  # Forbidden access
    db.session.delete(todo)
    db.session.commit()
    flash('Your task has been deleted!', 'success')
    return redirect(url_for('todo'))

# Run the app
if __name__ == "__main__":
    app.run(debug=True)