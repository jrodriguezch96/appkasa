# Utilizamos una imagen base con Python
FROM python:3.9

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos los archivos de requerimientos y los instalamos
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copiamos el resto del código de la aplicación
COPY . .

# Definimos el comando para ejecutar la aplicación
CMD ["sh", "-c", "celery -A app.tasks worker --loglevel=info & celery -A app.tasks beat --loglevel=info & python3 -m flask run --host=0.0.0.0 --port=5000"]