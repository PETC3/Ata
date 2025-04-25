# seu_projeto_flask/config.py
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env (opcional, mas bom para secrets)
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Configurações base da aplicação."""
    # Chave secreta para segurança de sessões e formulários CSRF
    # É MUITO IMPORTANTE gerar uma chave segura e mantê-la secreta!
    # Pode gerar uma com: python -c 'import secrets; print(secrets.token_hex(16))'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'voce-precisa-mudar-esta-chave-secreta'

    # Configuração do Banco de Dados (SQLite neste exemplo)
    # O banco ficará na pasta 'instance', que não deve ir para o controle de versão
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'site.db')
    # Desativa um recurso do SQLAlchemy que não usaremos e consome recursos
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pasta para salvar os uploads (logos dos projetos)
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'app', 'static', 'uploads')

    # Garante que a pasta de uploads exista
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Outras configurações podem ser adicionadas aqui
    # Ex: Configurações de email para recuperação de senha, etc.