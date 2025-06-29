# config.py

import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-dificil-de-adivinhar'
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')

    # --- NOVA CONFIGURAÇÃO DO BANCO DE DADOS ---
    # Usando suas credenciais REAIS que você criou no PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')

    
    SQLALCHEMY_TRACK_MODIFICATIONS = False