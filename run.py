"""
Application entry point.
"""

import os
from app import create_app
from flask.cli import FlaskGroup

# Создаем FlaskGroup для поддержки команд CLI, включая 'flask db'
cli = FlaskGroup(create_app=lambda: create_app(os.environ.get('FLASK_ENV', 'development')))

if __name__ == '__main__':
    # Запускаем приложение через CLI
    cli()
