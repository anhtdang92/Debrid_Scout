# app/routes/account.py

from flask import Blueprint, render_template
import logging

account_bp = Blueprint('account', __name__)
logger = logging.getLogger(__name__)


@account_bp.route("/account")
def account_info():
    """
    Render the account information page.

    Account info is automatically injected by the context processor
    in __init__.py (cached with a 5-minute TTL).
    """
    return render_template('account_info.html')
