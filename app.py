import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import openai
import logging

# 1. Cargar variables de entorno
load_dotenv(override=True)  # lee .env y prioriza sus valores sobre las variables existentes

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("La variable de entorno OPENAI_API_KEY no está definida.")

# 2. Inicializar cliente de OpenAI
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# 1) Lista de modelos permitidos
ALLOWED_MODELS = ["chatgpt-4o-latest", "o4-mini", "gpt-4o-mini-2024-07-18"]

# 3. Ruta principal que sirve la plantilla HTML
@app.route("/")
def index():
    return render_template(
        "index.html",
        models=ALLOWED_MODELS,
        default_model="o4-mini")

# 4. Endpoint API para procesar preguntas de programación
@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json()
    mensajes = data.get("messages", [])

    # 3) Leemos el modelo enviado (o fallback a o4-mini)
    model = data.get("model", "o4-mini")
    if model not in ALLOWED_MODELS:
        return jsonify({"error": f"Modelo no permitido: {model}"}), 400

    # Si no hay mensaje system, insertar uno por defecto
    if not mensajes or mensajes[0].get("role") != "system":
        mensajes.insert(0, {
            "role": "system",
            "content": "Eres un asistente de programación muy hábil. Responde de forma clara y concisa."
        })

    try:
        # Preparo los argumentos para openai.responses.create
        params = {
            "model": model,
            "input": mensajes,
            "max_output_tokens": 25000
        }

        # Solo añado reasoning si el modelo lo admite
        if model in ["o4-mini"]:
            params["reasoning"] = {"effort": "medium"}
        
        response = openai.responses.create(**params)
        app.logger.debug("Respuesta completa de OpenAI: %s", response)

        # --- Aquí tu comprobación de tokens truncados ---
        truncated = False
        if getattr(response, "status", None) == "incomplete" and \
           getattr(response, "incomplete_details", None) and \
           response.incomplete_details.reason == "max_output_tokens":
            truncated = True
            app.logger.warning("Ran out of tokens")
            if response.output_text:
                app.logger.warning("Partial output: %s", response.output_text)
            else:
                app.logger.warning("Ran out of tokens durante el razonamiento")
        # -------------------------------------------------

        # 6. Extraer la respuesta
        contenido = response.output_text.strip()

        app.logger.debug("Contenido generado: %s", contenido)

        return jsonify({
            "answer": contenido,
            "truncated": truncated
            })

    except openai.BadRequestError as e:
        # Si viene de la API con un 400, muestro mensaje más explícito
        app.logger.error("BadRequest en /api/ask: %s", e, exc_info=True)
        return jsonify({"error": e._message}), 400

    except Exception as e:
        # En caso de error en la petición a OpenAI
        app.logger.error("Error en /api/ask: %s", e, exc_info=True)
        return jsonify({"error": "Error interno del servidor. Revisa los registros."}), 500


# Health check endpoint
@app.route("/health")
def health():
    return jsonify({"status": "OK"})

if __name__ == "__main__":
    # Ejecutar en modo debug para desarrollo
    app.run(host="0.0.0.0", port=5001, debug=True)