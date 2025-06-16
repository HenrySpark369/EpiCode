// main.js

// Ajuste dinámico de espacio para #chatContainer según alto de #inputArea
function updateInputHeight() {
  const input = document.getElementById('inputArea');
  if (!input) return;
  const height = input.offsetHeight;
  document.documentElement.style.setProperty('--input-height', `${height}px`);
}
// Actualiza en carga y al redimensionar
window.addEventListener('load', updateInputHeight);
window.addEventListener('resize', updateInputHeight);

const MAX_TURNOS = 6; // Still defined, but the actual sliding window is managed by the backend
const SYSTEM_MESSAGE_CONTENT = "Eres un asistente de programación muy hábil. Responde de forma clara y concisa."; // Backend creates the system message

let conversations = [];            // Array of { id, title, created_at } from the backend
let currentConvId = null;          // ID of the active conversation

// --- Helpers for interacting with the Backend ---

// Añade esta función justo antes de tu listener de sendBtn
async function sendWithStream(convId, pregunta, model) {
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");
  const res = await fetch(
    `/api/conversations/${convId}/messages/stream`,
    {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify({ content: pregunta, model })
    }
  );
  if (!res.ok) throw new Error("Error en streaming: " + res.statusText);

  const chatContainer = document.getElementById("chatContainer");
  // Creamos el div del asistente con un <span> donde irá llegando el stream
  const botDiv = document.createElement("div");
  botDiv.className = "chat-message chat-bot";
  // Etiqueta “Asistente:”
  const labelBot = document.createElement("strong");
  labelBot.textContent = "Asistente:";
  botDiv.appendChild(labelBot);
// Contenedor para el streaming
  const streamingDiv = document.createElement("div");
  streamingDiv.className = "streaming";
  botDiv.appendChild(streamingDiv);

  chatContainer.appendChild(botDiv);
  scrollToBottom();
  const streamDiv = streamingDiv;

  // Leemos el body en chunks
  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let fullText = "";
  
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    // 1) Acumulas el trozo
    fullText += decoder.decode(value, { stream: true });
    // 2) parseas TODO el markdown
    const dirty = marked.parse(fullText);
    streamDiv.innerHTML = DOMPurify.sanitize(dirty);
    // 3) resaltas el código
    hljs.highlightAll();
    scrollToBottom();
  }
}

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
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");
    await axios.patch(`/api/conversations/${convId}`, { title: newTitle }, {
      headers: {
        "X-CSRF-Token": csrfToken
      }
    });
    // After renaming, refresh the list to show the new title
    await loadConversations();
  } catch (error) {
    console.error(`Error al renombrar conversación ${convId}:`, error);
    document.getElementById("statusMsg").textContent = `Error al renombrar conversación: ${error.message || error.response.data.error}`;
  }
}

// Borrar conversación
async function deleteConversation(convId) {
  if (!confirm("¿Seguro que quieres borrar esta conversación?")) return;
  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");
    await axios.delete(`/api/conversations/${convId}`, {
      headers: {
        "X-CSRFToken": csrfToken
      }
    });
    // Si borramos la conversación activa, limpiamos el chat
    if (currentConvId === convId) {
      currentConvId = null;
      document.getElementById("chatContainer").innerHTML = "";
    }
    await loadConversations();  // recarga listado
    // Si aún hay conversaciones, selecciona la primera
    if (conversations.length) {
      selectConversation(conversations[0].id);
    }
    document.getElementById("statusMsg").textContent = "Conversación borrada.";
  } catch (err) {
    console.error("Error borrando conversación:", err);
    document.getElementById("statusMsg").textContent = "No se pudo borrar la conversación.";
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

    // Borrar
    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-sm btn-link text-danger p-0";
    delBtn.innerHTML = "🗑️";
    delBtn.title = "Borrar conversación";
    delBtn.onclick = e => {
      e.stopPropagation();
      deleteConversation(conv.id);
    };

    li.appendChild(titleSpan);
    li.appendChild(renameBtn);
    li.appendChild(delBtn);

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
  // Si estamos en modo móvil, ocultar el sidebar automáticamente
  if (window.innerWidth <= 768) {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.remove("active");
    document.body.classList.remove("sidebar-open");
  }
}

/**
 * Creates a new conversation via the backend, then selects it.
 */
