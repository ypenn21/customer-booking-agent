/**
 * chat.js — Customer Booking Assistant
 *
 * Manages the chat conversation:
 *  - Maintains a messages[] array (OpenAI format)
 *  - POSTs to /v1/chat/completions
 *  - Renders user + agent bubbles
 *  - Handles sidebar toggle, suggestion chips, auto-resize textarea
 */

"use strict";

// ── State ──────────────────────────────────────────────────────────────────────
/** @type {{ role: "system"|"user"|"assistant", content: string }[]} */
let messages = [];

/** The active session ID fetched from localStorage or API response. */
let currentSessionId = localStorage.getItem("currentSessionId") || null;

/**
 * True only for the very first message after "New Chat" was clicked.
 * Signals the backend to create a brand-new Agent Engine session.
 */
let forceNewSession = false;

// ── DOM refs ───────────────────────────────────────────────────────────────────
const feed          = document.getElementById("messages-container");
const welcome       = document.getElementById("welcome-screen");
const input         = document.getElementById("chat-input");
const btnSend       = document.getElementById("btn-send");
const btnNewChat    = document.getElementById("btn-new-chat");
const btnToggle     = document.getElementById("btn-sidebar-toggle");
const sidebar       = document.getElementById("sidebar");
const suggestions   = document.querySelectorAll(".suggestion-chip");

// ── Helpers ────────────────────────────────────────────────────────────────────

/** Escape HTML to safely render text inside bubbles. */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

/** Scroll the feed to the bottom. */
function scrollToBottom() {
  feed.scrollTo({ top: feed.scrollHeight, behavior: "smooth" });
}

/** Auto-resize textarea up to a max height. */
function autoResize() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
}

// ── Render ─────────────────────────────────────────────────────────────────────

/**
 * Append a single message bubble to the feed.
 * @param {"user"|"assistant"} role
 * @param {string} content
 * @returns {HTMLElement} the bubble element
 */
function appendBubble(role, content) {
  if (welcome) welcome.style.display = "none";

  const row = document.createElement("div");
  row.className = `message-row ${role === "user" ? "user" : ""}`;

  const avatarLabel = role === "user" ? "You" : "✦";
  const bubbleClass = role === "user" ? "user" : "agent";
  const avatarClass = role === "user" ? "user" : "agent";

  row.innerHTML = `
    <div class="avatar ${avatarClass}">${avatarLabel[0]}</div>
    <div class="bubble ${bubbleClass}">${escapeHtml(content)}</div>
  `;

  feed.appendChild(row);
  scrollToBottom();
  return row;
}

/** Show the animated typing indicator. Returns the row element to remove later. */
function showTyping() {
  if (welcome) welcome.style.display = "none";

  const row = document.createElement("div");
  row.className = "message-row";
  row.id = "typing-row";
  row.innerHTML = `
    <div class="avatar agent">✦</div>
    <div class="bubble agent typing-indicator">
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    </div>
  `;
  feed.appendChild(row);
  scrollToBottom();
  return row;
}

/** Remove the typing indicator row from the DOM. */
function removeTyping() {
  const row = document.getElementById("typing-row");
  if (row) row.remove();
}

// ── API ────────────────────────────────────────────────────────────────────────

/**
 * POST to /v1/chat/completions (OpenAI-compatible).
 * @param {boolean} [newSession=false] - If true, instructs backend to start a fresh session.
 * @returns {Promise<string>} the assistant's reply content
 */
