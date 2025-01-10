import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'المفتاح_السري_الخاصة_بي'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///appointments.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Mail Konfiguration (optional, falls Sie E-Mails senden möchten)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # z. B. 'mygmail@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # App-Passwort
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')  # gleiche Adresse wie MAIL_USERNAME
