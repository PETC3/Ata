# seu_projeto_flask/app/routes.py

import os
import io
from flask import (render_template, flash, redirect, url_for, request,
                   current_app, send_file, abort, jsonify, Response)
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
# Importações corrigidas para parse de URL
from urllib.parse import urlparse, urljoin
# Importação necessária para checar tipo de arquivo uploadado
from werkzeug.datastructures import FileStorage

# Importações locais da aplicação
from . import db # Importa a instância db de __init__.py
# Importa os modelos
from .models import User, Member, Project, Ata, LocationTypeEnum
# Importa os formulários e as funções factory necessárias
from .forms import (LoginForm, MemberForm, ProjectForm, AtaForm,
                    get_active_members, get_active_projects)
# Importa a função de geração de PDF
from .utils import generate_ata_pdf

# --- Rotas de Autenticação ---
@current_app.route('/login', methods=['GET', 'POST'])
def login():
    """Rota para login do usuário."""
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('login'))

        login_user(user)
        flash('Login realizado com sucesso!', 'success')

        # Redirecionamento seguro corrigido
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('home')
        return redirect(next_page)

    return render_template('login.html', title='Entrar', form=form)

@current_app.route('/logout')
@login_required
def logout():
    """Rota para logout do usuário."""
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

# --- Rotas Principais da Aplicação (Protegidas) ---

@current_app.route('/')
@current_app.route('/home')
@login_required
def home():
    """Página inicial da área logada."""
    recent_atas = Ata.query.order_by(Ata.meeting_datetime.desc()).limit(5).all()
    return render_template('home.html', title='Início', recent_atas=recent_atas)

# --- CRUD de Membros ---

# Lista apenas membros ativos por padrão.
@current_app.route('/members')
@login_required
def list_members():
    """Lista os membros ativos."""
    members = Member.query.filter_by(is_active=True).order_by(Member.name).all()
    return render_template('members/list.html', title='Membros Ativos', members=members)

