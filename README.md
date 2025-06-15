# EpiCode - Asistente de Programación con IA  
  
EpiCode es un asistente de programación conversacional basado en Flask que utiliza la API de OpenAI para proporcionar ayuda con código y programación.  
  
## Requisitos Previos  
  
- Python 3.7+  
- PostgreSQL  
- Cuenta de OpenAI con API key  
  
## Configuración Inicial  
  
### 1. Variables de Entorno  
  
Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:  
  
```env  
# Obligatorio  
OPENAI_API_KEY=tu_clave_de_openai_aqui  
  
# Opcional (tiene valor por defecto)  
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/chatgpt_db  
```  
  
### 2. Configuración de la Base de Datos  
  
Por defecto, la aplicación se conecta a PostgreSQL con estos parámetros:  
- **Host**: localhost  
- **Puerto**: 5432  
- **Base de datos**: chatgpt_db  
- **Usuario**: usuario  
- **Contraseña**: your_secure_password  
  
### 3. Instalación de Dependencias  
  
```bash  
pip install -r requirements.txt  
```  
  
### 4. Inicialización de la Base de Datos  
  
```bash  
# Inicializar migraciones (solo la primera vez)  
flask db init  
  
# Crear migración inicial  
flask db migrate -m "Initial migration"  
  
# Aplicar migraciones  
flask db upgrade  
```  
  
## Arranque de la Aplicación  
  
```bash  
python manage.py  
```  
  
### Ejecución local con Gunicorn

```bash
export FLASK_ENV=development
# Ejecuta Gunicorn con:
#   - workers dinámicos (CPU*2+1)
#   - preload_app: True
#   - timeout: 30s
#   - bind: 0.0.0.0:8000
gunicorn -c gunicorn_conf.py wsgi:app
```

La aplicación estará disponible en: `http://localhost:8000`

Opciones adicionales:

```bash
# Especificar manualmente número de workers y puerto
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

## Configuración Adicional para el próximo arranque

Antes de iniciar la aplicación, configura estos elementos:

- Variables de entorno:
  - **SECRET_KEY**, **DATABASE_URL**, **OPENAI_API_KEY**  
- Nginx:
  - Ajusta `server_name` en `deploy/nginx/chatgpt.conf`  
  - Verifica la ruta `alias` para los archivos estáticos  
- Servicio systemd:
  - Sustituye `/path/to/your/project` en `deploy/systemd/chatgpt.service`  
- SSL/TLS (opcional):
  - Instala certificados (Certbot) y activa el bloque HTTPS en `chatgpt.conf`  
- Docker (si aplica):
  - Crea un archivo `.env` junto al `docker-compose.yml` o pasa variables al comando  

## Modelos de IA Soportados
  
- chatgpt-4o-latest  
- o4-mini  
- gpt-4o-mini-2024-07-18  
  
## Estructura de la Base de Datos  
  
### Tabla `conversations`  
- `id`: Identificador único  
- `title`: Título de la conversación (por defecto "Sin título")  
- `created_at`: Fecha de creación  
  
### Tabla `messages`  
- `id`: Identificador único  
- `conversation_id`: Referencia a la conversación  
- `role`: Rol del mensaje (system, user, assistant)  
- `content`: Contenido del mensaje  
- `created_at`: Fecha de creación  
- `turn_index`: Índice del turno en la conversación  
  
## Tecnologías Utilizadas  
  
### Backend  
- Flask (framework web)  
- SQLAlchemy (ORM)  
- Flask-Migrate (migraciones de BD)  
- OpenAI SDK (integración con IA)  
  
### Frontend  
- Bootstrap 5.3.0 (estilos)  
- Marked.js (renderizado de Markdown)  
- Highlight.js 11.8.0 (resaltado de código)  
- Axios (cliente HTTP)  
  
## Endpoints Principales  
  
- `GET /` - Interfaz principal  
- `POST /api/ask` - Consulta directa a IA  
- `GET /api/conversations` - Listar conversaciones  
- `POST /api/conversations` - Crear conversación  
- `GET /api/conversations/{id}/messages` - Obtener mensajes  
- `POST /api/conversations/{id}/messages` - Enviar mensaje  
- `PATCH /api/conversations/{id}` - Renombrar conversación  
- `DELETE /api/conversations/{id}` - Eliminar conversación  
- `GET /health` - Health check  
  
## Desarrollo

La aplicación se ejecuta en modo debug por defecto. Los logs se configuran automáticamente para facilitar el desarrollo.

## Configuración de Entornos

La configuración de la aplicación se centraliza en **config.py**, soportando tres entornos:

- **development**: Variables locales para desarrollo (activado por FLASK_ENV=development).  
- **testing**: Parámetros de base de datos en memoria o sandbox (activado por FLASK_ENV=testing).  
- **production**: Configuración optimizada para producción (activado por FLASK_ENV=production).

En `config.py` se definen clases `DevelopmentConfig`, `TestingConfig` y `ProductionConfig` que heredan de `BaseConfig`. Ejemplo de uso:

```python
class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # ...

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    DATABASE_URI = os.getenv('DATABASE_URL')
    # ...

