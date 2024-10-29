from flask import Flask, session, request, jsonify
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from os import path
from kaggle.api.kaggle_api_extended import KaggleApi
from kaggle.rest import ApiException
from flask_mail import Mail
from werkzeug.utils import secure_filename
import os

db = SQLAlchemy()
DB_NAME = "visulyfe.db"

mail = Mail()
api = KaggleApi()
api.authenticate()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'visualkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'visulyfe@gmail.com'
    app.config['MAIL_PASSWORD'] = 'qawl evfb aqiu svcv'

    mail.init_app(app)
    
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix = '/')
    app.register_blueprint(auth, url_prefix ='/')
    
    from .models import User

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'views.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    @app.before_request
    def fetch_and_store_datasets():
        try:
            dataset_list = api.datasets_list()
            formatted_datasets = []
            for dataset in dataset_list:
                formatted_dataset = {
                    'title': dataset['title'],
                    'url': dataset['url'],    
                }
                formatted_datasets.append(formatted_dataset)
            session['datasets'] = formatted_datasets
            print("Datasets fetched and stored successfully.")     
        except ApiException as e:
            error_message = f"Exception when calling KaggleApi->datasets_list: {e}"
            print(error_message)
    
    @app.route('/search', methods=['GET'])
    def search_datasets():
        # Get the query parameter from the request
        query = request.args.get('query')
        
        if query:
            try:
                # Call the API to search datasets based on the query
                search_results = api.datasets_list(search=query)
                
                # Format the search results
                formatted_results = []
                for dataset in search_results:
                    result = {'title': dataset['title'], 'url': dataset['url'],
                               'refrence': dataset['ref']}
                        
                    formatted_results.append(result)
                
                # Return the formatted results as JSON
                return jsonify({'results': formatted_results})
            except ApiException as e:
                # If an exception occurs during the API call, return an error message
                return jsonify({'error': str(e)})
        else:
            # If no query is provided, return an error message
            return jsonify({'error': 'No query provided'})

    return app

def download_csv_from_kaggle(dataset_ref, destination_dir):

    # Ensure the directory exists
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    # Download the dataset and unzip it
    api.dataset_download_files(dataset_ref, path=destination_dir, unzip=True)

    # Find CSV files in the directory
    csv_files = [f for f in os.listdir(destination_dir) if f.endswith('.csv')]

    if not csv_files:
        raise ValueError("No CSV files found in the downloaded dataset.")

    # Get the first CSV file
    csv_file = csv_files[0]
    full_path = os.path.join(destination_dir, csv_file)

    return full_path  # Return the full path to the downloaded CSV file
    
def create_database(app):
    if not path.exists('website/' + DB_NAME):
        with app.app_context():
            db.create_all()
        print("Created Database")

