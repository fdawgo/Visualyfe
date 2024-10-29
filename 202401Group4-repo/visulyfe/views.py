from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user, login_user
from werkzeug.security import check_password_hash
from .models import User

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash("Login Successful!", category='success')
                login_user(user, remember=True)
                return redirect(url_for('auth.home'))
            else:
                flash('Incorrect email or password, Please try again.', category='error')
        else:
            flash('Email does not exist, Please create an account.', category='error')

    return render_template("login.html", user=current_user)