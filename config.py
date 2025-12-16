
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-dificil-de-adivinhar'
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'ata.sqlite3')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False