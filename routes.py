# routes.py

import os
# import openai                                    # comentado para aislar C-extension
from flask import (
    request, jsonify, render_template,
    current_app, Response, stream_with_context,
    url_for, redirect, flash
)
from flask_login import login_required, current_user
from models import db, Conversation, Message, RoleEnum, User
# from openai import OpenAI

# Stub OpenAI to avoid NameError during isolation
class OpenAI:
    def __init__(self, api_key=None):
        pass

    @property
    def responses(self):
        class Dummy:
            def create(self, **kwargs):
                class R:
                    output_text = ""
                    status = None
                    incomplete_details = None
                return R()
        return Dummy()
from decorators import admin_required

MAX_TURNOS = 6

def init_app(app_instance):
    # Configura cliente OpenAI y modelos permitidos
    client = OpenAI(api_key=app_instance.config.get("OPENAI_API_KEY"))
    ALLOWED_MODELS = app_instance.config.get("ALLOWED_MODELS", [])

    # Ruta pública
    @app_instance.route("/")
    @login_required
    def index():
        return render_template(
            "index.html",
            models=ALLOWED_MODELS,
            default_model="chatgpt-4o-latest"
        )

    # Endpoint genérico de ask (requiere login)
    @app_instance.route("/api/ask", methods=["POST"])
    @login_required
    def ask():
        data = request.get_json()
        mensajes = data.get("messages", [])
        model = data.get("model", "chatgpt-4o-latest")

        if model not in ALLOWED_MODELS:
            return jsonify({"error": f"Modelo no permitido: {model}"}), 400

        if not mensajes or mensajes[0].get("role") != "system":
            mensajes.insert(0, {
                "role": "system",
                "content": "Eres un asistente de programación muy hábil. Responde de forma clara y concisa."
            })

        try:
            params = {
                "model": model,
                "input": mensajes,
                "max_output_tokens": 25000
            }
            if model == "o4-mini":
                params["reasoning"] = {"effort": "medium"}

            resp = client.responses.create(**params)
            current_app.logger.debug("Respuesta completa de OpenAI: %s", resp)

            truncated = False
            if getattr(resp, "status", None) == "incomplete" and \
               getattr(resp, "incomplete_details", None) and \
               resp.incomplete_details.reason == "max_output_tokens":
                truncated = True
                current_app.logger.warning("Ran out of tokens")
                if resp.output_text:
                    current_app.logger.warning("Partial output: %s", resp.output_text)

            contenido = resp.output_text.strip()
            current_app.logger.debug("Contenido generado: %s", contenido)

            return jsonify({"answer": contenido, "truncated": truncated})


        except Exception as e:
            current_app.logger.error("Error en /api/ask: %s", e, exc_info=True)
            return jsonify({"error": "Error interno del servidor. Revisa los registros."}), 500

    # Listar y crear conversaciones propias
    @app_instance.route("/api/conversations", methods=["GET", "POST"])
    @login_required
    def conversations():
        if request.method == "GET":
            convs = Conversation.query\
                .filter_by(user_id=current_user.id)\
                .order_by(Conversation.created_at.desc())\
                .all()
            return jsonify([{
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat()
            } for c in convs])

        # POST -> nueva conversación para el usuario actual
        conv = Conversation(user_id=current_user.id)
        db.session.add(conv)
        db.session.flush()

        sys_msg = Message(
            conversation_id=conv.id,
            role=RoleEnum.system,
            content="Eres un asistente de programación muy hábil. Responde de forma clara y concisa.",
            turn_index=0
        )
        db.session.add(sys_msg)
        db.session.commit()
        return jsonify({"id": conv.id}), 201

    # Obtener o añadir mensajes de una conversación
    @app_instance.route("/api/conversations/<int:conv_id>/messages", methods=["GET", "POST"])
    @login_required
    def messages(conv_id):
        conv = Conversation.query.get_or_404(conv_id)
        if conv.user_id != current_user.id:
            return jsonify({"error": "Acceso no autorizado"}), 403

        if request.method == "GET":
            msgs = [{
                "role": m.role.value,
                "content": m.content,
                "created_at": m.created_at.isoformat()
            } for m in conv.messages]
            return jsonify(msgs)

        # POST -> guardar user + llamar OpenAI + guardar assistant
        data = request.get_json()
        user_text = data.get("content")
        model = data.get("model", "chatgpt-4o-latest")

        last_message = Message.query.filter_by(conversation_id=conv.id)\
                          .order_by(Message.turn_index.desc())\
                          .first()
        last_index = last_message.turn_index if last_message else -1

        user_msg = Message(
            conversation_id=conv.id,
            role=RoleEnum.user,
            content=user_text,
            turn_index=last_index + 1
        )
        db.session.add(user_msg)
        db.session.flush()

        all_messages = Message.query.filter_by(conversation_id=conv.id)\
                            .order_by(Message.turn_index.asc())\
                            .all()

        system_msg = next((m for m in all_messages if m.role == RoleEnum.system), None)
        context = [m for m in all_messages if m.role != RoleEnum.system]
        últimos = context[-MAX_TURNOS:]

        payload = []
        if system_msg:
            payload.append({"role": system_msg.role.value, "content": system_msg.content})
        payload += [{"role": m.role.value, "content": m.content} for m in últimos]

        params = {"model": model, "input": payload, "max_output_tokens": 4096}
        if model == "o4-mini":
            params["reasoning"] = {"effort": "medium"}

        resp = client.responses.create(**params)
        answer = resp.output_text.strip()

        assistant_msg = Message(
            conversation_id=conv.id,
            role=RoleEnum.assistant,
            content=answer,
            turn_index=last_index + 2
        )
        db.session.add(assistant_msg)
        db.session.commit()

        return jsonify({"answer": answer})

    # Streaming de mensajes
    @app_instance.route("/api/conversations/<int:conv_id>/messages/stream", methods=["POST"])
    @login_required
    def stream_messages(conv_id):
        conv = Conversation.query.get_or_404(conv_id)
        if conv.user_id != current_user.id:
            return jsonify({"error": "Acceso no autorizado"}), 403

        data = request.get_json()
        user_text = data.get("content", "")
        model     = data.get("model", "chatgpt-4o-latest")

        last_msg = Message.query.filter_by(conversation_id=conv.id)\
                                 .order_by(Message.turn_index.desc())\
                                 .first()
        idx = last_msg.turn_index if last_msg else -1

        user_msg = Message(
            conversation_id=conv.id,
            role=RoleEnum.user,
            content=user_text,
            turn_index=idx + 1
        )
        db.session.add(user_msg)
        db.session.flush()

        all_msgs = Message.query.filter_by(conversation_id=conv.id)\
                                .order_by(Message.turn_index.asc())\
                                .all()
        system_msg = next((m for m in all_msgs if m.role==RoleEnum.system), None)
        history    = [m for m in all_msgs if m.role!=RoleEnum.system][-MAX_TURNOS:]

        payload = []
        if system_msg:
            payload.append({"role":"system", "content":system_msg.content})
        payload += [{"role":m.role.value, "content":m.content} for m in history]

        def generate():
            full_resp = ""
            try:
                if model == "o4-mini":
                    stream_resp = client.responses.create(
                        model=model,
                        input=payload,
                        stream=True,
                        max_output_tokens=4096,
                        reasoning={"effort":"medium"}
                    )
                else:
                    stream_resp = client.chat.completions.create(
                        model=model,
                        messages=payload,
                        stream=True,
                        max_tokens=1024
                    )

                for chunk in stream_resp:
                    if model == "o4-mini":
                        delta = getattr(chunk, "text", "")
                    else:
                        delta = getattr(chunk.choices[0].delta, "content", "") or ""
                    if not delta:
                        continue
                    full_resp += delta
                    yield delta.encode("utf-8")

            except Exception as e:
                current_app.logger.error("Error en stream: %s", e, exc_info=True)
                yield f"\n\n[Stream interrumpido: {e}]\n".encode("utf-8")
            finally:
                assistant_msg = Message(
                    conversation_id=conv.id,
                    role=RoleEnum.assistant,
                    content=full_resp,
                    turn_index=idx + 2
                )
                db.session.add(assistant_msg)
                db.session.commit()
                current_app.logger.debug("Respuesta stream guardada.")

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain; charset=utf-8",
            headers={"Cache-Control":"no-transform"}
        )

    # Renombrar conversación
    @app_instance.route("/api/conversations/<int:conv_id>", methods=["PATCH"])
    @login_required
    def rename(conv_id):
        conv = Conversation.query.get_or_404(conv_id)
        if conv.user_id != current_user.id:
            return jsonify({"error": "Acceso no autorizado"}), 403

        data = request.get_json()
        new_title = data.get("title", "").strip()
        conv.title = new_title if new_title else "Sin título"
        db.session.commit()
        return jsonify({"id": conv.id, "title": conv.title})

    # Borrar conversación
    @app_instance.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
    @login_required
    def delete_conversation(conv_id):
        conv = Conversation.query.get_or_404(conv_id)
        if conv.user_id != current_user.id:
            return jsonify({"error": "Acceso no autorizado"}), 403

        db.session.delete(conv)
        db.session.commit()
        return jsonify({"success": True}), 200

    # Health check público
    @app_instance.route("/health")
    def health():
        return jsonify({"status": "OK"})
