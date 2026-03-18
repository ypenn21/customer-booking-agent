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
 * @returns {Promise<string>} the assistant's reply content
 */
async function fetchCompletion() {
  const response = await fetch("/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "customers-agent",
      messages,
    }),
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

  try {
    const reply = await fetchCompletion();
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

function startNewChat() {
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
