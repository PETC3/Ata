# app.py
import os
from flask import (Flask, render_template, redirect, url_for, flash, request,
                   send_from_directory, make_response, send_file, jsonify) # Adicionar jsonify para API
from io import BytesIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
# Importar MetaData é opcional aqui, pois acessaremos via db.metadata
# from sqlalchemy import MetaData
from flask_login import (LoginManager, login_user, logout_user, login_required,
                         current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- Configuração Inicial ---
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-forte-e-dificil-de-adivinhar-troque'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 # Limite de upload 5MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Convenção de Nomenclatura para Constraints SQLAlchemy ---
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# --- Inicialização das Extensões ---

# 1. Inicialize SQLAlchemy SEM passar metadata_obj
db = SQLAlchemy(app)

# 2. Aplique a convenção de nomenclatura ao metadata do SQLAlchemy APÓS a inicialização
db.metadata.naming_convention = convention

# 3. Inicialize Migrate com render_as_batch=True para suporte a SQLite
#    Ele usará o db.metadata que agora contém a convenção.
migrate = Migrate(app, db, render_as_batch=True)

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"


# --- Modelos e Formulários (Importar DEPOIS de db e login_manager) ---
from models import User, Member, Project, Ata, AtaAttendee
from forms import LoginForm, MemberForm, ProjectForm, AtaForm


# --- Funções Auxiliares ---
def allowed_file(filename):
    """Verifica se a extensão do arquivo de logo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Função de geração de PDF (será movida para utils/pdf_generator.py depois)
# Placeholder por enquanto
def generate_ata_pdf_placeholder(ata_id):
     # Importar somente quando necessário (ou mover para módulo dedicado)
     from reportlab.pdfgen import canvas
     from reportlab.lib.pagesizes import letter
     buffer = BytesIO()
     p = canvas.Canvas(buffer, pagesize=letter)
     p.drawString(100, 750, f"Relatório Placeholder para Ata ID: {ata_id}")
     p.drawString(100, 735, "Conteúdo real da ata virá aqui.")
     # Adicionar mais detalhes se possível, mesmo no placeholder
     try:
        ata = Ata.query.get(ata_id)
        if ata:
            p.drawString(100, 715, f"Projeto: {ata.project.name}")
            p.drawString(100, 700, f"Data: {ata.date.strftime('%d/%m/%Y')}")
     except Exception:
         pass # Ignora erros se não conseguir buscar a ata
     p.showPage()
     p.save()
     buffer.seek(0)
     return buffer


# --- Flask-Login User Loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Comandos CLI ---
@app.cli.command("create-user")
def create_user():
    """Cria o usuário inicial para login."""
    if User.query.first():
        print("(!) Um usuário já existe. Use o shell Flask para gerenciar usuários.")
        return
    username = input("-- Digite o nome de usuário desejado: ")
    password = input(f"-- Digite a senha para {username}: ")
    user = User(username=username)
    user.set_password(password)
    try:
        db.session.add(user)
        db.session.commit()
        print(f"(*) Usuário '{username}' criado com sucesso!")
    except Exception as e:
        db.session.rollback()
        print(f"[!] Erro ao criar usuário: {e}")

# --- Rotas ---

# Rotas Principais e Autenticação
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        project_count = Project.query.count()
        member_count = Member.query.count()
        ata_count = Ata.query.count()
    except Exception as e:
        flash(f"Erro ao carregar dados do dashboard: {e}", "danger")
        project_count = 0
        member_count = 0
        ata_count = 0
    return render_template('dashboard.html', title='Dashboard',
                           project_count=project_count,
                           member_count=member_count,
                           ata_count=ata_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Login realizado com sucesso!', 'success')
            next_page = request.args.get('next')
            if next_page and not next_page.startswith('/'):
                 next_page = url_for('dashboard')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Login inválido. Verifique usuário e senha.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))


# Rotas CRUD de Membros
@app.route('/members')
@login_required
def list_members():
    try:
        members = Member.query.order_by(Member.name).all()
    except Exception as e:
        flash(f"Erro ao buscar membros: {e}", "danger")
        members = []
    return render_template('members_list.html', title='Membros', members=members)

@app.route('/members/add', methods=['GET', 'POST'])
@login_required
def add_member():
    form = MemberForm()
    if form.validate_on_submit():
        try:
            member = Member(name=form.name.data)
            db.session.add(member)
            db.session.commit()
            flash('Membro adicionado com sucesso!', 'success')
            return redirect(url_for('list_members'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar membro: {e}', 'danger')
    return render_template('member_form.html', title='Adicionar Membro', form=form, legend='Novo Membro')

@app.route('/members/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)
    form = MemberForm(obj=member)
    if form.validate_on_submit():
        try:
            member.name = form.name.data
            db.session.commit()
            flash('Membro atualizado com sucesso!', 'success')
            return redirect(url_for('list_members'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar membro: {e}', 'danger')
    return render_template('member_form.html', title='Editar Membro', form=form, legend=f'Editar Membro: {member.name}')

@app.route('/members/<int:member_id>/delete', methods=['POST'])
@login_required
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    try:
        db.session.delete(member)
        db.session.commit()
        flash('Membro excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir membro: {e}. Pode estar associado a um projeto ou ata.', 'danger')
    return redirect(url_for('list_members'))


# Rotas CRUD de Projetos
@app.route('/projects')
@login_required
def list_projects():
    try:
        projects = Project.query.order_by(Project.name).all()
    except Exception as e:
        flash(f"Erro ao buscar projetos: {e}", "danger")
        projects = []
    return render_template('projects_list.html', title='Projetos', projects=projects)

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        flash("Arquivo de logo não encontrado.", "warning")
        return redirect(url_for('list_projects'))

@app.route('/projects/add', methods=['GET', 'POST'])
@login_required
def add_project():
    form = ProjectForm()
    form.set_member_choices()
    if form.validate_on_submit():
        filename = None
        filepath = None
        file_saved = False
        try:
            file = form.logo.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                file_saved = True
            elif file:
                 flash('Tipo de arquivo de logo não permitido.', 'warning')

            project = Project(name=form.name.data, logo_filename=filename)
            db.session.add(project)
            db.session.flush()

            if form.members.data:
                selected_members = Member.query.filter(Member.id.in_(form.members.data)).all()
                project.members = selected_members

            db.session.commit()
            flash('Projeto adicionado com sucesso!', 'success')
            return redirect(url_for('list_projects'))

        except Exception as e:
            db.session.rollback()
            if file_saved and filepath and os.path.exists(filepath):
                try: os.remove(filepath)
                except OSError as remove_err: app.logger.error(f"Erro ao remover logo: {remove_err}")
            flash(f'Erro ao adicionar projeto: {e}', 'danger')

    return render_template('project_form.html', title='Adicionar Projeto', form=form, legend='Novo Projeto')

@app.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    form = ProjectForm(obj=project)
    form.set_member_choices()

    if request.method == 'GET':
        form.members.data = [member.id for member in project.members]

    if form.validate_on_submit():
        old_filename = project.logo_filename
        new_filename = old_filename
        filepath = None
        file_saved = False
        try:
            file = form.logo.data
            if file and allowed_file(file.filename):
                new_filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                file.save(filepath)
                file_saved = True
            elif file:
                 flash('Tipo de arquivo de logo não permitido. Logo anterior mantido.', 'warning')
                 new_filename = old_filename

            project.name = form.name.data
            project.logo_filename = new_filename
            selected_members = Member.query.filter(Member.id.in_(form.members.data)).all()
            project.members = selected_members
            db.session.commit()

            if file_saved and old_filename and old_filename != new_filename:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                if os.path.exists(old_path):
                    try: os.remove(old_path)
                    except OSError as e: app.logger.error(f"Erro ao excluir logo antigo: {e}")

            flash('Projeto atualizado com sucesso!', 'success')
            return redirect(url_for('list_projects'))

        except Exception as e:
            db.session.rollback()
            if file_saved and filepath and os.path.exists(filepath):
                 try: os.remove(filepath)
                 except OSError as rem_e: app.logger.error(f"Erro ao remover logo: {rem_e}")
            flash(f'Erro ao atualizar projeto: {e}', 'danger')

    if request.method == 'POST' and not form.validate_on_submit():
         pass

    return render_template('project_form.html', title='Editar Projeto', form=form, legend=f'Editar Projeto: {project.name}', project=project)

@app.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    logo_filename = project.logo_filename
    try:
        db.session.delete(project)
        db.session.commit()
        if logo_filename:
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
            if os.path.exists(logo_path):
                 try: os.remove(logo_path)
                 except OSError as e: app.logger.error(f"Erro ao excluir logo: {e}")
        flash('Projeto excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir projeto: {e}.', 'danger')
    return redirect(url_for('list_projects'))


# --- Rotas para Atas ---

@app.route('/atas')
@login_required
def list_atas():
    """Lista todas as atas criadas, das mais recentes para as mais antigas."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10 # Itens por página
        pagination = Ata.query.order_by(Ata.date.desc(), Ata.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        atas = pagination.items
    except Exception as e:
        flash(f"Erro ao buscar atas: {e}", "danger")
        atas = []
        pagination = None
    return render_template('atas_list.html', title='Histórico de Atas', atas=atas, pagination=pagination)


@app.route('/atas/new', methods=['GET', 'POST'])
@login_required
def new_ata():
    """Exibe o formulário para criar uma nova ata e processa a submissão."""
    form = AtaForm()
    form.set_project_choices()
    # Lógica para popular membros será feita via JS ou no POST inválido

    if form.validate_on_submit():
        try:
            project = Project.query.get(form.project_id.data)
            if not project:
                 flash("Projeto selecionado inválido.", "danger")
                 form.set_project_choices() # Manter projetos
                 return render_template('ata_form.html', title='Criar Nova Ata', form=form, legend='Nova Ata')

            ata = Ata(
                project_id=project.id,
                date=form.date.data,
                time=form.time.data,
                format=form.format.data,
                location_or_platform=form.location_or_platform.data,
                discussion_text=form.discussion_text.data
            )
            db.session.add(ata)
            db.session.flush() # Obter ID da ata

            present_member_ids = set(form.attendees_present.data)
            all_project_members = project.members

            for member in all_project_members:
                is_present = member.id in present_member_ids
                attendee_record = AtaAttendee(
                    ata_id=ata.id,
                    member_id=member.id,
                    is_present=is_present
                )
                db.session.add(attendee_record)

            db.session.commit()
            flash(f'Ata para o projeto "{project.name}" criada com sucesso!', 'success')
            return redirect(url_for('list_atas'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar ata: {e}', 'danger')
            app.logger.error(f"Erro ao criar ata: {e}", exc_info=True)

    # Se GET ou se POST inválido
    if request.method == 'POST' and not form.validate_on_submit():
        # Tentar repopular membros baseado no projeto selecionado no form inválido
        selected_project_id = request.form.get('project_id', type=int)
        if selected_project_id:
            project = Project.query.get(selected_project_id)
            if project:
                form.set_attendee_choices(project.members)
            else:
                 form.set_attendee_choices([]) # Limpar se projeto inválido
        else:
             form.set_attendee_choices([]) # Limpar se nenhum projeto selecionado
        # Manter a seleção de presentes que o usuário fez
        form.attendees_present.data = [int(mid) for mid in request.form.getlist('attendees_present')]
    else:
        # Em GET, não popula membros por padrão (espera JS)
        form.set_attendee_choices([])


    return render_template('ata_form.html', title='Criar Nova Ata', form=form, legend='Nova Ata')


@app.route('/atas/<int:ata_id>/download')
@login_required
def download_ata(ata_id):
    """Busca uma ata pelo ID e gera/retorna o PDF para download."""
    ata = Ata.query.get_or_404(ata_id)
    try:
        # Substituir pelo gerador real quando estiver pronto
        # from utils.pdf_generator import generate_ata_pdf
        # pdf_buffer = generate_ata_pdf(ata)

        pdf_buffer = generate_ata_pdf_placeholder(ata_id) # Usando placeholder

        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        filename = f"ata_{ata.project.name.replace(' ', '_')}_{ata.date.strftime('%Y%m%d')}.pdf"
        # Usar aspas duplas no filename para nomes com espaços, etc.
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        flash(f"Erro ao gerar PDF da ata {ata_id}: {e}", "danger")
        app.logger.error(f"Erro PDF ata {ata_id}: {e}", exc_info=True)
        return redirect(url_for('list_atas'))

# Rota auxiliar para carregar membros de um projeto (para JS no formulário de ata)
@app.route('/api/project/<int:project_id>/members')
@login_required
def get_project_members(project_id):
    """Retorna os membros de um projeto específico em formato JSON."""
    project = Project.query.get(project_id) # Usar get() para retornar None se não achar
    if not project:
        # Retornar 404 ou uma lista vazia? 404 é mais correto para API REST.
        return jsonify({"error": "Project not found"}), 404

    # Ordenar membros por nome para consistência
    members_list = sorted(project.members, key=lambda m: m.name)
    members_data = [{"id": m.id, "name": m.name} for m in members_list]
    return jsonify({"members": members_data})


# --- Execução da Aplicação ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')