async function fetchCompletion(newSession = false) {
  const body = {
    model: "customers-agent",
    messages,
    force_new_session: newSession,
  };
  
  if (currentSessionId && !newSession) {
    body.session_id = currentSessionId;
  }

  const response = await fetch("/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }

  const data = await response.json();
  
  if (data.session_id) {
    currentSessionId = data.session_id;
    localStorage.setItem("currentSessionId", currentSessionId);
    refreshSessionList();
  }

  return data.choices?.[0]?.message?.content ?? "No response from agent.";
}

// ── Send logic ─────────────────────────────────────────────────────────────────

/** @param {string} text */
async function sendMessage(text) {
  const userText = text.trim();
  if (!userText) return;

  // Clear input and disable controls
  input.value = "";
  input.style.height = "auto";
  btnSend.disabled = true;

  // Push to message history and render user bubble
  messages.push({ role: "user", content: userText });
  appendBubble("user", userText);

  // Show typing indicator
  showTyping();

  // Capture & clear the flag so only the first post-reset message forces a new session
  const isNew = forceNewSession;
  forceNewSession = false;

  try {
    const reply = await fetchCompletion(isNew);
    removeTyping();
    messages.push({ role: "assistant", content: reply });
    appendBubble("assistant", reply);
  } catch (err) {
    removeTyping();
    const errMsg = `⚠️ Error: ${err.message}`;
    messages.push({ role: "assistant", content: errMsg });
    appendBubble("assistant", errMsg);
  }
}

// ── Reset ──────────────────────────────────────────────────────────────────────

async function startNewChat() {
  // Mark that the next message should start a fresh session
  forceNewSession = true;
  currentSessionId = null;
  localStorage.removeItem("currentSessionId");
  refreshSessionList();

  messages = [];
  // Clear message rows but keep the welcome screen element
  [...feed.children].forEach(child => {
    if (child.id !== "welcome-screen") child.remove();
  });
  if (welcome) welcome.style.display = "";
  input.value = "";
  input.style.height = "auto";
  btnSend.disabled = true;
}

// ── Event listeners ────────────────────────────────────────────────────────────

// Send on button click
btnSend.addEventListener("click", () => sendMessage(input.value));

// Send on Enter (Shift+Enter for newline)
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage(input.value);
  }
});

// Enable/disable send button based on input content
input.addEventListener("input", () => {
  btnSend.disabled = input.value.trim().length === 0;
  autoResize();
});

// New chat
btnNewChat.addEventListener("click", startNewChat);

// Sidebar toggle
btnToggle.addEventListener("click", () => {
  sidebar.classList.toggle("open");
});

// Suggestion chips
suggestions.forEach(chip => {
  chip.addEventListener("click", () => {
    const prompt = chip.dataset.prompt;
    if (prompt) sendMessage(prompt);
    // Close sidebar on mobile after selecting a chip
    sidebar.classList.remove("open");
  });
});

// Close sidebar when clicking outside on mobile
document.addEventListener("click", (e) => {
  if (
    window.innerWidth <= 700 &&
    sidebar.classList.contains("open") &&
    !sidebar.contains(e.target) &&
    e.target !== btnToggle
  ) {
    sidebar.classList.remove("open");
  }
});

// ── Sessions Management ────────────────────────────────────────

async function loadSessionHistory(sessionId) {
  try {
    const res = await fetch(`/v1/sessions/${sessionId}/messages`);
    if (!res.ok) return;
    const data = await res.json();
    
    // Clear feed
    messages = [];
    [...feed.children].forEach(child => {
      if (child.id !== "welcome-screen") child.remove();
    });
    
    if (data.messages && data.messages.length > 0) {
      if (welcome) welcome.style.display = "none";
      
      // Events from the backend are chronological
      const history = data.messages;
      
      history.forEach(msg => {
        const mappedRole = msg.role === "user" ? "user" : "assistant";
        messages.push({ role: mappedRole, content: msg.content });
        appendBubble(mappedRole, msg.content);
      });
    } else {
      if (welcome) welcome.style.display = "none";
      appendBubble("assistant", "Session context resumed. No messages found.");
    }
  } catch (err) {
    console.error("Failed to load session history:", err);
  }
}

async function refreshSessionList() {
  try {
    const res = await fetch("/v1/sessions");
    if (!res.ok) return;
    const data = await res.json();
    
    const container = document.getElementById("session-history-container");
    const list = document.getElementById("session-list");
    if (!container || !list) return;

    if (data.sessions && data.sessions.length > 0) {
      container.style.display = "flex";
      list.innerHTML = "";
      
      data.sessions.forEach(session => {
        const btn = document.createElement("button");
        btn.className = "session-chip";
        btn.textContent = `Session: ${session.id.substring(0, 8)}...`;
        
        if (session.id === currentSessionId) {
          btn.classList.add("active");
        }
        
        btn.onclick = () => {
          currentSessionId = session.id;
          localStorage.setItem("currentSessionId", currentSessionId);
          loadSessionHistory(currentSessionId);
          refreshSessionList();
          
          if (window.innerWidth <= 700) {
            sidebar.classList.remove("open");
          }
        };
        list.appendChild(btn);
      });
    } else {
      container.style.display = "none";
    }
  } catch(e) { 
    console.warn("Failed to list sessions:", e); 
  }
}

// Initial fetch on load
refreshSessionList();
if (currentSessionId) {
  loadSessionHistory(currentSessionId);
}
