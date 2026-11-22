"""
Vercel / WSGI Serverless Entrypoint for SafeSight AI.
Imports the configured Flask application from run.py.
"""
from run import app

if __name__ == "__main__":
    app.run()
