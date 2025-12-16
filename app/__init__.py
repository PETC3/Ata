# seu_projeto_flask/app/__init__.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate # Embora inicializado em run.py, é bom tê-lo aqui se precisar em outros lugares
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config # Importa a classe de configuração

# Cria instâncias das extensões FORA da factory para que possam ser importadas
# por outros módulos (como models.py, routes.py) sem causar importações circulares
# e antes que o 'app' esteja totalmente configurado.
db = SQLAlchemy()
migrate = Migrate() # Instância do Migrate pode ser criada aqui também
login_manager = LoginManager()
csrf = CSRFProtect()

# Configuração do Flask-Login:
# Para onde o Flask-Login redireciona o usuário se ele tentar acessar
# uma página protegida sem estar logado. 'auth.login' seria o nome da view de login
# se estivéssemos usando Blueprints. Vamos definir a rota '/login' mais tarde.
login_manager.login_view = 'login'
# Mensagem exibida quando o usuário é redirecionado para o login.
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
# Categoria da mensagem flash (para estilização, se usar Bootstrap por exemplo).
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    """
    Application Factory: Cria e configura a instância do Flask.
    Permite criar múltiplas instâncias com diferentes configurações (ex: para testes).
    """
    app = Flask(__name__, instance_relative_config=True)
    

    # Carrega a configuração a partir do objeto Config importado
    app.config.from_object(config_class)
    
        # Só depois sobrepõe (se quiser forçar Debug)
    app.config['ENV'] = 'development'
    app.config['DEBUG'] = True

    # Tenta carregar configuração adicional da pasta 'instance', se existir
    # Útil para segredos que não devem ir para o controle de versão (como API keys)
    # Ex: instance/config.py (não versionado)
    # app.config.from_pyfile('config.py', silent=True)

    # Garante que a pasta de instância exista (onde o SQLite DB ficará)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # Pasta já existe

    # Inicializa as extensões Flask com a instância 'app'
    db.init_app(app)
    # O migrate pode ser inicializado aqui ou em run.py.
    # Se inicializado aqui, run.py precisaria importar 'migrate' daqui.
    # Deixar a inicialização principal em run.py como fizemos é comum.
    # migrate.init_app(app, db) # Alternativa a inicializar em run.py
    login_manager.init_app(app)
    csrf.init_app(app) # Inicializa a proteção CSRF

    # Importa e registra as rotas e modelos DENTRO da factory
    # para evitar importações circulares.
    # Os modelos precisam ser definidos antes de criar as tabelas ou rodar migrações.
    with app.app_context():
        from . import routes, models # Importa rotas e modelos do pacote 'app'
        # (Opcional) Cria as tabelas automaticamente quando estiver usando SQLite e
        # o arquivo de banco ainda não existir. Isso é útil para desenvolvimento local
        # sem precisar aplicar migrações (que podem ter especificidades de Postgres).
        uri = app.config.get('SQLALCHEMY_DATABASE_URI', '') or ''
        if uri.startswith('sqlite:///'):
            db_path = uri.replace('sqlite:///', '', 1)
            # Se o banco não existir, cria as tabelas automaticamente
            try:
                if not os.path.exists(db_path):
                    db.create_all()
                    print(f"SQLite DB not found; created new DB at: {db_path}")
            except Exception as e:
                # Se algo falhar aqui (ex: permissões), apenas logue a exceção
                print(f"Warning: failed to auto-create sqlite DB: {e}")

        # Se estiver usando Blueprints, eles seriam registrados aqui:
        # from .auth import auth as auth_blueprint
        # app.register_blueprint(auth_blueprint, url_prefix='/auth')
        # from .main import main as main_blueprint
        # app.register_blueprint(main_blueprint)

    print(f"Upload folder configured at: {app.config['UPLOAD_FOLDER']}") # Debug: verificar pasta upload
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}") # Debug: verificar URI DB

    return app