# Ata: Sistema de Gestão de Atas de Reunião

Projeto web desenvolvido com **Flask** para o gerenciamento de **Atas de Reunião**, com persistência de dados via **SQLAlchemy (ORM)** e versionamento do banco utilizando **Flask-Migrate**.

O banco de dados padrão em ambiente de desenvolvimento é o **SQLite**, localizado em:

```
instance/ata.sqlite3
```

---

## 🚀 Como configurar e rodar o projeto

Os passos abaixo assumem um ambiente Linux/macOS. No Windows, apenas adapte os comandos de ativação do ambiente virtual.

---

## 1. Preparação do ambiente

No terminal:

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd SEU_REPOSITORIO/

# Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# .\\venv\\Scripts\\activate  # Windows (PowerShell)

# Instale as dependências
pip install -r requirements.txt
```

---

## 2. Configuração do Flask (SQLite)

Crie ou edite o arquivo **.flaskenv** na raiz do projeto para definir as variáveis de ambiente essenciais:

```env
FLASK_APP=run.py
FLASK_ENV=development
DATABASE_URI=sqlite:///instance/ata.sqlite3
```

Essas variáveis permitem que o Flask identifique corretamente o ponto de entrada da aplicação e o banco de dados utilizado.

---

## 3. Inicialização do banco de dados

Para criar a estrutura do banco e aplicar as migrações:

```bash
# Inicializa o sistema de migrações (executar apenas uma vez)
flask db init

# Aplica todas as migrações e cria o arquivo ata.sqlite3
flask db upgrade
```

Ao final desse processo, o banco **ata.sqlite3** será criado automaticamente dentro da pasta `instance/`.

---

## 4. Criar o usuário administrador

Crie o usuário que será utilizado para acessar a aplicação:

```bash
flask create-user
```

O comando abrirá um prompt solicitando:
- Nome de usuário
- Senha

---

## 5. Iniciar o servidor

Com o ambiente virtual ativo, execute:

```bash
flask run
```

A aplicação estará disponível, por padrão, em:

```
http://127.0.0.1:5000
```

---

## 🧠 Observações finais

- Certifique-se de que o ambiente virtual esteja **ativo** sempre que for rodar o projeto.
- Em produção, recomenda-se substituir o SQLite por um banco mais robusto (ex.: PostgreSQL).
- O arquivo `run.py` deve conter o ponto de entrada da aplicação com `app.run()`.

Código não executa intenções. Executa comandos.