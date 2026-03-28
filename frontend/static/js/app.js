const state = {
    token: localStorage.getItem("vijay_session_token") || "",
    me: null,
    publicConfig: null,
    status: null,
    adminUsers: [],
    selectedAdminUserId: null,
    recorder: {
        mode: null,
        isRecording: false,
        stream: null,
        context: null,
        source: null,
        processor: null,
        sink: null,
        chunks: [],
        sampleRate: 44100,
    },
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
const voiceStatusNote = document.getElementById("voiceStatusNote");
const voiceCommandMessage = document.getElementById("voiceCommandMessage");
const voiceThresholdInput = document.getElementById("voiceThreshold");
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
const startEnrollBtn = document.getElementById("startEnrollBtn");
const stopEnrollBtn = document.getElementById("stopEnrollBtn");
const startVoiceCommandBtn = document.getElementById("startVoiceCommandBtn");
const stopVoiceCommandBtn = document.getElementById("stopVoiceCommandBtn");

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
    const headers = {
        ...authHeaders(),
        ...(options.headers || {}),
    };

    if (
        options.body &&
        !(options.body instanceof Blob) &&
        !(options.body instanceof FormData) &&
        !headers["Content-Type"] &&
        !headers["content-type"]
    ) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(path, {
        ...options,
        headers,
    });

    let payload = {};
    try {
        payload = await response.json();
    } catch (error) {
        payload = { message: response.statusText || "Request failed" };
    }

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

    const voiceModelsValue = state.status.voice.dependencies_ready ? "Ready" : "Install deps";
    const voiceProfileValue = state.me
        ? (state.status.voice.user_has_profile ? "Trained" : "Not trained")
        : `${state.status.voice.profile_count} profile(s)`;

    const items = [
        ["Google", state.status.google_ready ? "Ready" : "Missing client ID"],
        ["Groq", state.status.groq_ready ? "Ready" : "Missing API key"],
        ["Supabase", state.status.supabase_ready ? "Ready" : "Not configured"],
        ["Cloud logging", state.status.logging_ready ? "Ready" : "Local only"],
        ["Dry run", state.status.dry_run ? "Enabled" : "Disabled"],
        ["Voice models", voiceModelsValue],
        ["Voice lock", state.status.voice.lock_enabled ? "Enabled" : "Disabled"],
        ["Voice profile", voiceProfileValue],
    ];

    statusGrid.innerHTML = "";
    items.forEach(([label, value]) => {
        const pill = document.createElement("div");
        pill.className = "status-pill";
        pill.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
        statusGrid.appendChild(pill);
    });

    renderVoiceStatus();
}

