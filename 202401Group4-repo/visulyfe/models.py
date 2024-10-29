from . import db
from flask_login import UserMixin
from sqlalchemy import func

# Side Note: this model only stores information of the csv file and when it was uploaded.
class Datasets(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.LargeBinary, nullable=True)  # Add a new column to store file content

# Adds the User to the database
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(150), unique = True)
    password = db.Column(db.String(150), nullable=False)
    first_name  = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    datasets = db.relationship('Datasets', backref='user', lazy=True)
