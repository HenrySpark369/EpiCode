document.addEventListener("DOMContentLoaded", () => {
  const sendBtn = document.getElementById("sendBtn");
  const questionInput = document.getElementById("questionInput");
  const respuestaContainer = document.getElementById("respuestaContainer");
  const respuestaText = document.getElementById("respuestaText");
  const statusMsg = document.getElementById("statusMsg");

  sendBtn.addEventListener("click", async () => {
    const pregunta = questionInput.value.trim();
    if (!pregunta) {
      statusMsg.textContent = "Por favor escribe una pregunta primero.";
      return;
    }

    // Mostrar que se está procesando
    statusMsg.textContent = "Pensando… 🧠";
    respuestaContainer.style.display = "none";
    respuestaText.textContent = "";

    try {
      // Petición POST al endpoint /api/ask
      const res = await axios.post("/api/ask", { question: pregunta });

      if (res.data.error) {
        statusMsg.textContent = `Error: ${res.data.error}`;
      } else {
        // Mostrar la respuesta
        respuestaText.textContent = res.data.answer;
        respuestaContainer.style.display = "block";
        statusMsg.textContent = "¡Listo!";
      }
    } catch (err) {
      // Errores de red o servidor
      console.error(err);
      statusMsg.textContent = "Ocurrió un error al contactar al servidor.";
    }
  });
});