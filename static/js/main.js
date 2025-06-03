// main.js

const MAX_TURNOS = 6; // Still defined, but the actual sliding window is managed by the backend
const SYSTEM_MESSAGE_CONTENT = "Eres un asistente de programación muy hábil. Responde de forma clara y concisa."; // Backend creates the system message

let conversations = [];            // Array of { id, title, created_at } from the backend
let currentConvId = null;          // ID of the active conversation

// --- Helpers for interacting with the Backend ---

/**
 * Loads all conversations from the backend and updates the local 'conversations' array.
 */
async function loadConversations() {
  try {
    const response = await axios.get("/api/conversations");
    conversations = response.data;
    // Ensure titles are strings, handle potential nulls from DB if any
    conversations.forEach(conv => {
      conv.title = conv.title || "Sin título";
    });
    renderConversationList(); // Update sidebar after loading
  } catch (error) {
    console.error("Error al cargar conversaciones:", error);
    document.getElementById("statusMsg").textContent = "Error al cargar conversaciones.";
    conversations = []; // Clear if error
  }
}

/**
 * Saves (updates the title of) a conversation in the backend.
 * @param {number} convId - The ID of the conversation to update.
 * @param {string} newTitle - The new title for the conversation.
 */
async function saveConversationTitle(convId, newTitle) {
  try {
    await axios.patch(`/api/conversations/${convId}`, { title: newTitle });
    // After renaming, refresh the list to show the new title
    await loadConversations();
  } catch (error) {
    console.error(`Error al renombrar conversación ${convId}:`, error);
    document.getElementById("statusMsg").textContent = `Error al renombrar conversación: ${error.message || error.response.data.error}`;
  }
}

// --- UI for the conversation list (sidebar) ---

function renderConversationList() {
  const ul = document.getElementById("convList"); // Changed from conversationList to convList as per HTML
  ul.innerHTML = "";
  if (conversations.length === 0) {
    ul.innerHTML = "<li class='list-group-item text-muted'>No hay conversaciones.</li>";
  }

  conversations.forEach(conv => {
    const li = document.createElement("li");
    li.className = "list-group-item list-group-item-action";
    if (conv.id === currentConvId) li.classList.add("active");

    const titleSpan = document.createElement("span");
    titleSpan.textContent = conv.title;
    titleSpan.className = "flex-grow-1"; // Allow title to take space

    // Optional: Add a rename button/icon (e.g., Bootstrap icon)
    const renameBtn = document.createElement("button");
    renameBtn.className = "btn btn-sm btn-link p-0 ms-auto";
    renameBtn.innerHTML = '✏️'; // Pencil icon
    renameBtn.title = "Renombrar";
    renameBtn.onclick = (e) => {
      e.stopPropagation(); // Prevent selecting conversation when clicking rename
      const newName = prompt("Nuevo nombre para la conversación:", conv.title);
      if (newName !== null && newName.trim() !== "" && newName !== conv.title) {
        saveConversationTitle(conv.id, newName.trim());
      }
    };

    li.appendChild(titleSpan);
    li.appendChild(renameBtn);

    li.onclick = () => selectConversation(conv.id);
    ul.appendChild(li);
  });
}

/**
 * Selects a conversation by its ID, updates UI, and loads its history.
 * @param {number} id - The ID of the conversation to select.
 */
async function selectConversation(id) {
  currentConvId = id;
  renderConversationList(); // Highlight the active conversation in the sidebar
  await renderChat(); // Load and display the chat history for the selected conversation
}

/**
 * Creates a new conversation via the backend, then selects it.
 */
async function newConversation() {
  document.getElementById("statusMsg").textContent = "Creando nueva conversación...";
  try {
    const response = await axios.post("/api/conversations");
    const newConvId = response.data.id;

    // Reload conversations to get the new one and its correct order
    await loadConversations();
    selectConversation(newConvId);
    document.getElementById("statusMsg").textContent = "Nueva conversación creada.";
  } catch (error) {
    console.error("Error al crear nueva conversación:", error);
    document.getElementById("statusMsg").textContent = "Error al crear nueva conversación.";
  }
}

/**
 * Gets the current conversation object from the local 'conversations' array.
 * This is primarily for accessing its 'title' locally.
 * @returns {object|undefined} The current conversation object.
 */
function getCurrentConvFromList() {
  return conversations.find(c => c.id === currentConvId);
}

/**
 * Renders the chat messages for the currently selected conversation.
 * Fetches messages from the backend.
 */
