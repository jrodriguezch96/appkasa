# Base runtime image for OpenSSL configuration
FROM mcr.microsoft.com/dotnet/runtime:7.0-alpine AS base-runtime

# OpenSSL 3.0 configuration
RUN sed -i 's/providers = provider_sect/providers = provider_sect\n\
ssl_conf = ssl_sect\n\
\n\
[ssl_sect]\n\
system_default = system_default_sect\n\
\n\
[system_default_sect]\n\
Options = UnsafeLegacyRenegotiation/' /etc/ssl/openssl.cnf

# Imagen base con Python
FROM python:3.9-alpine

# Copiamos la configuración de openssl de la imagen base
COPY --from=base-runtime /etc/ssl/openssl.cnf /etc/ssl/openssl.cnf

# Instalar dependencias de OpenSSL
RUN apk add --no-cache openssl

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos los archivos de requerimientos y los instalamos
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copiamos el resto del código de la aplicación
COPY . .

# Verificar configuración de OpenSSL
RUN cat /etc/ssl/openssl.cnf | grep -A 3 'ssl_conf = ssl_sect'

# Definimos el comando para ejecutar la aplicación
CMD ["sh", "-c", "python3 -m app.start2 & flask --app api_rest run --host=0.0.0.0 --port=5000"] --port=5000"]