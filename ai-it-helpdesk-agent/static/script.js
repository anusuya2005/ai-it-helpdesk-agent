const chatWindow = document.getElementById("chat-window");
const composer = document.getElementById("composer");
const input = document.getElementById("message-input");

// Persist a lightweight session id in the browser so the agent's memory
// can recognize returning users across page reloads.
function getSessionId() {
  let sessionId = localStorage.getItem("helpdesk_session_id");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem("helpdesk_session_id", sessionId);
  }
  return sessionId;
}

function appendMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = formatText(text);
  wrapper.appendChild(bubble);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return wrapper;
}

function formatText(text) {
  // minimal markdown-ish formatting: **bold**
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");
}

function appendMeta(wrapper, result) {
  const bits = [];
  if (result.category) bits.push(`Category: ${result.category}`);
  if (result.tools_used && result.tools_used.length) {
    bits.push(`Tools used: ${result.tools_used.map((t) => t.tool).join(", ")}`);
  }
  if (result.escalated) bits.push("Escalated to human support");
  if (!bits.length) return;
  const meta = document.createElement("div");
  meta.className = "meta-row";
  meta.textContent = bits.join(" · ");
  wrapper.appendChild(meta);
}

async function sendMessage(message) {
  appendMessage("user", message);

  const typing = appendMessage("assistant", "…thinking…");
  typing.querySelector(".bubble").classList.add("typing-indicator");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: getSessionId() }),
    });
    const data = await res.json();
    typing.remove();

    if (data.error) {
      appendMessage("assistant", `Error: ${data.error}`);
      return;
    }
    const wrapper = appendMessage("assistant", data.response);
    appendMeta(wrapper, data);
  } catch (err) {
    typing.remove();
    appendMessage("assistant", "Sorry, something went wrong reaching the server.");
  }
}

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  sendMessage(message);
});
