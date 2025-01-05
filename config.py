import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'Ihr_Secret_Key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///appointments.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
