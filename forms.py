# forms.py
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField,
                     SelectMultipleField, widgets, TextAreaField, SelectField,
                     DateField, TimeField) # BooleanField não é necessário aqui diretamente
# Importar validadores
from wtforms.validators import DataRequired, Length, Optional, ValidationError
# Importar campos e validadores de arquivo
from flask_wtf.file import FileField, FileAllowed

# Defina ALLOWED_EXTENSIONS aqui para evitar importação circular de app.py
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


class LoginForm(FlaskForm):
    """Formulário para autenticação do usuário."""
    username = StringField('Usuário',
                           render_kw={"placeholder": "Digite seu usuário"},
                           validators=[DataRequired(message="Nome de usuário é obrigatório.")])
    password = PasswordField('Senha',
                             render_kw={"placeholder": "Digite sua senha"},
                             validators=[DataRequired(message="Senha é obrigatória.")])
    submit = SubmitField('Entrar')


class MemberForm(FlaskForm):
    """Formulário para adicionar ou editar membros."""
    name = StringField('Nome Completo do Membro',
                       render_kw={"placeholder": "Ex: Fulano de Tal"},
                       validators=[
                           DataRequired(message="Nome é obrigatório."),
                           Length(min=2, max=100, message="Nome deve ter entre 2 e 100 caracteres.")
                       ])
    submit = SubmitField('Salvar Membro')


# Widget customizado para renderizar SelectMultipleField como checkboxes
class MultiCheckboxField(SelectMultipleField):
    """
    Um campo SelectMultipleField que renderiza como uma lista de checkboxes.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class ProjectForm(FlaskForm):
    """Formulário para adicionar ou editar projetos."""
    name = StringField('Nome do Projeto',
                       render_kw={"placeholder": "Ex: Projeto Alpha"},
                       validators=[
                           DataRequired(message="Nome do projeto é obrigatório."),
                           Length(min=3, max=150, message="Nome deve ter entre 3 e 150 caracteres.")
                       ])
    logo = FileField('Logo do Projeto (Opcional)',
                     validators=[
                         Optional(),
                         FileAllowed(ALLOWED_EXTENSIONS, 'Apenas imagens (png, jpg, jpeg, gif) são permitidas!')
                     ])
    members = MultiCheckboxField('Membros Associados (Opcional)',
                                 coerce=int,
                                 validators=[Optional()])
    submit = SubmitField('Salvar Projeto')

    def set_member_choices(self):
        """Busca membros no DB e define as opções para o campo 'members'."""
        from models import Member # Import local
        try:
            self.members.choices = [(m.id, m.name) for m in Member.query.order_by(Member.name).all()]
        except Exception as e:
            print(f"Erro ao buscar membros para choices: {e}")
            self.members.choices = []


# --- Formulário para Atas (AGORA ATIVO) ---

class AtaForm(FlaskForm):
    """Formulário para criar ou editar atas."""
    # Campo Select para escolher o projeto. 'coerce=int' garante que o valor seja tratado como inteiro.
    project_id = SelectField('Projeto*',
                             coerce=int,
                             validators=[DataRequired(message="Selecione um projeto.")])

    # Campo de Data. 'format' especifica como a data deve ser interpretada/formatada.
    date = DateField('Data da Reunião*',
                     format='%Y-%m-%d', # Formato ISO (AAAA-MM-DD), bom para date pickers HTML5
                     validators=[DataRequired(message="Data é obrigatória.")])

    # Campo de Hora. Opcional.
    time = TimeField('Horário (Opcional)',
                     format='%H:%M', # Formato 24h (HH:MM)
                     validators=[Optional()])

    # Campo Select para o formato da reunião.
    format = SelectField('Formato*', choices=[
                                            ('', '-- Selecione o Formato --'), # Opção vazia inicial
                                            ('Presencial', 'Presencial'),
                                            ('Online', 'Online'),
                                            ('Misto', 'Misto')
                                            ],
                                     validators=[DataRequired(message="Formato é obrigatório.")])

    # Campo de texto para local ou plataforma. A validação customizada abaixo o torna obrigatório condicionalmente.
    location_or_platform = StringField('Local ou Plataforma',
                                       render_kw={"placeholder": "Ex: Sala de Reuniões 1 / Google Meet"},
                                       validators=[Optional(), Length(max=200)])

    # Campo para selecionar os participantes presentes. Usamos o MultiCheckboxField.
    # As opções (choices) serão populadas dinamicamente na rota com base no projeto selecionado.
    attendees_present = MultiCheckboxField('Participantes Presentes*',
                                           coerce=int,
                                           # Não colocamos DataRequired aqui, pois a lógica na rota
                                           # considerará todos os membros do projeto. Validar se pelo menos
                                           # um está presente pode ser feito na rota, se necessário.
                                           validators=[Optional()])

    # Campo de texto longo para os detalhes da ata.
    discussion_text = TextAreaField('Assuntos Discutidos / Deliberações*',
                                    render_kw={"rows": 10, "placeholder": "Digite aqui o conteúdo da ata..."},
                                    validators=[DataRequired(message="Descrição dos assuntos é obrigatória.")])

    submit = SubmitField('Salvar Ata') # O botão pode gerar PDF depois ou em outra ação

    # Método para popular as opções do campo 'project_id' (chamar na rota)
    def set_project_choices(self):
        """Busca projetos no DB e define as opções para o campo 'project_id'."""
        from models import Project # Import local
        try:
            # Adiciona uma opção inicial não selecionável
            choices = [('', '-- Selecione um Projeto --')]
            projects = Project.query.order_by(Project.name).all()
            choices.extend([(p.id, p.name) for p in projects])
            self.project_id.choices = choices
        except Exception as e:
            print(f"Erro ao buscar projetos para choices: {e}")
            self.project_id.choices = [('', '-- Erro ao carregar Projetos --')]

    # Método para popular as opções do campo 'attendees_present' (chamar na rota)
    def set_attendee_choices(self, members_list):
        """Popula as opções de participantes com base em uma lista de objetos Member."""
        # Recebe uma lista de objetos Member (geralmente project.members)
        try:
            self.attendees_present.choices = [(m.id, m.name) for m in sorted(members_list, key=lambda x: x.name)]
        except Exception as e:
             print(f"Erro ao definir choices de participantes: {e}")
             self.attendees_present.choices = []

    # Validação customizada: Garante que 'location_or_platform' seja preenchido se formato for Presencial, Online ou Misto.
    def validate_location_or_platform(self, field):
        """Validador customizado para o campo Local/Plataforma."""
        format_selected = self.format.data
        # Se um formato que exige local/plataforma foi selecionado E o campo está vazio
        if format_selected in ['Presencial', 'Online', 'Misto'] and not field.data:
            if format_selected == 'Online':
                raise ValidationError('A Plataforma é obrigatória para reuniões online.')
            else: # Presencial ou Misto
                raise ValidationError('O Local é obrigatório para reuniões presenciais ou mistas.')

    # Validação customizada (opcional): Garantir que pelo menos um participante esteja marcado?
    # def validate_attendees_present(self, field):
    #    if not field.data: # field.data será uma lista de IDs
    #        raise ValidationError("Selecione pelo menos um participante presente.")