from flask import Blueprint, render_template,session,flash, redirect, url_for
from functools import wraps
from flask_login import  current_user


view = Blueprint('view', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and 'role' in session and session['role'] == 'admin':
            return f(*args, **kwargs)
        else:
            flash("You must be an admin to access this page.", "warning")
            return redirect(url_for('auth.admin_login'))
    return decorated_function


def librarian_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and 'role' in session and session['role'] == 'librarian':
            return f(*args, **kwargs)
        else:
            flash("You must be a librarian to access this page.", "warning")
            session.clear()
            return redirect(url_for('auth.admin_login'))
    return decorated_function

def both_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and 'role' in session and (session['role'] == 'librarian' or session['role'] == 'admin'):
            return f(*args, **kwargs)
        else:
            flash("You must be a librarian to access this page.", "warning")
            session.clear()
            return redirect(url_for('auth.login'))
    return decorated_function


@view.route('/')
@both_required
def home():
    return render_template("home.html", user=current_user)