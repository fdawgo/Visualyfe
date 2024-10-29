from datetime import datetime
from tempfile import mkdtemp
from flask import Blueprint, app, jsonify, redirect, render_template, render_template_string, request, flash, send_file, send_from_directory, session, url_for
from flask_login import login_user, login_required, logout_user, current_user
import pandas as pd
from .models import User, Datasets
from kaggle.api.kaggle_api_extended import KaggleApi
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from . import db, download_csv_from_kaggle, mail
import os
import plotly.express as px
import os
from flask import render_template, jsonify

s = URLSafeTimedSerializer("your-secret-key")
special_characters = set("!@#$%^&*()_+{}[]:\;<>?,./\\|")
auth = Blueprint('auth', __name__)

ALLOWED_EXTENSIONS = {'csv'}  #this extension is the only file that will be accepted. 

@auth.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    print("Current user ID:", current_user.id)
    user_datasets = Datasets.query.filter_by(user_id=current_user.id).all()
    kaggle_datasets = session.get('datasets', [])
    if not kaggle_datasets:
        flash('Failed to fetch datasets from Kaggle.', category='error')
    return render_template("home.html", user=current_user, user_datasets=user_datasets, datasets=kaggle_datasets)


def allowed_file(filename): ##checks that the file is a .csv file and returns a boolean 
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auth.route('/download_and_display_columns', methods=['POST'])
@login_required
def download_and_upload():

    #Download a Kaggle dataset and store it in the database
    data = request.json
    dataset_ref = data.get('dataset_ref')

    #Validate required fields
    if not all([dataset_ref]):
        return jsonify({'error': 'All fields must be filled'}), 400

    try:
        # Download the CSV file from Kaggle
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tmp_dir = os.path.join(base_dir, 'tmp')  

        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        csv_path = download_csv_from_kaggle(dataset_ref, tmp_dir)
        file = None
        
        # Open the CSV file
        file = open(csv_path, 'rb')
        filename = secure_filename(os.path.basename(csv_path))
        if not allowed_file(filename):
            print("Received file:", filename)
            return jsonify({'error': 'Invalid file format. Please upload a CSV file.'}), 400

        columns = get_column_names(pd.read_csv(file))
        return jsonify({'message': 'CSV downloaded and stored successfully', 
                        'csv_path': csv_path, 'columns' : columns}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
  # Import your Datasets model

@auth.route('/save', methods=['POST']) 
def save(): 
    data = request.json
    name = data.get('dataset_name')
    path = data.get('file_path')

    if os.path.exists(path):  # Check if the file exists
        if os.path.getsize(path) == 0:  # Check if the file is empty
            return jsonify({"Empty": "There is no file to save"}), 200
        else:
            with open(path, 'rb') as file:
                content = file.read()

            dataset = Datasets(
                filename=name,
                upload_date=datetime.now(),
                user_id=current_user.id,
                content=content
            )

            db.session.add(dataset)
            db.session.commit()

            return jsonify({'success': 'Saved Dataset'}), 200
    else:
        return jsonify({"error": "File not found"}), 404


@auth.route('/create_graph', methods=['POST'])
@login_required
def create_graph():
    #Create a graph using the X and Y columns provided by the user.
    data = request.json
    name = data.get('dataset_name')
    graph = data.get('graph')
    color = data.get('color')
    x_column = int(data.get('x_column'))
    y_column = int(data.get('y_column'))
    csv_path = data.get('file_path')  # Path to the temporary CSV file
    print(name)
    print(graph)
    print(x_column)
    print(y_column)
    print(csv_path)
    # Validate required fields
    # if not all([x_column, y_column, csv_path]):
    #     return 'All fields must be filled', 400
    try:
        # Read the CSV file
        df = pd.read_csv(csv_path)
        print("worked")
        # Convert column indices to column names
        x_column_name = df.columns[x_column]
        y_column_name = df.columns[y_column]

        if graph == 'line':
            # Generate the plot
            fig = px.line(df, x=x_column_name, y=y_column_name, title=name)
            fig.update_traces(line=dict(color=color))
        elif graph == 'scatter':
            # Generate the plot
            fig = px.scatter(df, x=x_column_name, y=y_column_name, title=name)
            fig.update_traces(marker=dict(color=color))
        elif graph == 'bar':
            # Generate the plot
            fig = px.bar(df, x=x_column_name, y=y_column_name, title=name)
            fig.update_traces(marker=dict(color=color))
        
        # Save the plot as an HTML string
        graph_html = fig.to_html(full_html=False)

        if os.path.exists(csv_path):
            try:
                os.remove(csv_path)
            except Exception as delete_error:
                app.logger.warning(f"Failed to delete temporary file: {delete_error}")
        # Return the HTML content
        return render_template('graph.html', graph_div=graph_html)

    except Exception as e:
        print("Error", e)
        return f'Error: {str(e)}', 500
# @auth.route('/plot')
# def download_plot(filename):
#     # Serve the HTML file
#     return send_from_directory(directory=os.path.dirname(filename), filename=os.path.basename(filename))

def get_column_names(df):
    columns = df.columns.tolist()
    return columns

# this one links to the Password Submission page
@auth.route('/reset-pass<token>', methods=['GET', 'POST'])
def new_pass_page(token):
    try:
        # Decode the token to get the user's email
        email = s.loads(token, salt='password-recover-salt', max_age=3600)  # Token expires in 1 hour
    except Exception:
        flash("The reset link is invalid or has expired.", category='error')
        return redirect(url_for('auth.forgot_password'))  # Redirect to a page to request another reset
    if request.method == 'POST':
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if len(password1) < 8:
            flash('Password must be at least 8 characters.', category='error')
        elif not (any(char.isupper() for char in password1) and
                  any(char.isdigit() for char in password1) and
                  any(char in special_characters for char in password1)):
            flash('Password must contain at least one uppercase letter, one number, and one special character', category='error')
        elif password1 != password2:
            flash("Please be sure that both passwords match.", category='error')
        else:
            # Find the user by email
            user = User.query.filter_by(email=email).first()
            if user:
                # Update user's password
                user.password = generate_password_hash(password1, method='pbkdf2:sha256')
                db.session.commit()
                flash("Password successfully updated. You can now login with your new password.", category='success')
                return redirect(url_for('views.login'))  # Redirect to Login page
    return render_template("newpassform.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.login'))

@auth.route('/about', methods=['GET'])
def about():
    return render_template("about.html", user=current_user)

# this is the route that adds funtionality to it
@auth.route('/recover-pass', methods=['GET', 'POST'])
def password_recover_post():
    if request.method == 'POST':
        email = request.form.get('email')

        if User.query.filter_by(email=email).first():
            # Create a token for the user with a time limit (e.g., 1 hour)
            token = s.dumps(email, salt='password-recover-salt')

            # Generate the password reset URL
            reset_url = url_for('auth.new_pass_page', token=token, _external=True)

            # Send the email
            subject = "Password Recovery"
            msg = Message(subject, sender="visulyfe@gmail.com", recipients=[email])
            msg.body = f"Click the following link to reset your password: {reset_url}"
            mail.send(msg)

            flash("A password reset link has been sent to your email.", category='info')
        
        return redirect(url_for('views.login'))

    return render_template("passrecovery.html", user=current_user)  # Password recovery page template

#@app.route('/dashboard')
#def dashboard():
    # Fetch the user's graphs from the database
    #user_datasets = Graph.query.filter_by(user_id=current_user.id).all()
    #return render_template('dashboard.html', user_datasets=user_datasets)

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstname')
        last_name = request.form.get('lastname')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email=email).first()

        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 4 characters.', category='error')
        elif len(password1) < 8:
            flash('Password must be at least 8 characters.', category='error')
        elif not any(char.isupper() for char in password1) or not any(char.isdigit() for char in password1) or not any(char in special_characters for char in password1):
            flash('Password must contain at least one uppercase letter, one number, and one special character', category='error')
        elif password1 != password2:
            flash("Please be sure that both passwords match.", category='error')
        else:
            new_user = User(email=email, first_name=first_name, last_name=last_name, 
                password=generate_password_hash(password1, method='pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash("Account created. You are now able to login.", category="success")
            return redirect(url_for('views.login'))
         
    return render_template("signup.html", user=current_user)

@auth.route('/delete-dataset/<int:dataset_id>', methods=['POST'])
@login_required
def delete_dataset(dataset_id):
    # Fetch the dataset, or return 404 if not found
    dataset = Datasets.query.filter_by(id=dataset_id, user_id=current_user.id).first_or_404()

    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('auth.home'))
    
    try:
        dataset = Datasets.query.filter_by(id=dataset_id, user_id=current_user.id).first_or_404()
        db.session.delete(dataset)
        db.session.commit()
    except Exception as e:
        db.session.rollback()  # Roll back on exception
        flash('An error occurred while deleting the dataset.', 'error')
        print(f"Error deleting dataset: {e}")
    return redirect(url_for('auth.home'))

@auth.route('/upload', methods=['POST'])
@login_required
def upload_file():
    
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tmp_dir = os.path.join(base_dir, 'tmp')  

        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(tmp_dir, filename)
            file.save(file_path)

            # Open the CSV file
            with open(file_path, 'rb') as csv_file:
                columns = get_column_names(pd.read_csv(csv_file))
            print(columns)
            print(file_path)
            return jsonify({'message': 'CSV uploaded and stored successfully', 
                            'csv_path': file_path, 'columns': columns, 'filename': file.filename}), 200

        else:
            return jsonify({'error': 'Invalid file format. Please upload a CSV file.'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    