function renderSession() {
    if (!state.me) {
        sessionCard.innerHTML = "";
        show(sessionCard, false);
        show(onboardingPanel, false);
        show(adminSection, false);
        promptInput.value = "";
        renderVoiceStatus();
        return;
    }

    const voiceProfileLabel = state.status?.voice?.user_has_profile ? "trained" : "not trained";
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
        <p>Voice profile: ${voiceProfileLabel}</p>
    `;
    promptInput.value = state.me.system_prompt || "";
    show(sessionCard, true);
    show(onboardingPanel, !state.me.device_access_configured);
    show(adminSection, state.me.role === "admin");
    renderVoiceStatus();
}

function renderVoiceStatus() {
    if (!state.status?.voice) {
        return;
    }
    voiceThresholdInput.value = Number(state.status.voice.similarity_threshold || 0.8).toFixed(2);

    const notes = [];
    if (state.me) {
        notes.push(
            state.status.voice.user_has_profile
                ? `Voice profile trained${state.status.voice.user_trained_at ? ` on ${new Date(state.status.voice.user_trained_at).toLocaleString()}` : ""}.`
                : "No voice profile has been trained for this account yet."
        );
    }
    notes.push(state.status.voice.dependency_message);
    setMessage(voiceStatusNote, notes.filter(Boolean).join(" "));
    syncRecordingButtons();
}

function syncRecordingButtons() {
    const isRecording = state.recorder.isRecording;
    startEnrollBtn.disabled = isRecording;
    startVoiceCommandBtn.disabled = isRecording;
    stopEnrollBtn.disabled = !isRecording || state.recorder.mode !== "enroll";
    stopVoiceCommandBtn.disabled = !isRecording || state.recorder.mode !== "command";
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
    if (state.me) {
        renderSession();
    }
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

function writeString(view, offset, value) {
    for (let index = 0; index < value.length; index += 1) {
        view.setUint8(offset + index, value.charCodeAt(index));
    }
}

function floatTo16BitPCM(view, offset, input) {
    for (let index = 0; index < input.length; index += 1) {
        const sample = Math.max(-1, Math.min(1, input[index]));
        view.setInt16(offset + (index * 2), sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    }
}

function mergeAudioChunks(chunks) {
    const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    chunks.forEach((chunk) => {
        merged.set(chunk, offset);
        offset += chunk.length;
    });
    return merged;
}

function encodeWav(chunks, sampleRate) {
    const samples = mergeAudioChunks(chunks);
    const buffer = new ArrayBuffer(44 + (samples.length * 2));
    const view = new DataView(buffer);

    writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + (samples.length * 2), true);
    writeString(view, 8, "WAVE");
    writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, "data");
    view.setUint32(40, samples.length * 2, true);
    floatTo16BitPCM(view, 44, samples);

    return new Blob([buffer], { type: "audio/wav" });
}

async function resetRecorder() {
    if (!state.recorder.isRecording) {
        syncRecordingButtons();
        return null;
    }

    const snapshot = { ...state.recorder };
    state.recorder = {
        mode: null,
        isRecording: false,
        stream: null,
        context: null,
        source: null,
        processor: null,
        sink: null,
        chunks: [],
        sampleRate: 44100,
    };
    syncRecordingButtons();

    snapshot.processor?.disconnect();
    snapshot.source?.disconnect();
    snapshot.sink?.disconnect();
    snapshot.stream?.getTracks().forEach((track) => track.stop());
    if (snapshot.context) {
        await snapshot.context.close();
    }

    return {
        blob: encodeWav(snapshot.chunks, snapshot.sampleRate),
        mode: snapshot.mode,
    };
}

async function startRecording(mode) {
    if (!state.me) {
        throw new Error("Sign in with Google first.");
    }
    if (!state.status?.voice?.dependencies_ready) {
        throw new Error(state.status?.voice?.dependency_message || "Voice models are not ready yet.");
    }
    if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("This browser does not support microphone capture for Vijay.");
    }
    if (state.recorder.isRecording) {
        throw new Error("A recording is already in progress.");
    }

    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
        throw new Error("This browser does not support Web Audio recording.");
    }

    const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
        },
    });
    const context = new AudioContextClass();
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    const sink = context.createGain();
    sink.gain.value = 0;

    const chunks = [];
    processor.onaudioprocess = (event) => {
        chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    };

    source.connect(processor);
    processor.connect(sink);
    sink.connect(context.destination);

    state.recorder = {
        mode,
        isRecording: true,
        stream,
        context,
        source,
        processor,
        sink,
        chunks,
        sampleRate: context.sampleRate,
    };
    syncRecordingButtons();
}

async function uploadEnrollment(blob) {
    setMessage(voiceMessage, "Uploading enrollment sample to Vijay...");
    const payload = await api("/api/voice/train/audio", {
        method: "POST",
        headers: {
            "Content-Type": "audio/wav",
            "X-Audio-Filename": "enrollment.wav",
        },
        body: blob,
    });
    const transcript = payload.data?.transcript ? ` Transcript: ${payload.data.transcript}` : "";
    setMessage(voiceMessage, `${payload.message}${transcript}`);
    await loadStatus();
}

async function uploadVoiceCommand(blob) {
    setMessage(voiceCommandMessage, "Verifying your voice and transcribing the command...");
    const payload = await api("/api/voice/command", {
        method: "POST",
        headers: {
            "Content-Type": "audio/wav",
            "X-Audio-Filename": "command.wav",
        },
        body: blob,
    });

    const voice = payload.data?.voice || {};
    const similarity = voice.similarity
        ? `Similarity ${voice.similarity} / threshold ${voice.threshold}`
        : "";

    if (payload.data?.transcript) {
        addChatEntry("You (voice)", payload.data.transcript, similarity);
        const meta = payload.data.actions?.length ? JSON.stringify(payload.data.actions) : similarity;
        addChatEntry("Vijay", payload.data.response || payload.message, meta);
        await loadCommands();
        await loadHistory();
        if (state.me?.role === "admin") {
            await loadAdminOverview();
        }
    } else {
        addChatEntry("Vijay", payload.message, similarity);
    }

    setMessage(voiceCommandMessage, payload.message);
    await loadStatus();
}

document.getElementById("logoutBtn").addEventListener("click", async () => {
    try {
        await api("/api/auth/logout", { method: "POST" });
    } catch (error) {
        console.error(error);
    }
    await resetRecorder();
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

document.getElementById("saveVoiceThresholdBtn").addEventListener("click", async () => {
    if (!state.me) {
        setMessage(voiceMessage, "Sign in first.");
        return;
    }
    try {
        const payload = await api("/api/voice/settings", {
            method: "POST",
            body: JSON.stringify({
                similarity_threshold: Number(voiceThresholdInput.value),
            }),
        });
        setMessage(voiceMessage, payload.message);
        await loadStatus();
    } catch (error) {
        setMessage(voiceMessage, error.message);
    }
});

startEnrollBtn.addEventListener("click", async () => {
    try {
        await startRecording("enroll");
        setMessage(voiceMessage, "Recording enrollment sample. Speak naturally, then click Stop Enrollment.");
        setMessage(voiceCommandMessage, "");
    } catch (error) {
        setMessage(voiceMessage, error.message);
    }
});

stopEnrollBtn.addEventListener("click", async () => {
    try {
        const recording = await resetRecorder();
        if (!recording || recording.mode !== "enroll") {
            setMessage(voiceMessage, "No enrollment recording is active.");
            return;
        }
        await uploadEnrollment(recording.blob);
    } catch (error) {
        setMessage(voiceMessage, error.message);
    }
});

startVoiceCommandBtn.addEventListener("click", async () => {
    try {
        await startRecording("command");
        setMessage(voiceCommandMessage, "Recording secure voice command. Speak, then click Stop Voice Command.");
        setMessage(voiceMessage, "");
    } catch (error) {
        setMessage(voiceCommandMessage, error.message);
    }
});

stopVoiceCommandBtn.addEventListener("click", async () => {
    try {
        const recording = await resetRecorder();
        if (!recording || recording.mode !== "command") {
            setMessage(voiceCommandMessage, "No voice command recording is active.");
            return;
        }
        await uploadVoiceCommand(recording.blob);
    } catch (error) {
        setMessage(voiceCommandMessage, error.message);
        addChatEntry("System", error.message);
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
    syncRecordingButtons();
}

bootstrap();
