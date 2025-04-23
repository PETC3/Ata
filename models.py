# models.py
from datetime import datetime
from sqlalchemy import MetaData
from flask_login import UserMixin # <--- IMPORTAÇÃO CORRETA
from app import db # Importar 'db' de app.py

# --- Convenção de Nomenclatura ---
# Define um padrão para nomear índices, chaves únicas, chaves estrangeiras, etc.
# Ajuda Alembic e SQLAlchemy a gerenciar constraints, especialmente em SQLite com batch mode.
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
# Assumindo que db.metadata já tem a convenção aplicada em app.py
metadata = db.metadata


# --- Tabela de Associação (Muitos-para-Muitos) ---
# Definindo a tabela explicitamente com o metadata que contém a convenção.
project_members = db.Table('project_members',
    metadata, # Passa o metadata como segundo argumento
    db.Column('project_id', db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), primary_key=True),
    db.Column('member_id', db.Integer, db.ForeignKey('member.id', ondelete='CASCADE'), primary_key=True)
    # Os nomes das ForeignKeys (fk_...) serão gerados automaticamente pela convenção.
)

# --- Modelos Principais ---

class User(db.Model, UserMixin): # <--- USAR UserMixin importado diretamente
    """Modelo para o usuário do sistema (login)."""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    # Armazena o HASH da senha, nunca a senha original
    password_hash = db.Column(db.String(256), nullable=False)

    # Métodos exigidos ou úteis para Flask-Login e segurança
    def set_password(self, password):
        """Cria um hash seguro da senha e o armazena."""
        # Importar aqui ou no topo, dependendo da preferência/necessidade
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        from werkzeug.security import check_password_hash
        # Retorna True se a senha confere, False caso contrário
        return check_password_hash(self.password_hash, password)

    # O UserMixin já fornece is_authenticated, is_active, is_anonymous, get_id()

    def __repr__(self):
        # Representação textual do objeto, útil para debugging
        return f'<User {self.username}>'


class Member(db.Model):
    """Modelo para os membros que podem participar das reuniões."""
    __tablename__ = 'member'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)

    # Relacionamento reverso 'projects' é criado pelo backref em Project.members.
    # Permite acessar membro.projects.

    # Relacionamento reverso com AtaAttendee.
    # 'lazy=dynamic' retorna um objeto query que pode ser filtrado depois.
    # Ex: member.attendance_records.filter_by(is_present=True).all()
    attendance_records = db.relationship('AtaAttendee', backref='member', lazy='dynamic')


    def __repr__(self):
        return f'<Member {self.id}: {self.name}>'


class Project(db.Model):
    """Modelo para os projetos, aos quais as atas e membros estão associados."""
    __tablename__ = 'project'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    # Armazena apenas o nome do arquivo. O caminho base fica em app.config['UPLOAD_FOLDER']
    logo_filename = db.Column(db.String(255), nullable=True) # Permite logos opcionais

    # Relacionamento Muitos-para-Muitos com Membros, usando a tabela 'project_members'
    members = db.relationship('Member',
                              secondary=project_members, # Usa a tabela definida acima
                              # 'subquery' carrega os membros relacionados eficientemente
                              lazy='subquery',
                              # Cria o atributo 'projects' no modelo Member
                              backref=db.backref('projects', lazy=True))

    # Relacionamento Um-para-Muitos com Atas.
    # Se um projeto for deletado, todas as suas atas associadas também serão (cascade).
    atas = db.relationship('Ata', backref='project', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Project {self.id}: {self.name}>'


# --- Modelos para Atas ---

class Ata(db.Model):
    """Modelo para armazenar os dados de uma ata de reunião."""
    __tablename__ = 'ata'

    id = db.Column(db.Integer, primary_key=True)
    # Chave estrangeira para o projeto. Se o projeto for deletado, a ata também será (cascade).
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=True) # Horário pode ser opcional
    format = db.Column(db.String(50), nullable=False) # Ex: 'Presencial', 'Online', 'Misto'
    location_or_platform = db.Column(db.String(200), nullable=True) # Ex: 'Sala X' ou 'Google Meet'
    discussion_text = db.Column(db.Text, nullable=False) # O conteúdo principal da ata
    # Data/Hora em que o registro foi criado no banco de dados
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relacionamento com a tabela de associação AtaAttendee.
    # Se uma ata for deletada, seus registros de presença também serão (cascade).
    attendee_records = db.relationship('AtaAttendee', backref='ata', lazy='subquery', cascade="all, delete-orphan")

    @property
    def present_members(self):
        """Retorna uma lista de objetos Member que estavam presentes."""
        return [record.member for record in self.attendee_records if record.is_present]

    @property
    def absent_members(self):
        """Retorna uma lista de objetos Member do projeto que estavam ausentes."""
        if not self.project: # Segurança caso o projeto não esteja carregado
            return []
        present_member_ids = {record.member_id for record in self.attendee_records if record.is_present}
        # Compara todos os membros do projeto com os que estavam presentes
        return [member for member in self.project.members if member.id not in present_member_ids]


    def __repr__(self):
        return f'<Ata {self.id} - Projeto {self.project_id} em {self.date}>'


class AtaAttendee(db.Model):
    """Tabela de associação para registrar presença (ou ausência) de um Membro em uma Ata."""
    __tablename__ = 'ata_attendee'

    # Chave primária composta para garantir unicidade
    ata_id = db.Column(db.Integer, db.ForeignKey('ata.id', ondelete='CASCADE'), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id', ondelete='CASCADE'), primary_key=True)

    # Indica explicitamente se o membro estava presente nesta ata específica.
    is_present = db.Column(db.Boolean, nullable=False, default=False)

    # Os relacionamentos reversos 'ata' e 'member' são criados pelos backrefs

    def __repr__(self):
        status = "Presente" if self.is_present else "Ausente"
        # Acesso aos objetos relacionados via backref para um repr mais informativo
        member_name = self.member.name if self.member else 'Desconhecido'
        return f'<AtaAttendee Ata:{self.ata_id} Membro:{member_name} ({status})>'