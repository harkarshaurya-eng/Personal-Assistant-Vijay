const state = {
    token: localStorage.getItem("vijay_session_token") || "",
    me: null,
    publicConfig: null,
    status: null,
    adminUsers: [],
    selectedAdminUserId: null,
};

const statusGrid = document.getElementById("statusGrid");
const authMessage = document.getElementById("authMessage");
const sessionCard = document.getElementById("sessionCard");
const onboardingPanel = document.getElementById("onboardingPanel");
const onboardingMessage = document.getElementById("onboardingMessage");
const promptInput = document.getElementById("promptInput");
const promptMessage = document.getElementById("promptMessage");
const chatLog = document.getElementById("chatLog");
const voiceMessage = document.getElementById("voiceMessage");
const commandList = document.getElementById("commandList");
const conversationHistory = document.getElementById("conversationHistory");
const actionHistory = document.getElementById("actionHistory");
const adminSection = document.getElementById("admin");
const adminUsersList = document.getElementById("adminUsersList");
const adminUserTitle = document.getElementById("adminUserTitle");
const adminPromptInput = document.getElementById("adminPromptInput");
const adminConversationHistory = document.getElementById("adminConversationHistory");
const adminActionHistory = document.getElementById("adminActionHistory");
const adminOverviewNote = document.getElementById("adminOverviewNote");

