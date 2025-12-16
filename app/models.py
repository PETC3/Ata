# seu_projeto_flask/app/models.py

from datetime import datetime
import enum
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Enum as SQLAlchemyEnum

# Importa a instância 'db' e 'login_manager' criadas em app/__init__.py
from . import db, login_manager

# --- Tabelas de Associação (Muitos-para-Muitos) ---

# Tabela para relacionar Projetos e Membros (Sem alteração)
project_members = db.Table('project_members',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('member_id', db.Integer, db.ForeignKey('member.id'), primary_key=True)
)

# Tabela para relacionar Atas e Membros Presentes (Sem alteração - continua a registrar a presença)
ata_present_members = db.Table('ata_present_members',
    db.Column('ata_id', db.Integer, db.ForeignKey('ata.id'), primary_key=True),
    db.Column('member_id', db.Integer, db.ForeignKey('member.id'), primary_key=True)
)

# --------------------------------------------------------------------------
# NOVA CLASSE DE ASSOCIAÇÃO COM DADOS: Armazenará SOMENTE as Justificativas dos AUSENTES
# --------------------------------------------------------------------------
class AtaAbsentJustification(db.Model):
    """Armazena a justificativa de um membro para uma ausência específica."""
    __tablename__ = 'ata_absent_justification'

    # Chaves Primárias
    ata_id = db.Column(db.Integer, db.ForeignKey('ata.id'), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), primary_key=True)
    
    # Campo para armazenar a justificativa (Obrigatório se o registro existir nesta tabela)
    justification = db.Column(db.Text, nullable=False) 

    # --- Relacionamentos de volta ---
    ata = db.relationship("Ata", back_populates="absent_justifications")
    member = db.relationship("Member") # O membro que justificou a ausência

# --------------------------------------------------------------------------
# Fim da Nova Classe
# --------------------------------------------------------------------------


# --- Modelos Principais ---

@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário pelo ID."""
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """Modelo para o usuário administrador (único neste caso)."""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Member(db.Model):
    """Modelo para os membros que podem participar das reuniões."""
    __tablename__ = 'member'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # --- RELACIONAMENTOS COM back_populates ---
    # Relacionamento com Projetos (Muitos-para-Muitos)
    projects = db.relationship(
        'Project',
        secondary=project_members,
        lazy='dynamic',
        back_populates='members'
    )

    # Relacionamento com Atas onde esteve presente (Muitos-para-Muitos - Sem alteração)
    attended_meetings = db.relationship(
        'Ata',
        secondary=ata_present_members,
        lazy='dynamic',
        back_populates='present_members'
    )
    # --- FIM DOS RELACIONAMENTOS ---

    def __repr__(self):
        status = "ativo" if self.is_active else "inativo"
        return f'<Member {self.name} ({status})>'

class Project(db.Model):
    """Modelo para os projetos."""
    __tablename__ = 'project'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    logo = db.Column(db.String(200), nullable=True)

    # --- RELACIONAMENTOS COM back_populates ---
    # Relacionamento com Membros (Muitos-para-Muitos - com sua correção anterior)
    members = db.relationship(
        'Member',
        secondary=project_members,
        lazy='selectin',
        back_populates='projects'
    )

    # Relacionamento com Atas (Um-para-Muitos)
    atas = db.relationship(
        'Ata',
        lazy='dynamic',
        cascade="all, delete-orphan",
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
        back_populates='atas'
    )

    # Relacionamento com Membros Presentes (Muitos-para-Muitos - com sua correção anterior)
    present_members = db.relationship(
        'Member',
        secondary=ata_present_members,
        lazy='selectin',
        back_populates='attended_meetings'
    )

    # >>> NOVO RELACIONAMENTO: Justificativas de Ausência <<<
    absent_justifications = db.relationship(
        'AtaAbsentJustification',
        back_populates='ata',
        lazy='selectin',
        cascade="all, delete-orphan",
    )
    # --- FIM DOS RELACIONAMENTOS ---

    @property
    def absent_members(self):
        """
        Retorna uma lista de objetos Member que estavam ausentes (Membros do Projeto - Membros Presentes).
        """
        if not self.project or not hasattr(self.project, 'members'):
            return []
        
        # Pega IDs de todos os membros já associados ao projeto
        all_proj_member_ids = {m.id for m in self.project.members}
        # Pega IDs dos membros presentes nesta ata
        present_member_ids = {m.id for m in self.present_members}

        absent_member_ids = all_proj_member_ids - present_member_ids

        if absent_member_ids:
            # Retorna os objetos Member (ativos ou inativos) correspondentes
            return list(Member.query.filter(Member.id.in_(absent_member_ids)).all())
        else:
            return []
            
    # >>> NOVA PROPRIEDADE: Obtém as justificativas de ausência como um dicionário
    @property
    def absent_justifications_dict(self):
        """Retorna um dicionário {member_id: justification} para ausentes justificados."""
        return {
            rec.member_id: rec.justification
            for rec in self.absent_justifications
        }

    def __repr__(self):
         project_name = self.project.name if self.project else 'N/A'
         meeting_date_str = self.meeting_datetime.strftime('%Y-%m-%d %H:%M') if self.meeting_datetime else 'N/A'
         return f"<Ata Projeto '{project_name}' - {meeting_date_str}>"