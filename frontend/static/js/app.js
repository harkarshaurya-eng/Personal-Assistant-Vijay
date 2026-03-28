const state = {
    token: localStorage.getItem("vijay_access_token") || "",
};

const statusGrid = document.getElementById("statusGrid");
const chatLog = document.getElementById("chatLog");
const authMessage = document.getElementById("authMessage");
const voiceMessage = document.getElementById("voiceMessage");
const commandList = document.getElementById("commandList");
const conversationHistory = document.getElementById("conversationHistory");
const actionHistory = document.getElementById("actionHistory");

function authHeaders() {
    return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

function setMessage(node, message) {
    node.textContent = message || "";
}

async function api(path, options = {}) {
    const response = await fetch(path, {
        headers: {
            "Content-Type": "application/json",
            ...authHeaders(),
            ...(options.headers || {}),
        },
        ...options,
    });

    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || payload.message || "Request failed");
    }
    return payload;
}

function addChatEntry(author, message, meta = "") {
    const item = document.createElement("div");
    item.className = "chat-entry";
    item.innerHTML = `<strong>${author}</strong><p>${message}</p>${meta ? `<small>${meta}</small>` : ""}`;
    chatLog.prepend(item);
}

function renderStatus(data) {
    const items = [
        ["Supabase", data.supabase_ready ? "Ready" : "Not configured"],
        ["Cloud logging", data.logging_ready ? "Ready" : "Local only"],
        ["Dry run", data.dry_run ? "Enabled" : "Disabled"],
        ["Voice mode", data.voice.mode],
        ["Voice lock", data.voice.lock_enabled ? "Enabled" : "Disabled"],
    ];

    statusGrid.innerHTML = "";
    items.forEach(([label, value]) => {
        const pill = document.createElement("div");
        pill.className = "status-pill";
        pill.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
        statusGrid.appendChild(pill);
    });
}

function renderCommands(commands) {
    commandList.innerHTML = "";
    commands.forEach((command) => {
        const item = document.createElement("li");
        item.textContent = `${command.trigger} -> ${command.steps.join(", ")}`;
        commandList.appendChild(item);
    });
}

function renderHistory(history) {
    conversationHistory.innerHTML = "";
    actionHistory.innerHTML = "";

    history.local.conversations.forEach((entry) => {
        const item = document.createElement("li");
        item.textContent = `${entry.timestamp}: ${entry.message} -> ${entry.response}`;
        conversationHistory.appendChild(item);
    });

    history.local.actions.forEach((entry) => {
        const item = document.createElement("li");
        item.textContent = `${entry.timestamp}: ${entry.action_type}`;
        actionHistory.appendChild(item);
    });
}

async function loadStatus() {
    const payload = await api("/api/status", { method: "GET" });
    renderStatus(payload);
}

async function loadCommands() {
    const payload = await api("/api/commands", { method: "GET" });
    renderCommands(payload.data.commands || []);
}

async function loadHistory() {
    const payload = await api("/api/history", { method: "GET" });
    renderHistory(payload.data);
}

document.getElementById("signupBtn").addEventListener("click", async () => {
    try {
        const payload = await api("/api/auth/signup", {
            method: "POST",
            body: JSON.stringify({
                email: document.getElementById("email").value,
                password: document.getElementById("password").value,
            }),
        });
        const token = payload.data.access_token || "";
        state.token = token;
        localStorage.setItem("vijay_access_token", token);
        setMessage(authMessage, payload.message);
    } catch (error) {
        setMessage(authMessage, error.message);
    }
});

document.getElementById("loginBtn").addEventListener("click", async () => {
    try {
        const payload = await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({
                email: document.getElementById("email").value,
                password: document.getElementById("password").value,
            }),
        });
        const token = payload.data.access_token || "";
        state.token = token;
        localStorage.setItem("vijay_access_token", token);
        setMessage(authMessage, payload.message);
        await loadHistory();
    } catch (error) {
        setMessage(authMessage, error.message);
    }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
    state.token = "";
    localStorage.removeItem("vijay_access_token");
    setMessage(authMessage, "Local session cleared.");
});

document.getElementById("trainVoiceBtn").addEventListener("click", async () => {
    try {
        const payload = await api("/api/voice/train", {
            method: "POST",
            body: JSON.stringify({
                sample_reference: document.getElementById("voiceSample").value,
            }),
        });
        setMessage(voiceMessage, payload.message);
        await loadStatus();
    } catch (error) {
        setMessage(voiceMessage, error.message);
    }
});

document.getElementById("saveCommandBtn").addEventListener("click", async () => {
    try {
        const payload = await api("/api/commands/learn", {
            method: "POST",
            body: JSON.stringify({
                instruction: document.getElementById("commandInput").value,
            }),
        });
        addChatEntry("Vijay", payload.message, payload.data.trigger || "");
        await loadCommands();
    } catch (error) {
        addChatEntry("System", error.message);
    }
});

async function sendChat(confirm = false) {
    const text = document.getElementById("chatInput").value;
    if (!text.trim()) {
        return;
    }

    addChatEntry("You", text);
    document.getElementById("chatInput").value = "";

    try {
        const payload = await api("/api/chat", {
            method: "POST",
            body: JSON.stringify({ message: text, confirm }),
        });
        const meta = payload.data.actions.length
            ? JSON.stringify(payload.data.actions)
            : "";
        addChatEntry("Vijay", payload.data.response, meta);
        await loadCommands();
        await loadHistory();
    } catch (error) {
        addChatEntry("System", error.message);
    }
}

document.getElementById("sendBtn").addEventListener("click", () => sendChat(false));
document.getElementById("confirmBtn").addEventListener("click", () => sendChat(true));
document.getElementById("refreshHistoryBtn").addEventListener("click", loadHistory);

loadStatus();
loadCommands();
loadHistory();

