"""
Authentication Routes for SafeSight AI.
Supports authentication using:
1. Database users (`users` table with secure password hashing).
2. Environment variables (`LOGIN_USERNAME` and `LOGIN_PASSWORD`), checked dynamically on request.
Includes registration (/register) to create and manage credentials easily.
"""
import os
import logging
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import execute_query, execute_insert

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    GET  -> render the login form.
    POST -> validate credentials against Database users and Environment variables.
    """
    if session.get("logged_in"):
        return redirect(url_for("pages.landing"))

    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        authenticated = False

        if username and password:
            # 1. Check database users table
            try:
                user_rows = execute_query(
                    "SELECT * FROM users WHERE username = %s",
                    (username,),
                    fetch=True
                )
                if user_rows:
                    user_record = user_rows[0]
                    # Verify password hash
                    if check_password_hash(user_record.get("password_hash", ""), password):
                        authenticated = True
            except Exception as e:
                logger.error(f"Error querying users table during login: {e}")

            # 2. Check dynamic environment variables if not authenticated via DB
            if not authenticated:
                env_user = os.environ.get("LOGIN_USERNAME", "").strip()
                env_pass = os.environ.get("LOGIN_PASSWORD", "")
                if env_user and env_pass and username == env_user and password == env_pass:
                    authenticated = True

        if authenticated:
            session.permanent = True
            session["logged_in"] = True
            session["username"] = username
            logger.info("User '%s' logged in successfully.", username)
            next_page = request.args.get("next") or url_for("pages.landing")
            return redirect(next_page)
        else:
            error = "Wrong username or password"
            logger.warning("Failed login attempt for username: '%s'.", username)

    return render_template("login.html", error=error)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    GET  -> render registration form.
    POST -> create a new user account with hashed password in the database.
    """
    if session.get("logged_in"):
        return redirect(url_for("pages.landing"))

    error = None
    success = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            error = "Username and password are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif len(password) < 4:
            error = "Password must be at least 4 characters long."
        else:
            try:
                existing = execute_query(
                    "SELECT id FROM users WHERE username = %s",
                    (username,),
                    fetch=True
                )
                if existing:
                    error = "An account with that username/email already exists."
                else:
                    pwd_hash = generate_password_hash(password)
                    execute_insert(
                        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                        (username, pwd_hash)
                    )
                    logger.info("New user registered successfully: '%s'", username)
                    return render_template("login.html", success="Account created successfully! Please log in with your credentials.")
            except Exception as e:
                logger.error(f"Error registering user: {e}")
                error = "Registration failed due to a database error. Please try again."

    return render_template("register.html", error=error, success=success)


@auth_bp.route("/logout")
def logout():
    """Clears the session and redirects to the login page."""
    username = session.get("username", "unknown")
    session.clear()
    logger.info("User '%s' logged out.", username)
    return redirect(url_for("auth.login"))
