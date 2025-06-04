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
  
La aplicación estará disponible en: `http://localhost:5002`  
  
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
  
## Características  
  
- Interfaz de chat conversacional  
- Historial persistente de conversaciones  
- Soporte para múltiples modelos de OpenAI  
- Renderizado de Markdown con resaltado de código  
- Gestión automática de contexto con ventana deslizante  
- Eliminación en cascada de mensajes