// main.js

// Número de turnos que quieres conservar (cada turno incluye un mensaje de usuario y uno de assistant)
const MAX_TURNOS = 6;  // por ejemplo, conserva 3 intercambios completos (user+assistant = 2 turnos cada uno × 3 = 6 mensajes)

let chatHistory = [
  { role: "system", content: "Eres un asistente muy hábil en programación..." }
];

document.addEventListener("DOMContentLoaded", () => {
  const sendBtn = document.getElementById("sendBtn");
  const questionInput = document.getElementById("questionInput");
  const chatContainer = document.getElementById("chatContainer");
  const statusMsg = document.getElementById("statusMsg");

  questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  sendBtn.addEventListener("click", async () => {
    const pregunta = questionInput.value.trim();
    if (!pregunta) {
      statusMsg.textContent = "Por favor escribe una pregunta primero.";
      return;
    }
    // Limpiar el campo de texto después de obtener la pregunta
    questionInput.value = "";

    // 1) Guardar el mensaje del usuario
    chatHistory.push({ role: "user", content: pregunta });

    // 2) Aplicar ventana deslizante: conservar sólo los últimos MAX_TURNOS mensajes (excluyendo el system)
    //    Esto recorta el array dejando el "system" en la posición 0 y luego los MAX_TURNOS últimos, p.ej. 6.
    const systemMensaje = chatHistory[0];
    const ultimos = chatHistory.slice(-MAX_TURNOS);
    const mensajesAEnviar = [systemMensaje, ...ultimos];

    // Mostrar que se está procesando
    statusMsg.textContent = "Pensando… 🧠";
    chatContainer.style.display = "block";

    // Mostrar el mensaje del usuario
    const userDiv = document.createElement("div");
    userDiv.classList.add("chat-message", "chat-user");
    userDiv.innerHTML = `<strong>Tú:</strong> ${pregunta}`;
    chatContainer.appendChild(userDiv);

    try {
      // Petición POST al endpoint /api/ask
      const res = await axios.post("/api/ask", { messages: mensajesAEnviar });

      if (res.data.error) {
        statusMsg.textContent = `Error: ${res.data.error}`;
      } else {
        // Convertir el Markdown recibido a HTML usando marked()
        const markdown = res.data.answer;
        // 4) Guardar la respuesta del asistente
        chatHistory.push({ role: "assistant", content: markdown });

        const botDiv = document.createElement("div");
        botDiv.classList.add("chat-message", "chat-bot");
        botDiv.innerHTML = `<strong>Asistente:</strong> ${marked.parse(markdown)}`;
        chatContainer.appendChild(botDiv);
        statusMsg.textContent = "¡Listo!";
      }
    } catch (err) {
      // Errores de red o servidor
      console.error(err);
      statusMsg.textContent = "Ocurrió un error al contactar al servidor.";
    }
  });
});