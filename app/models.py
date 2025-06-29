# seu_projeto_flask/app/models.py

from datetime import datetime
import enum
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Enum as SQLAlchemyEnum # Renomeado para evitar conflito

# Importa a instância 'db' e 'login_manager' criadas em app/__init__.py
from . import db, login_manager

# --- Tabelas de Associação (Muitos-para-Muitos) ---

# Tabela para relacionar Projetos e Membros
project_members = db.Table('project_members',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('member_id', db.Integer, db.ForeignKey('member.id'), primary_key=True)
)

# Tabela para relacionar Atas e Membros Presentes
ata_present_members = db.Table('ata_present_members',
    db.Column('ata_id', db.Integer, db.ForeignKey('ata.id'), primary_key=True),
    # Mantém a referência ao member.id mesmo se o membro for desativado
    # ForeignKey sem ON DELETE CASCADE ou SET NULL para preservar o histórico
    db.Column('member_id', db.Integer, db.ForeignKey('member.id'), primary_key=True)
)

# --- Modelos Principais ---

# Função necessária pelo Flask-Login para carregar um usuário a partir do ID armazenado na sessão.
@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário pelo ID."""
    # Busca na tabela User pelo ID primário
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """Modelo para o usuário administrador (único neste caso)."""
    __tablename__ = 'user' # Nome explícito da tabela

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # Hash pode ser longo

    def set_password(self, password):
        """Gera o hash da senha e armazena."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        # Representação do objeto para debugging
        return f'<User {self.username}>'

class Member(db.Model):
    """Modelo para os membros que podem participar das reuniões."""
    __tablename__ = 'member'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    # Campo para controle de soft delete
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # --- RELACIONAMENTOS COM back_populates ---
    # Relacionamento com Projetos (Muitos-para-Muitos)
    projects = db.relationship(
        'Project',
        secondary=project_members,
        lazy='dynamic', # Permite filtrar depois (ex: member.projects.filter(...))
        # Aponta para o atributo 'members' na classe Project
        back_populates='members'
    )

    # Relacionamento com Atas onde esteve presente (Muitos-para-Muitos)
    attended_meetings = db.relationship(
        'Ata',
        secondary=ata_present_members,
        lazy='dynamic',
        # Aponta para o atributo 'present_members' na classe Ata
        back_populates='present_members'
    )
    # --- FIM DOS RELACIONAMENTOS ---

    def __repr__(self):
        # Inclui status ativo/inativo na representação
        status = "ativo" if self.is_active else "inativo"
        return f'<Member {self.name} ({status})>'

class Project(db.Model):
    """Modelo para os projetos."""
    __tablename__ = 'project'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    logo = db.Column(db.String(200), nullable=True) # Nome do arquivo do logo

    # --- RELACIONAMENTOS COM back_populates ---
    # Relacionamento com Membros (Muitos-para-Muitos)
    members = db.relationship(
        'Member',
        secondary=project_members,
        lazy='subquery', # Carrega membros junto com o projeto
        # Aponta para o atributo 'projects' na classe Member
        back_populates='projects'
    )

    # Relacionamento com Atas (Um-para-Muitos)
    atas = db.relationship(
        'Ata',
        lazy='dynamic', # Permite filtrar atas depois (project.atas.filter(...))
        cascade="all, delete-orphan", # Deleta atas se o projeto for deletado
        # Aponta para o atributo 'project' na classe Ata
        back_populates='project'
    )
    # --- FIM DOS RELACIONAMENTOS ---

    @property
    def active_members(self):
        return sorted(
        (m for m in self.members if m.is_active),
        key=lambda m: m.name.lower()
    )

    def __repr__(self):
        return f'<Project {self.name}>'

# Enum para os tipos de local da reunião
class LocationTypeEnum(enum.Enum):
    presencial = 'Presencial'
    online = 'Online'
    hibrido = 'Híbrido'

class Ata(db.Model):
    """Modelo para as Atas de Reunião."""
    __tablename__ = 'ata'

    id = db.Column(db.Integer, primary_key=True)
    meeting_datetime = db.Column(db.DateTime, nullable=False)
    location_type = db.Column(SQLAlchemyEnum(LocationTypeEnum, name="location_type_enum"), nullable=True)
    location_details = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- RELACIONAMENTOS COM back_populates ---
    # Chave estrangeira para o projeto
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    # Relacionamento com Projeto (Muitos-para-Um)
    project = db.relationship(
        'Project',
        # Aponta para o atributo 'atas' na classe Project
        back_populates='atas'
    )

    # Relacionamento com Membros Presentes (Muitos-para-Muitos)
    present_members = db.relationship(
        'Member',
        secondary=ata_present_members,
        lazy='subquery', # Carrega presentes junto com a ata
        # Aponta para o atributo 'attended_meetings' na classe Member
        back_populates='attended_meetings'
    )
    # --- FIM DOS RELACIONAMENTOS ---

    @property
    def absent_members(self):
        """
        Retorna uma lista de objetos Member que estavam associados ao projeto
        mas não foram marcados como presentes nesta ata específica.
        Nota: Pode incluir membros desativados após a ata.
        """
        if not self.project or not hasattr(self.project, 'members'):
            return []
        # Pega IDs de todos os membros já associados ao projeto
        all_proj_member_ids = {m.id for m in self.project.members} # Usa o relacionamento principal
        # Pega IDs dos membros presentes nesta ata
        present_member_ids = {m.id for m in self.present_members}

        absent_member_ids = all_proj_member_ids - present_member_ids

        if absent_member_ids:
            # Retorna os objetos Member (ativos ou inativos) correspondentes
            return list(Member.query.filter(Member.id.in_(absent_member_ids)).all())
        else:
            return []

    def __repr__(self):
         project_name = self.project.name if self.project else 'N/A'
         meeting_date_str = self.meeting_datetime.strftime('%Y-%m-%d %H:%M') if self.meeting_datetime else 'N/A'
         return f"<Ata Projeto '{project_name}' - {meeting_date_str}>"