async function renderChat() {
  const chatContainer = document.getElementById("chatContainer");
  chatContainer.innerHTML = ""; // Clear existing messages
  const conv = getCurrentConvFromList();

  if (!conv || !currentConvId) {
    chatContainer.innerHTML = "<p class='text-muted text-center mt-5'>Selecciona o crea una conversación para empezar.</p>";
    return;
  }

  document.getElementById("statusMsg").textContent = "Cargando historial...";
  try {
    const response = await axios.get(`/api/conversations/${currentConvId}/messages`);
    const history = response.data; // This now includes system message, but we filter it.

    if (history.length === 1 && history[0].role === "system") {
        chatContainer.innerHTML = "<p class='text-muted text-center mt-5'>¡Hola! Soy tu asistente de programación. ¿En qué puedo ayudarte hoy?</p>";
    } else {
        history.filter(msg => msg.role !== "system").forEach(msg => { // Filter out system messages for display
            const div = document.createElement("div");
            div.classList.add("chat-message", msg.role === "user" ? "chat-user" : "chat-bot");
            const who = msg.role === "user" ? "Tú" : "Asistente";
            const content = msg.role === "assistant" ? marked.parse(msg.content) : msg.content;
            div.innerHTML = `<strong>${who}:</strong> ${content}`;
            chatContainer.appendChild(div);
        });
    }

    scrollToBottom();
    hljs.highlightAll(); // Highlight code blocks after rendering
    document.getElementById("statusMsg").textContent = "Historial cargado.";
  } catch (error) {
    console.error("Error al cargar el historial del chat:", error);
    document.getElementById("statusMsg").textContent = "Error al cargar el historial de la conversación.";
    chatContainer.innerHTML = "<p class='text-danger text-center mt-5'>Error al cargar el historial de la conversación.</p>";
  }
}

/**
 * Scrolls the chat container to the bottom.
 */
function scrollToBottom() {
  const chatContainer = document.getElementById("chatContainer");
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// --- Main Logic (DOMContentLoaded) ---

document.addEventListener("DOMContentLoaded", async () => {
  const sendBtn = document.getElementById("sendBtn");
  const questionInput = document.getElementById("questionInput");
  const statusMsg = document.getElementById("statusMsg");
  const modelSelect = document.getElementById("modelSelect");
  const newConvBtn = document.getElementById("newConvBtn"); // Get the new conversation button

  // Configure marked + highlight.js
  marked.setOptions({
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return hljs.highlightAuto(code).value;
    }
  });

  // Initial load: Load existing conversations or create a new one
  await loadConversations();
  if (conversations.length === 0) {
    // If no conversations exist, create a new one automatically
    await newConversation();
  } else {
    // Otherwise, select the most recent one (first in the 'conversations' array)
    selectConversation(conversations[0].id);
  }

  // Event listener for "Nueva conversación" button
  newConvBtn.addEventListener("click", newConversation);

  // Enter key to send message
  questionInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  // Send button click handler
  sendBtn.addEventListener("click", async () => {
    const pregunta = questionInput.value.trim();
    if (!pregunta) {
      statusMsg.textContent = "Por favor escribe una pregunta primero.";
      return;
    }
    questionInput.value = ""; // Clear input field

    if (!currentConvId) {
      statusMsg.textContent = "No hay una conversación activa. Por favor, crea o selecciona una.";
      return;
    }

    // --- Optimistic UI Update: Display user message immediately ---
    const chatContainer = document.getElementById("chatContainer");
    const userDiv = document.createElement("div");
    userDiv.classList.add("chat-message", "chat-user");
    userDiv.innerHTML = `<strong>Tú:</strong> ${pregunta}`;
    chatContainer.appendChild(userDiv);
    scrollToBottom();

    // --- Update conversation title if it's "Sin título" ---
    const convInList = getCurrentConvFromList();
    if (convInList && convInList.title === "Sin título") {
      const newTitle = pregunta.slice(0, 20) + (pregunta.length > 20 ? "…" : "");
      convInList.title = newTitle; // Update local object
      await saveConversationTitle(currentConvId, newTitle); // Send to backend and re-render sidebar
    }

    statusMsg.textContent = "Pensando… 🧠";

    try {
      // Send message to the backend
      const res = await axios.post(`/api/conversations/${currentConvId}/messages`, {
        content: pregunta,
        model: modelSelect.value
      });

      if (res.data.error) {
        statusMsg.textContent = `Error: ${res.data.error}`;
        // Optionally, remove the last user message from UI if send failed
        // userDiv.remove();
        return;
      }
      const answer = res.data.answer.trim();

      // --- Display assistant's answer ---
      const botDiv = document.createElement("div");
      botDiv.classList.add("chat-message", "chat-bot");
      botDiv.innerHTML = `<strong>Asistente:</strong> ${marked.parse(answer)}`;
      chatContainer.appendChild(botDiv);
      scrollToBottom();
      hljs.highlightAll(); // Highlight new code blocks

      document.getElementById("statusMsg").textContent = "¡Listo!";

      // After successful message, re-render chat just in case (e.g. for complete sync if history diverges)
      // Or simply trust the optimistic update and backend's answer
      // A full `renderChat()` call here is robust but might cause a flicker.
      // For a simpler app, appending is often enough.
      // await renderChat(); // Optional: uncomment if you want to fully re-render chat from backend after each message
    } catch (err) {
      console.error(err);
      statusMsg.textContent = "Ocurrió un error al contactar al servidor.";
      // Optionally, remove the last user message from UI if send failed
      // userDiv.remove();
    }
  });
});