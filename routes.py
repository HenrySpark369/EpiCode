# routes.py
import os
from flask import request, jsonify, render_template, current_app # Import render_template directly
from models import db, Conversation, Message, RoleEnum
import openai

MAX_TURNOS = 6

def init_app(app_instance): # 'app_instance' is the Flask app object passed from manage.py
    # Configure OpenAI API key and allowed models from the app config
    openai.api_key = app_instance.config.get("OPENAI_API_KEY")
    ALLOWED_MODELS = app_instance.config.get("ALLOWED_MODELS", [])

    # 3. Ruta principal que sirve la plantilla HTML
    @app_instance.route("/") # Decorator uses the passed app_instance
    def index():
        return render_template(
            "index.html",
            models=ALLOWED_MODELS, # Use the ALLOWED_MODELS from the init_app scope
            default_model="o4-mini")

    # 4. Endpoint API para procesar preguntas de programación
    @app_instance.route("/api/ask", methods=["POST"])
    def ask():
        data = request.get_json()
        mensajes = data.get("messages", [])

        # 3) Leemos el modelo enviado (o fallback a o4-mini)
        model = data.get("model", "o4-mini")
        # Access ALLOWED_MODELS via current_app.config since it's an app-wide setting
        if model not in current_app.config.get("ALLOWED_MODELS", []):
            return jsonify({"error": f"Modelo no permitido: {model}"}), 400

        # If no system message, insert one by default
        if not mensajes or mensajes[0].get("role") != "system":
            mensajes.insert(0, {
                "role": "system",
                "content": "Eres un asistente de programación muy hábil. Responde de forma clara y concisa."
            })

        try:
            # Prepare arguments for openai.responses.create
            params = {
                "model": model,
                "input": mensajes,
                "max_output_tokens": 25000
            }

            # Add reasoning only if the model supports it
            if model in ["o4-mini"]:
                params["reasoning"] = {"effort": "medium"}

            resp = openai.responses.create(**params)
            current_app.logger.debug("Respuesta completa de OpenAI: %s", resp) # Use current_app.logger

            # --- Your truncated token check ---
            truncated = False
            if getattr(resp, "status", None) == "incomplete" and \
               getattr(resp, "incomplete_details", None) and \
               resp.incomplete_details.reason == "max_output_tokens":
                truncated = True
                current_app.logger.warning("Ran out of tokens")
                if resp.output_text:
                    current_app.logger.warning("Partial output: %s", resp.output_text)
                else:
                    current_app.logger.warning("Ran out of tokens durante el razonamiento")
            # -------------------------------------------------

            # 6. Extract the answer
            contenido = resp.output_text.strip()

            current_app.logger.debug("Contenido generado: %s", contenido) # Use current_app.logger

            return jsonify({
                "answer": contenido,
                "truncated": truncated
                })

        except openai.BadRequestError as e:
            current_app.logger.error("BadRequest en /api/ask: %s", e, exc_info=True)
            return jsonify({"error": e._message}), 400

        except Exception as e:
            current_app.logger.error("Error en /api/ask: %s", e, exc_info=True)
            return jsonify({"error": "Error interno del servidor. Revisa los registros."}), 500

    @app_instance.route("/api/conversations", methods=["GET", "POST"])
    def conversations():
        if request.method == "GET":
            convs = Conversation.query.order_by(Conversation.created_at.desc()).all()
            # Ensure created_at is JSON serializable
            return jsonify([{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in convs])
        else:
            # POST -> create new conversation
            conv = Conversation()
            db.session.add(conv)
            db.session.commit()
            # Create initial system message
            sys_msg = Message(
                conversation_id=conv.id,
                role=RoleEnum.system,
                content="Eres un asistente de programación muy hábil. Responde de forma clara y concisa.",
                turn_index=0
            )
            db.session.add(sys_msg)
            db.session.commit()
            return jsonify({"id": conv.id}), 201

    @app_instance.route("/api/conversations/<int:conv_id>/messages", methods=["GET", "POST"])
    def messages(conv_id):
        conv = Conversation.query.get_or_404(conv_id)
        if request.method == "GET":
            # Return full history or last N messages
            msgs = [{
                "role": m.role.value,
                "content": m.content,
                "created_at": m.created_at.isoformat() # Ensure created_at is serializable
            } for m in conv.messages]
            return jsonify(msgs)

        # POST -> add user message, call OpenAI, save response
        data = request.get_json()
        user_text = data.get("content")
        model = data.get("model", "o4-mini")

        # 1) Save user message
        last_message = Message.query.filter_by(conversation_id=conv.id)\
                                  .order_by(Message.turn_index.desc()).first()
        last_index = last_message.turn_index if last_message else -1
        user_msg = Message(
            conversation_id=conv.id,
            role=RoleEnum.user,
            content=user_text,
            turn_index=last_index + 1
        )
        db.session.add(user_msg)
        db.session.flush()

        # 2) Prepare messages for OpenAI: system + last MAX_TURNOS
        all_messages_for_context = Message.query.filter_by(conversation_id=conv.id)\
                                                .order_by(Message.turn_index.asc()).all()

        system_msg = None
        context_messages = []
        for msg in all_messages_for_context:
            if msg.role == RoleEnum.system:
                system_msg = msg
            else:
                context_messages.append(msg)

        # Apply sliding window only to non-system messages
        últimos = context_messages[-MAX_TURNOS:]

        payload = []
        if system_msg:
            payload.append({"role": system_msg.role.value, "content": system_msg.content})
        payload.extend([{"role": m.role.value, "content": m.content} for m in últimos])

        # 3) Call OpenAI
        params = {"model": model, "input": payload, "max_output_tokens": 4096}
        if model in ["o4-mini"]:
            params["reasoning"] = {"effort": "medium"}
        resp = openai.responses.create(**params)
        answer = resp.output_text.strip()

        # 4) Save assistant
        assistant_msg = Message(
            conversation_id=conv.id,
            role=RoleEnum.assistant,
            content=answer,
            turn_index=last_index + 2
        )
        db.session.add(assistant_msg)
        db.session.commit()

        return jsonify({"answer": answer})

    # (Optional) rename conversation
    @app_instance.route("/api/conversations/<int:conv_id>", methods=["PATCH"])
    def rename(conv_id):
        conv = Conversation.query.get_or_404(conv_id)
        data = request.get_json()
        new_title = data.get("title")
        if new_title is not None and new_title.strip() != "":
            conv.title = new_title.strip()
        else:
            conv.title = "Sin título"
        db.session.commit()
        return jsonify({"id": conv.id, "title": conv.title})

    @app_instance.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
    def delete_conversation(conv_id):
        conv = Conversation.query.get_or_404(conv_id)
        db.session.delete(conv)
        db.session.commit()
        return jsonify({"success": True}), 200

    # Health check endpoint
    @app_instance.route("/health")
    def health():
        return jsonify({"status": "OK"})