async function newConversation() {
  document.getElementById("statusMsg").textContent = "Creando nueva conversación...";
  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");
    const response = await axios.post("/api/conversations", null, {
      headers: {
        "X-CSRFToken": csrfToken
      }
    });
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
            const content = msg.role === "assistant"
              ? DOMPurify.sanitize(marked.parse(msg.content))
              : msg.content;
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
  const key      = "theme-preference";
  const html     = document.documentElement;
  const btnTheme = document.getElementById("themeToggle");

  // 1) Detecto tema inicial: 
  //    - primero lo guardado en localStorage,
  //    - si no, lo que viene en el atributo data-theme del <html>,
  //    - si tampoco, la preferencia del sistema.
  const saved     = localStorage.getItem(key);
  const attrTheme = html.getAttribute("data-theme");
  const system    = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  let theme       = saved || attrTheme || system;

  // 2) Función para aplicar y guardar
  function applyTheme(t) {
    html.setAttribute("data-theme", t);
    localStorage.setItem(key, t);
    btnTheme.textContent = t === "dark" ? " ☀️ " : " 🌙 ";
  }

  // 3) Aplico tema inicial
  applyTheme(theme);

  // Al clicar, alterna, guarda y actualiza texto
  btnTheme.addEventListener("click", () => {
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next);
  });

  window.matchMedia("(prefers-color-scheme: dark)")
        .addEventListener("change", e => {
    if (!localStorage.getItem(key)) { // sólo si el usuario NO ha forzado un tema
      applyTheme(e.matches ? "dark" : "light");
    }
  });
  
  const sendBtn = document.getElementById("sendBtn");
  const questionInput = document.getElementById("questionInput");
  const statusMsg = document.getElementById("statusMsg");
  const modelSelect = document.getElementById("modelSelect");
  const newConvBtn = document.getElementById("newConvBtn"); // Get the new conversation button
  const tokenCountSpan = document.getElementById("tokenCount");
  const tokenLimitSpan = document.getElementById("tokenLimit");
  const errorAlert = document.getElementById("errorAlert");

  // Configure marked + highlight.js
  marked.setOptions({
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return hljs.highlightAuto(code).value;
    }
  });

  // Function to count tokens (simple word count)
  function countTokens(text) {
    if (!text) return 0;
    return text.trim().split(/\s+/).length;
  }

  // Update token count display based on current input and selected model
  function updateTokenInfo() {
    const text = questionInput.value;
    const tokens = countTokens(text);
    tokenCountSpan.textContent = tokens;

    // Set token limit based on selected model
    const model = modelSelect.value;
    // Hardcoded limits for demo; ideally fetch from backend or config
    const modelLimits = {
      "chatgpt-4o-latest": 8192,
      "o4-mini": 2048,
      "chatgpt-3.5-turbo": 4096
    };
    const limit = modelLimits[model] || 4096;
    tokenLimitSpan.textContent = limit;

    // Change color if close to limit
    if (tokens > limit) {
      tokenCountSpan.style.color = "red";
      statusMsg.textContent = "¡Has excedido el límite de tokens para este modelo!";
      sendBtn.disabled = true;
    } else if (tokens > limit * 0.8) {
      tokenCountSpan.style.color = "orange";
      statusMsg.textContent = "Cuidado: te estás acercando al límite de tokens.";
      sendBtn.disabled = false;
    } else {
      tokenCountSpan.style.color = "";
      statusMsg.textContent = "";
      sendBtn.disabled = false;
    }
  }

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

  // Update token info on input and model change
  questionInput.addEventListener("input", updateTokenInfo);
  modelSelect.addEventListener("change", updateTokenInfo);

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

    // Clear previous error alert
    errorAlert.classList.add("d-none");
    errorAlert.textContent = "";

    // --- Optimistic UI Update: Display user message immediately ---
    const chatContainer = document.getElementById("chatContainer");
    const userDiv = document.createElement("div");
    userDiv.classList.add("chat-message", "chat-user");
    const labelYou = document.createElement("strong");
    labelYou.textContent = "Tú: ";
    userDiv.appendChild(labelYou);
    userDiv.appendChild(document.createTextNode(pregunta));
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
      // 3) Aquí llamamos a nuestro streaming
      await sendWithStream(currentConvId, pregunta, modelSelect.value);
      statusMsg.textContent = "¡Listo!";
    } catch (err) {
      console.error(err);
      statusMsg.textContent = "Error en el streaming.";
      // Show error alert if error response has JSON with error_code and error
      if (err.response && err.response.data) {
        const data = err.response.data;
        if (data.error_code && data.error) {
          errorAlert.textContent = data.error;
          errorAlert.classList.remove("d-none");
        }
      }
    }
  });

  const sidebar = document.getElementById("sidebar");
  const toggleSidebarBtn = document.getElementById("toggleSidebarBtn");

  if (toggleSidebarBtn && sidebar) {
    toggleSidebarBtn.addEventListener("click", () => {
      sidebar.classList.toggle("active");
      document.body.classList.toggle("sidebar-open");
    });

    // Ocultar sidebar al hacer clic fuera de él (solo móvil)
    document.addEventListener("click", function (e) {
      if (window.innerWidth <= 768 && sidebar.classList.contains("active")) {
        const clickedInside = sidebar.contains(e.target) || toggleSidebarBtn.contains(e.target);
        if (!clickedInside) {
          sidebar.classList.remove("active");
          document.body.classList.remove("sidebar-open");
        }
      }
    });
  }

});