function authHeaders() {
    return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

function setMessage(node, message) {
    node.textContent = message || "";
}

function show(node, visible) {
    node.classList.toggle("is-hidden", !visible);
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

function renderStatus() {
    if (!state.status) {
        return;
    }
    const items = [
        ["Google", state.status.google_ready ? "Ready" : "Missing client ID"],
        ["Groq", state.status.groq_ready ? "Ready" : "Missing API key"],
        ["Supabase", state.status.supabase_ready ? "Ready" : "Not configured"],
        ["Cloud logging", state.status.logging_ready ? "Ready" : "Local only"],
        ["Dry run", state.status.dry_run ? "Enabled" : "Disabled"],
        ["Voice lock", state.status.voice.lock_enabled ? "Enabled" : "Disabled"],
    ];

    statusGrid.innerHTML = "";
    items.forEach(([label, value]) => {
        const pill = document.createElement("div");
        pill.className = "status-pill";
        pill.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
        statusGrid.appendChild(pill);
    });
}

function renderSession() {
    if (!state.me) {
        sessionCard.innerHTML = "";
        show(sessionCard, false);
        show(onboardingPanel, false);
        show(adminSection, false);
        promptInput.value = "";
        return;
    }

    sessionCard.innerHTML = `
        <div class="user-head">
            <div>
                <strong>${state.me.name || state.me.email}</strong>
                <p>${state.me.email}</p>
            </div>
            <span class="role-badge ${state.me.role}">${state.me.role}</span>
        </div>
        <p>Provider: ${state.me.provider}</p>
        <p>Device access: ${state.me.device_access_enabled ? "enabled" : "disabled"}</p>
    `;
    promptInput.value = state.me.system_prompt || "";
    show(sessionCard, true);
    show(onboardingPanel, !state.me.device_access_configured);
    show(adminSection, state.me.role === "admin");
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

function renderAdminUsers(users) {
    adminUsersList.innerHTML = "";
    adminOverviewNote.textContent = `${users.length} user account(s) available in this Vijay instance.`;
    users.forEach((user) => {
        const item = document.createElement("li");
        item.className = `admin-user-item ${state.selectedAdminUserId === user.id ? "selected" : ""}`;
        item.innerHTML = `
            <button type="button" data-user-id="${user.id}" class="user-select-btn">
                <strong>${user.name || user.email}</strong>
                <span>${user.email}</span>
                <small>${user.role} • ${user.conversation_count} chats • ${user.action_count} actions</small>
            </button>
        `;
        adminUsersList.appendChild(item);
    });

    document.querySelectorAll(".user-select-btn").forEach((button) => {
        button.addEventListener("click", () => loadAdminUser(button.dataset.userId));
    });
}

function renderAdminUserDetail(data) {
    const user = data.user;
    state.selectedAdminUserId = user.id;
    adminUserTitle.textContent = `${user.name || user.email} (${user.role})`;
    adminPromptInput.value = user.system_prompt || "";

    adminConversationHistory.innerHTML = "";
    adminActionHistory.innerHTML = "";

    data.local.conversations.forEach((entry) => {
        const item = document.createElement("li");
        item.textContent = `${entry.timestamp}: ${entry.message} -> ${entry.response}`;
        adminConversationHistory.appendChild(item);
    });

    data.local.actions.forEach((entry) => {
        const item = document.createElement("li");
        item.textContent = `${entry.timestamp}: ${entry.action_type}`;
        adminActionHistory.appendChild(item);
    });
}

async function loadPublicConfig() {
    const payload = await api("/api/public-config", { method: "GET" });
    state.publicConfig = payload;
}

async function loadStatus() {
    state.status = await api("/api/status", { method: "GET" });
    renderStatus();
}

async function loadSession() {
    if (!state.token) {
        state.me = null;
        renderSession();
        return;
    }

    try {
        const payload = await api("/api/auth/session", { method: "GET" });
        state.me = payload.data.user;
    } catch (error) {
        state.token = "";
        state.me = null;
        localStorage.removeItem("vijay_session_token");
        setMessage(authMessage, error.message);
    }
    renderSession();
}

async function loadCommands() {
    const payload = await api("/api/commands", { method: "GET" });
    renderCommands(payload.data.commands || []);
}

async function loadHistory() {
    if (!state.me) {
        conversationHistory.innerHTML = "";
        actionHistory.innerHTML = "";
        return;
    }
    const payload = await api("/api/history", { method: "GET" });
    renderHistory(payload.data);
}

async function loadAdminOverview() {
    if (!state.me || state.me.role !== "admin") {
        return;
    }
    const payload = await api("/api/admin/overview", { method: "GET" });
    state.adminUsers = payload.data.users || [];
    renderAdminUsers(state.adminUsers);
    if (state.adminUsers.length && !state.selectedAdminUserId) {
        await loadAdminUser(state.adminUsers[0].id);
    }
}

async function loadAdminUser(userId) {
    if (!userId) {
        return;
    }
    const payload = await api(`/api/admin/users/${userId}`, { method: "GET" });
    renderAdminUserDetail(payload.data);
    renderAdminUsers(state.adminUsers);
}

async function handleGoogleCredentialResponse(credential) {
    try {
        const payload = await api("/api/auth/google", {
            method: "POST",
            body: JSON.stringify({ credential }),
        });
        state.token = payload.data.session_token;
        localStorage.setItem("vijay_session_token", state.token);
        state.me = payload.data.user;
        renderSession();
        setMessage(authMessage, payload.message);
        await loadStatus();
        await loadHistory();
        await loadAdminOverview();
        if (payload.data.redirect_hash === "admin") {
            window.location.hash = "admin";
            adminSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    } catch (error) {
        setMessage(authMessage, error.message);
    }
}

function initializeGoogleButton() {
    if (!state.publicConfig?.google_enabled) {
        setMessage(authMessage, "Add GOOGLE_CLIENT_ID in .env to enable Google sign-in.");
        return;
    }
    if (!window.google || !document.getElementById("googleButton")) {
        window.setTimeout(initializeGoogleButton, 250);
        return;
    }

    window.google.accounts.id.initialize({
        client_id: state.publicConfig.google_client_id,
        callback: (response) => handleGoogleCredentialResponse(response.credential),
        auto_select: true,
        ux_mode: "popup",
    });
    window.google.accounts.id.renderButton(
        document.getElementById("googleButton"),
        {
            theme: "outline",
            size: "large",
            shape: "pill",
            text: "continue_with",
            width: 320,
        }
    );
}

document.getElementById("logoutBtn").addEventListener("click", async () => {
    try {
        await api("/api/auth/logout", { method: "POST" });
    } catch (error) {
        console.error(error);
    }
    state.token = "";
    state.me = null;
    state.selectedAdminUserId = null;
    localStorage.removeItem("vijay_session_token");
    if (window.google?.accounts?.id) {
        window.google.accounts.id.disableAutoSelect();
    }
    renderSession();
    await loadStatus();
    await loadHistory();
    setMessage(authMessage, "Signed out.");
});

document.getElementById("allowDeviceBtn").addEventListener("click", async () => {
    try {
        const payload = await api("/api/me/device-permission", {
            method: "POST",
            body: JSON.stringify({ enabled: true }),
        });
        state.me = payload.data.user;
        renderSession();
        setMessage(onboardingMessage, payload.message);
        await loadStatus();
    } catch (error) {
        setMessage(onboardingMessage, error.message);
    }
});

document.getElementById("denyDeviceBtn").addEventListener("click", async () => {
    try {
        const payload = await api("/api/me/device-permission", {
            method: "POST",
            body: JSON.stringify({ enabled: false }),
        });
        state.me = payload.data.user;
        renderSession();
        setMessage(onboardingMessage, payload.message);
        await loadStatus();
    } catch (error) {
        setMessage(onboardingMessage, error.message);
    }
});

document.getElementById("savePromptBtn").addEventListener("click", async () => {
    if (!state.me) {
        setMessage(promptMessage, "Sign in first.");
        return;
    }
    try {
        const payload = await api("/api/me/system-prompt", {
            method: "POST",
            body: JSON.stringify({ prompt: promptInput.value }),
        });
        state.me = payload.data.user;
        renderSession();
        setMessage(promptMessage, payload.message);
    } catch (error) {
        setMessage(promptMessage, error.message);
    }
});

document.getElementById("trainVoiceBtn").addEventListener("click", async () => {
    if (!state.me) {
        setMessage(voiceMessage, "Sign in first.");
        return;
    }
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
    if (!state.me) {
        addChatEntry("System", "Sign in first.");
        return;
    }
    try {
        const payload = await api("/api/commands/learn", {
            method: "POST",
            body: JSON.stringify({
                instruction: document.getElementById("commandInput").value,
            }),
        });
        addChatEntry("Vijay", payload.message, payload.data.trigger || "");
        await loadCommands();
        await loadHistory();
    } catch (error) {
        addChatEntry("System", error.message);
    }
});

async function sendChat(confirm = false) {
    const text = document.getElementById("chatInput").value;
    if (!text.trim()) {
        return;
    }
    if (!state.me) {
        addChatEntry("System", "Sign in with Google first.");
        return;
    }

    addChatEntry("You", text);
    document.getElementById("chatInput").value = "";

    try {
        const payload = await api("/api/chat", {
            method: "POST",
            body: JSON.stringify({ message: text, confirm }),
        });
        const meta = payload.data.actions.length ? JSON.stringify(payload.data.actions) : "";
        addChatEntry("Vijay", payload.data.response, meta);
        await loadCommands();
        await loadHistory();
        if (state.me.role === "admin") {
            await loadAdminOverview();
        }
    } catch (error) {
        addChatEntry("System", error.message);
    }
}

document.getElementById("sendBtn").addEventListener("click", () => sendChat(false));
document.getElementById("confirmBtn").addEventListener("click", () => sendChat(true));
document.getElementById("refreshHistoryBtn").addEventListener("click", loadHistory);

document.getElementById("saveAdminPromptBtn").addEventListener("click", async () => {
    if (!state.selectedAdminUserId) {
        setMessage(adminOverviewNote, "Select a user first.");
        return;
    }
    try {
        const payload = await api(`/api/admin/users/${state.selectedAdminUserId}`, {
            method: "POST",
            body: JSON.stringify({ prompt: adminPromptInput.value }),
        });
        setMessage(adminOverviewNote, payload.message);
        await loadAdminOverview();
        await loadAdminUser(state.selectedAdminUserId);
    } catch (error) {
        setMessage(adminOverviewNote, error.message);
    }
});

document.getElementById("enableAdminDeviceBtn").addEventListener("click", async () => {
    if (!state.selectedAdminUserId) {
        setMessage(adminOverviewNote, "Select a user first.");
        return;
    }
    try {
        const payload = await api(`/api/admin/users/${state.selectedAdminUserId}`, {
            method: "POST",
            body: JSON.stringify({ device_access_enabled: true }),
        });
        setMessage(adminOverviewNote, payload.message);
        await loadAdminOverview();
        await loadAdminUser(state.selectedAdminUserId);
    } catch (error) {
        setMessage(adminOverviewNote, error.message);
    }
});

document.getElementById("disableAdminDeviceBtn").addEventListener("click", async () => {
    if (!state.selectedAdminUserId) {
        setMessage(adminOverviewNote, "Select a user first.");
        return;
    }
    try {
        const payload = await api(`/api/admin/users/${state.selectedAdminUserId}`, {
            method: "POST",
            body: JSON.stringify({ device_access_enabled: false }),
        });
        setMessage(adminOverviewNote, payload.message);
        await loadAdminOverview();
        await loadAdminUser(state.selectedAdminUserId);
    } catch (error) {
        setMessage(adminOverviewNote, error.message);
    }
});

async function bootstrap() {
    await loadPublicConfig();
    await loadStatus();
    await loadSession();
    await loadCommands();
    if (state.me) {
        await loadHistory();
        if (state.me.role === "admin") {
            await loadAdminOverview();
        }
    }
    initializeGoogleButton();
}

bootstrap();
