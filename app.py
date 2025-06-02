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

# 3. Ruta principal que sirve la plantilla HTML
@app.route("/")
def index():
    return render_template("index.html")

# 4. Endpoint API para procesar preguntas de programación
@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json()
    pregunta = data.get("question", "").strip()

    if not pregunta:
        return jsonify({"error": "La pregunta está vacía."}), 400

    try:
        # 5. Consumir la API de OpenAI con el modelo o4-mini-high
        response = openai.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente de programación muy hábil. Responde de forma clara y concisa."},
                {"role": "user", "content": pregunta}
            ],
            max_completion_tokens=512,        # ajusta según lo que necesites
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )

        # 6. Extraer la respuesta
        contenido = response.choices[0].message.content.strip()

        return jsonify({"answer": contenido})

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