# Rota para adicionar membro (cria como ativo por padrão).
@current_app.route('/members/add', methods=['GET', 'POST'])
@login_required
def add_member():
    """Adiciona um novo membro (sempre como ativo)."""
    form = MemberForm()
    if form.validate_on_submit():
        member = Member(name=form.name.data) # is_active=True é o default do modelo
        db.session.add(member)
        try:
            db.session.commit()
            flash(f'Membro "{member.name}" adicionado com sucesso!', 'success')
            return redirect(url_for('list_members'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar membro: {e}', 'danger')
            current_app.logger.error(f"Erro DB ao adicionar membro: {e}")
    return render_template('members/form.html', title='Adicionar Membro', form=form, action='Adicionar')

# Rota para editar o nome de um membro (ativo ou inativo).
@current_app.route('/members/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_member(id):
    """Edita o nome de um membro existente."""
    member = Member.query.get_or_404(id) # Pega o membro independentemente do status
    form = MemberForm(obj=member) # Popula o form com o nome atual
    form._original_member = member # Para a validação de nome único

    if form.validate_on_submit():
        member.name = form.name.data # Atualiza apenas o nome
        try:
            db.session.commit()
            flash(f'Membro "{member.name}" atualizado com sucesso!', 'success')
            # Redireciona para a lista de membros ATIVOS
            return redirect(url_for('list_members'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar membro: {e}', 'danger')
            current_app.logger.error(f"Erro DB ao editar membro {id}: {e}")

    status = "(Ativo)" if member.is_active else "(Inativo)"
    return render_template('members/form.html', title=f'Editar Membro: {member.name} {status}', form=form, action='Salvar Alterações', member=member)

# ATUALIZADO: Rota para DESATIVAR um membro (Soft Delete) - Correção para lazy='dynamic'
@current_app.route('/members/delete/<int:id>', methods=['POST']) # Mantido nome 'delete' para URL
@login_required
def delete_member(id):
    """Marca um membro como inativo (soft delete) e o remove dos projetos associados."""
    member = Member.query.get_or_404(id)
    member_name = member.name

    if not member.is_active: # Verifica se já está inativo
        flash(f'Membro "{member_name}" já está inativo.', 'info')
        return redirect(url_for('list_members'))

    try:
        # Marca como inativo
        member.is_active = False
        # --- CORREÇÃO AQUI para lazy='dynamic' ---
        # Remove de todos os projetos associados atribuindo uma lista vazia
        member.projects = []
        # --- FIM DA CORREÇÃO ---
        # NÃO limpa member.attended_meetings para manter o histórico

        # Salva as alterações no banco (is_active = False e remoção de project_members)
        db.session.commit()
        flash(f'Membro "{member_name}" desativado com sucesso e removido dos projetos!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao desativar membro: {e}', 'danger')
        current_app.logger.error(f"Erro DB ao desativar membro {id}: {e}")

    return redirect(url_for('list_members'))


# --- CRUD de Projetos ---
@current_app.route('/projects')
@login_required
def list_projects():
    """Lista todos os projetos."""
    projects = Project.query.order_by(Project.name).all()
    return render_template('projects/list.html', title='Projetos', projects=projects)

def save_logo(form_logo_data):
    """Salva o arquivo de logo e retorna o nome do arquivo."""
    if not isinstance(form_logo_data, FileStorage) or not form_logo_data.filename:
        return None
    filename = secure_filename(form_logo_data.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    try:
        form_logo_data.save(filepath)
        return filename
    except Exception as e:
        current_app.logger.error(f"Erro ao salvar logo {filename}: {e}")
        flash(f"Erro ao salvar o arquivo de logo: {e}", "danger")
        return None

def delete_logo(filename):
    """Deleta o arquivo de logo do servidor."""
    if not filename:
        return
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            current_app.logger.info(f"Logo {filename} deletado.")
    except Exception as e:
        current_app.logger.error(f"Erro ao deletar logo {filename}: {e}")

@current_app.route('/projects/add', methods=['GET', 'POST'])
@login_required
def add_project():
    """Adiciona um novo projeto."""
    form = ProjectForm()
    if form.validate_on_submit():
        filename = None
        if form.logo.data and isinstance(form.logo.data, FileStorage):
             filename = save_logo(form.logo.data)
        project = Project(name=form.name.data, logo=filename)
        project.members = form.members.data # Associa membros ativos selecionados
        db.session.add(project)
        try:
            db.session.commit()
            flash(f'Projeto "{project.name}" adicionado com sucesso!', 'success')
            return redirect(url_for('list_projects'))
        except Exception as e:
            db.session.rollback()
            delete_logo(filename)
            flash(f'Erro ao adicionar projeto: {e}', 'danger')
            current_app.logger.error(f"Erro DB ao adicionar projeto: {e}")
    return render_template('projects/form.html', title='Adicionar Projeto', form=form, action='Adicionar')


@current_app.route('/projects/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    """Edita um projeto existente."""
    project = Project.query.get_or_404(id)
    form = ProjectForm(obj=project)
    form._original_project = project

    if form.validate_on_submit():
        old_logo = project.logo
        new_filename = old_logo
        if form.logo.data and isinstance(form.logo.data, FileStorage):
            saved_fn = save_logo(form.logo.data)
            if saved_fn:
                new_filename = saved_fn
                if old_logo and old_logo != new_filename:
                    delete_logo(old_logo)
        elif 'logo-clear' in request.form:
             delete_logo(old_logo)
             new_filename = None
        project.name = form.name.data
        project.logo = new_filename
        project.members = form.members.data # Associa/Desassocia membros ATIVOS selecionados
        try:
            db.session.commit()
            flash(f'Projeto "{project.name}" atualizado com sucesso!', 'success')
            return redirect(url_for('list_projects'))
        except Exception as e:
            db.session.rollback()
            if new_filename and new_filename != old_logo and isinstance(form.logo.data, FileStorage):
                 delete_logo(new_filename)
            flash(f'Erro ao editar projeto: {e}', 'danger')
            current_app.logger.error(f"Erro DB ao editar projeto {id}: {e}")

    elif request.method == 'GET':
         # Pré-seleciona apenas os membros ATIVOS que JÁ estão associados ao projeto
         form.members.data = project.active_members

    return render_template('projects/form.html', title='Editar Projeto', form=form, action='Salvar Alterações', project=project)

@current_app.route('/projects/delete/<int:id>', methods=['POST'])
@login_required
def delete_project(id):
    """Deleta um projeto."""
    project = Project.query.get_or_404(id)
    project_name = project.name
    logo_filename = project.logo
    try:
        # A exclusão do projeto deleta as atas associadas devido ao cascade no modelo
        db.session.delete(project)
        db.session.commit()
        delete_logo(logo_filename)
        flash(f'Projeto "{project_name}" e suas atas associadas foram excluídos com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir projeto: {e}', 'danger')
        current_app.logger.error(f"Erro DB ao excluir projeto {id}: {e}")
    return redirect(url_for('list_projects'))


# --- Gestão de Atas ---
@current_app.route('/atas/create', defaults={'project_id': None}, methods=['GET', 'POST'])
@current_app.route('/atas/create/for/<int:project_id>', methods=['GET', 'POST'])
@login_required
def create_ata(project_id):
    """Cria uma nova ata, opcionalmente pré-selecionando um projeto."""
    form = AtaForm()
    project = None
    if project_id:
        project = Project.query.get_or_404(project_id)
        if request.method == 'GET':
            form.project.data = project

    project_members = [] # Lista de membros ativos do projeto para o JS
    selected_project_in_form = form.project.data
    if request.method == 'POST' and form.project.validate(form):
         selected_project_in_form = form.project.data
    elif project:
         selected_project_in_form = project

    if selected_project_in_form:
        project_members = selected_project_in_form.active_members

    if form.validate_on_submit():
        ata = Ata(
            project=form.project.data,
            meeting_datetime=form.meeting_datetime.data,
            notes=form.notes.data
        )
        # Associa os membros ATIVOS selecionados como presentes
        ata.present_members = form.present_members.data
        db.session.add(ata)
        try:
            db.session.commit()
            flash('Ata criada com sucesso!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar ata: {e}', 'danger')
            current_app.logger.error(f"Erro DB ao criar ata: {e}")

    return render_template('atas/create_form.html',
                           title='Criar Nova Ata',
                           form=form,
                           project_members=project_members, # Passa membros ativos para o JS
                           selected_project=project)

@current_app.route('/atas/download/<int:id>')
@login_required
def download_ata_pdf(id):
    """Gera e baixa o PDF de uma ata específica."""
    ata = Ata.query.get_or_404(id)
    try:
        pdf_data = generate_ata_pdf(ata)
        filename = f"Ata_{ata.project.name.replace(' ', '_')}_{ata.meeting_datetime.strftime('%Y%m%d')}.pdf"
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar PDF para ata {id}: {e}")
        flash(f"Ocorreu um erro ao gerar o PDF da ata: {e}", "danger")
        return redirect(url_for('home'))

@current_app.route('/atas/delete/<int:id>', methods=['POST'])
@login_required
def delete_ata(id):
    """Deleta uma ata específica."""
    ata = Ata.query.get_or_404(id)
    try:
        db.session.delete(ata)
        db.session.commit()
        flash('Ata excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir a ata: {e}', 'danger')
        current_app.logger.error(f"Erro DB ao excluir ata {id}: {e}")
    return redirect(url_for('home'))


# --- Rota API Auxiliar ---
@current_app.route('/api/project/<int:project_id>/members')
@login_required
def api_get_project_members(project_id):
    """Retorna os membros ATIVOS de um projeto específico em formato JSON."""
    project = Project.query.get_or_404(project_id)
    active_project_members = project.active_members
    members_data = [{'id': member.id, 'name': member.name} for member in active_project_members]
    return jsonify(members=members_data)

# --- Handlers de Erro ---
@current_app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html', title='Página Não Encontrada'), 404

@current_app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    current_app.logger.error(f"Erro interno do servidor: {error}", exc_info=True)
    return render_template('errors/500.html', title='Erro Interno'), 500

