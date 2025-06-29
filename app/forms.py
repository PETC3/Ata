# seu_projeto_flask/app/forms.py

from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, TextAreaField,
                     SelectField, DateTimeField, HiddenField, SelectMultipleField)
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from flask_wtf.file import FileField, FileAllowed # Para upload de logo
# Importa campos específicos para lidar com queries do SQLAlchemy
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
# Importa widgets para customizar a aparência (ex: checkboxes)
from wtforms import widgets

# Importa os modelos necessários para as queries dos campos
from .models import Project, Member, User
from datetime import datetime

# --- Funções Query Factory Atualizadas ---

def get_active_projects():
    """Retorna uma query com todos os projetos ativos, ordenados por nome."""
    # Assumindo que não há status 'ativo/inativo' para projetos por enquanto
    return Project.query.order_by(Project.name)

# Busca apenas membros ATIVOS
def get_active_members():
    """Retorna uma query com todos os membros ATIVOS, ordenados por nome."""
    return Member.query.filter_by(is_active=True).order_by(Member.name)

# --- Formulários ---

class LoginForm(FlaskForm):
    """Formulário de Login."""
    username = StringField('Usuário', validators=[DataRequired("Nome de usuário é obrigatório.")])
    password = PasswordField('Senha', validators=[DataRequired("Senha é obrigatória.")])
    submit = SubmitField('Entrar')

class MemberForm(FlaskForm):
    """Formulário para adicionar ou editar Membros (apenas o nome)."""
    name = StringField('Nome do Membro', validators=[
        DataRequired("Nome é obrigatório."),
        Length(min=2, max=100, message="Nome deve ter entre 2 e 100 caracteres.")
    ])
    # O campo 'is_active' não é gerenciado por este formulário.
    submit = SubmitField('Salvar Membro')

    # Validação customizada para garantir nome único entre membros ATIVOS
    def validate_name(self, name):
        # Obtém o membro original que está sendo editado (se houver)
        original_member = getattr(self, '_original_member', None)
        # Busca por outros membros ATIVOS com o mesmo nome
        query = Member.query.filter(Member.name == name.data, Member.is_active == True)
        # Exclui o próprio membro da verificação se estiver editando
        if original_member:
            query = query.filter(Member.id != original_member.id)
        existing_member = query.first()
        if existing_member:
            raise ValidationError('Já existe um membro ativo com este nome. Por favor, escolha outro.')


class ProjectForm(FlaskForm):
    """Formulário para adicionar ou editar Projetos."""
    name = StringField('Nome do Projeto', validators=[
        DataRequired("Nome do projeto é obrigatório."),
        Length(min=3, max=150)
    ])
    logo = FileField('Logo do Projeto (Opcional)', validators=[
        Optional(), # O campo é opcional
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Apenas imagens (jpg, png, jpeg, gif) são permitidas!')
    ])
    # Usa get_active_members para as opções
    # O usuário só pode associar membros ativos a um projeto
    members = QuerySelectMultipleField(
        'Membros Associados ao Projeto (Ativos)', # Label atualizado
        query_factory=get_active_members, # Usa a factory que filtra por ativos
        get_label='name',
        widget=widgets.ListWidget(prefix_label=False),
        option_widget=widgets.CheckboxInput()
    )
    submit = SubmitField('Salvar Projeto')

    # Validação para nome único de projeto (sem alterações)
    def validate_name(self, name):
        original_project = getattr(self, '_original_project', None)
        query = Project.query.filter(Project.name == name.data)
        if original_project:
            query = query.filter(Project.id != original_project.id)
        existing_project = query.first()
        if existing_project:
            raise ValidationError('Já existe um projeto com este nome.')

class AtaForm(FlaskForm):
    """Formulário para criar ou editar Atas."""
    project = QuerySelectField(
        'Projeto da Reunião',
        query_factory=get_active_projects,
        get_label='name',
        allow_blank=False,
        validators=[DataRequired("É necessário selecionar um projeto.")]
    )
    meeting_datetime = DateTimeField(  
        'Data e Hora da Reunião',
        format='%Y-%m-%dT%H:%M',
        default=datetime.now,
        validators=[DataRequired("Data e hora são obrigatórias.")]
    )

    # Usa get_active_members para as opções
    # O usuário só pode marcar membros ativos como presentes em uma nova ata
    present_members = QuerySelectMultipleField(
        'Membros Presentes na Reunião (Ativos)', # Label atualizado
        query_factory=get_active_members, # Usa a factory que filtra por ativos
        get_label='name',
        widget=widgets.ListWidget(prefix_label=False),
        option_widget=widgets.CheckboxInput()
    )
    notes = TextAreaField('Assuntos Tratados / Deliberações', validators=[
        DataRequired("É necessário registrar o que foi tratado."),
        Length(min=10)
    ])
    submit = SubmitField('Salvar Ata')

    # Validação para garantir que os membros selecionados como presentes
    # realmente pertencem ao projeto selecionado.
    def validate_present_members(self, present_members_field):
        if self.project.data: # Se um projeto foi selecionado no formulário
            # --- LINHA CORRIGIDA ---
            # Pega os IDs de TODOS os membros associados ao projeto (ativos ou inativos)
            # Usando o atributo de relacionamento 'members' do objeto Project
            project_member_ids = {member.id for member in self.project.data.members}
            # --- FIM DA CORREÇÃO ---

            # Pega os IDs dos membros selecionados no formulário (que só podem ser ativos)
            selected_member_ids = {member.id for member in present_members_field.data}

            # Verifica se algum ID selecionado NÃO está na lista de IDs associados ao projeto
            invalid_members = selected_member_ids - project_member_ids
            if invalid_members:
                # Busca os nomes dos membros inválidos para a mensagem de erro
                invalid_member_objects = Member.query.filter(Member.id.in_(invalid_members)).all()
                invalid_member_names = [m.name for m in invalid_member_objects]
                raise ValidationError(f"Os seguintes membros selecionados não pertencem ao projeto '{self.project.data.name}': {', '.join(invalid_member_names)}")