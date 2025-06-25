# seu_projeto_flask/run.py

from flask import Flask
from app import create_app, db # Importa a factory e a instância do DB
from app.models import User, Member, Project, Ata # Importa os modelos
from flask_migrate import Migrate # Importa Migrate
import click # Importa Click para criar comandos CLI

# Cria a instância da aplicação Flask usando a factory
app = create_app()

# Configura o Flask-Migrate
migrate = Migrate(app, db)

# Cria um contexto de shell que importa o app e o db automaticamente
@app.shell_context_processor
def make_shell_context():
    """Adiciona instâncias ao contexto do shell Flask."""
    return {'db': db, 'User': User, 'Member': Member, 'Project': Project, 'Ata': Ata}

# --- Comando Personalizado para Criar Usuário ---
@app.cli.command("create-user")
@click.option('--username', prompt=True, help='O nome de usuário para o novo admin.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='A senha para o novo admin.')
def create_user(username, password):
    """Cria o usuário administrador inicial."""
    # O contexto da aplicação é necessário para interagir com o banco de dados
    with app.app_context():
        # Verificar se o usuário já existe
        if User.query.filter_by(username=username).first():
            click.echo(f"Erro: Usuário '{username}' já existe.")
            return # Sai do comando

        # Criar o novo usuário
        user = User(username=username)
        user.set_password(password) # Usa o método do modelo para hashear

        # Adicionar e salvar no banco
        try:
            db.session.add(user)
            db.session.commit()
            click.echo(f"Usuário '{username}' criado com sucesso!")
        except Exception as e:
            db.session.rollback() # Desfaz em caso de erro no commit
            click.echo(f"Erro ao criar usuário: {e}")
            app.logger.error(f"Erro ao criar usuário: {e}") # Loga o erro também

# --- Fim do Comando Personalizado ---

# Permite executar o servidor diretamente com `python run.py`
#if __name__ == '__main__':
#    app.run()