class TestingConfig(BaseConfig):
    TESTING = True
    DATABASE_URI = 'sqlite:///:memory:'
    # ...

class ProductionConfig(BaseConfig):
    DEBUG = False
    DATABASE_URI = os.getenv('DATABASE_URL')
    # ...
```

## Selección de Configuración en manage.py

`manage.py` carga el entorno según la variable `FLASK_ENV`. Ejemplo:

```python
from config import DevelopmentConfig, TestingConfig, ProductionConfig
import os

env = os.getenv('FLASK_ENV', 'development').lower()
config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}
app.config.from_object(config_map.get(env))
```

Arranque de la aplicación con:

```bash
export FLASK_ENV=production
python manage.py
```

## Configuración de Gunicorn

El archivo **gunicorn_conf.py** optimiza el despliegue con:

- **workers** dinámicos: Calculados en función de CPU (`multiples de CPU * 2 + 1`).  
- **preload_app**: Precarga la aplicación en memoria antes de fork para ahorrar recursos.  
- **timeout**: Tiempo de espera para los workers.  
- **bind**: Dirección y puerto de escucha.

Ejemplo de `gunicorn_conf.py`:

```python
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
preload_app = True
timeout = 30
bind = '0.0.0.0:8000'
```

## Detección y solución de SIGSEGV al precargar la aplicación

Para identificar y corregir fallos de segmentación al usar `preload_app`:

1. Aislar la extensión conflictiva:
   - Vuelve a activar `preload_app = True` con un único worker (`workers = 1`).  
   - Comenta los imports de módulos nativos (por ejemplo `psycopg2`, `bcrypt`) uno por uno o usa un entorno REPL para aislar la extensión culpable.  
   ```bash
   preload_app = True
   workers = 1
   ```
2. Ejecutar Gunicorn bajo gdb para obtener backtrace:
   ```bash
   brew install gdb
   gdb --args gunicorn -c gunicorn_conf.py wsgi:app
   run
   backtrace
   ```
   El backtrace mostrará el módulo que causa el SIGSEGV.
3. Actualizar el paquete conflictivo:
   ```bash
   pip install --upgrade nombre_del_paquete
   ```
4. Bloquear la versión estable en `requirements.txt`:
   ```bash
   pip freeze > requirements.txt
   ```

Una vez confirmado que el error desaparece, puedes reactivar `preload_app` y ajustar `workers` según necesidad.

## Despliegue con Docker Compose y VPS

En `deploy/docker/Dockerfile` se utiliza multi-stage para reducir el tamaño de la imagen:

```dockerfile
# Stage 1: Builder
FROM python:3.9-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt
COPY . .

# Stage 2: Runner
FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app
ENV PATH=/root/.local/bin:$PATH
CMD ["gunicorn", "-c", "gunicorn_conf.py", "wsgi:app"]
```

Arranque de servicios con Docker Compose:

```bash
cd deploy/docker
docker-compose up -d --build
```

Despliegue en VPS con systemd:

```bash
scp -r . deploy@mi-servidor:/var/www/chatgpt
ssh deploy@mi-servidor
sudo cp deploy/systemd/chatgpt.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable chatgpt
sudo systemctl start chatgpt
```
  
## Características  
  
- Interfaz de chat conversacional  
- Historial persistente de conversaciones  
- Soporte para múltiples modelos de OpenAI  
- Renderizado de Markdown con resaltado de código  
- Gestión automática de contexto con ventana deslizante  
- Eliminación en cascada de mensajes
