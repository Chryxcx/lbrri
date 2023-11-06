from flask import Blueprint, render_template
from flask_login import login_required, current_user


view = Blueprint('view', __name__)

@view.route('/home')
@login_required
def home():
    return render_template("home.html", user=current_user)