# seu_projeto_flask/.flaskenv
FLASK_APP=run.py
FLASK_ENV=development # Ativa o modo de desenvolvimento (debug=True)

# Credenciais do Banco de Dados que serão lidas pelo config.py
### Por padrão para desenvolvimento local, usamos SQLite (arquivo em instance/)
DATABASE_URI=sqlite:///instance/ata.sqlite3

# Se quiser testar com PostgreSQL (produção), substitua a linha acima por:
# DATABASE_URI=postgresql://USUARIO:SENHA@localhost:5432/NOME_DO_BANCO
