# Usa imagem oficial do Python 3.11 slim
FROM python:3.11-slim

# Define diretório padrão de trabalho dentro do container
WORKDIR /app

# Copia os arquivos do projeto pro container
COPY . .

# Instala dependências do sistema (como libpq pra psycopg2)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expõe a porta padrão do gunicorn
EXPOSE 8000

# Comando de inicialização
CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:8000"]
