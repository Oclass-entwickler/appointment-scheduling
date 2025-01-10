import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'MEIN_GEHEIMNIS'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///appointments.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Mail Konfiguration für Gmail
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # statt 'hasankeisar@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # statt 'oate yljt eetx uokp'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')  # statt 'hasankeisar@gmail.com'
