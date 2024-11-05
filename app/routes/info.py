# app/routes/info.py
from flask import Blueprint, render_template

info_bp = Blueprint('info', __name__)

@info_bp.route('/about')
def about():
    return render_template('about.html')

@info_bp.route('/contact')
def contact():
    return render_template('contact.html')