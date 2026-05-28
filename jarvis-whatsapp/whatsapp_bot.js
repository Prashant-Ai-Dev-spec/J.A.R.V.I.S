"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const axios = require("axios");
const QRCode = require("qrcode");
const qrcode = require("qrcode-terminal");
const { Client, LocalAuth } = require("whatsapp-web.js");

const ROOT_DIR = path.resolve(__dirname, "..");
const CONFIG_PATH = path.join(ROOT_DIR, "jarvis_config.json");
const RUNTIME_DIR = path.join(ROOT_DIR, ".jarvis_runtime");
const SESSION_DIR = path.join(RUNTIME_DIR, "whatsapp_session");
const QR_IMAGE_PATH = path.join(RUNTIME_DIR, "whatsapp_qr.png");

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
  } catch (_err) {
    return {};
  }
}

const cfg = loadConfig();
const PORT = Number(process.env.JARVIS_WHATSAPP_PORT || cfg.whatsapp_bridge_port || 3001);
const JARVIS_URL = String(
  process.env.JARVIS_WHATSAPP_INCOMING_URL ||
    cfg.whatsapp_bridge_incoming_url ||
    "http://127.0.0.1:8765/api/whatsapp/incoming"
);
const WEB_TOKEN = String(process.env.JARVIS_WEB_TOKEN || cfg.web_api_token || "").trim();
const CLIENT_ID = String(process.env.JARVIS_WHATSAPP_CLIENT_ID || cfg.whatsapp_bridge_client_id || "jarvis").trim() || "jarvis";

let ready = false;
let lastQrAt = 0;
let lastError = "";
let me = "";
let initializing = false;
const activeCalls = new Map();

fs.mkdirSync(RUNTIME_DIR, { recursive: true });
fs.mkdirSync(SESSION_DIR, { recursive: true });

function findBrowserExecutable() {
  const configured = String(process.env.JARVIS_BROWSER_PATH || cfg.whatsapp_bridge_browser_path || "").trim();
  const candidates = [
    configured,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    path.join(process.env.LOCALAPPDATA || "", "Google\\Chrome\\Application\\chrome.exe"),
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  return candidates.find(candidate => {
    try {
      return fs.existsSync(candidate);
    } catch (_err) {
      return false;
    }
  });
}

const browserPath = findBrowserExecutable();

const client = new Client({
  authStrategy: new LocalAuth({
    clientId: CLIENT_ID,
    dataPath: SESSION_DIR,
  }),
  puppeteer: {
    headless: cfg.whatsapp_bridge_headless !== false,
    executablePath: browserPath || undefined,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-extensions",
      "--disable-gpu",
      "--window-size=1280,900",
    ],
  },
});

function jsonResponse(res, status, payload) {
  const body = Buffer.from(JSON.stringify(payload));
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Content-Length": body.length,
  });
  res.end(body);
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", chunk => chunks.push(chunk));
    req.on("end", () => {
      try {
        const raw = Buffer.concat(chunks).toString("utf8").trim();
        resolve(raw ? JSON.parse(raw) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

function postToJarvis(payload) {
  const headers = { "Content-Type": "application/json" };
  if (WEB_TOKEN) {
    headers["X-Jarvis-Token"] = WEB_TOKEN;
  }
  return axios.post(JARVIS_URL, payload, { headers, timeout: 5000 });
}

function isGroupChat(id) {
  return String(id || "").includes("@g.us");
}

client.on("qr", qr => {
  lastQrAt = Date.now();
  console.log("[JARVIS-WA] Scan this WhatsApp QR from Linked Devices:");
  qrcode.generate(qr, { small: true });
  QRCode.toFile(QR_IMAGE_PATH, qr, { width: 420, margin: 2 })
    .then(() => console.log(`[JARVIS-WA] QR image saved: ${QR_IMAGE_PATH}`))
    .catch(err => {
      lastError = err?.message || String(err);
      console.error("[JARVIS-WA] QR image save failed:", lastError);
    });
});

client.on("ready", async () => {
  ready = true;
  initializing = false;
  lastError = "";
  try {
    me = client.info?.wid?._serialized || client.info?.wid?.user || "";
  } catch (_err) {
    me = "";
  }
  console.log("[JARVIS-WA] WhatsApp connected.");
});

client.on("authenticated", () => {
  console.log("[JARVIS-WA] Authenticated.");
});

client.on("auth_failure", message => {
  ready = false;
  initializing = false;
  lastError = String(message || "Authentication failed");
  console.error("[JARVIS-WA] Auth failure:", lastError);
});

client.on("disconnected", reason => {
  ready = false;
  initializing = false;
  lastError = String(reason || "Disconnected");
  console.log("[JARVIS-WA] Disconnected:", lastError);
  setTimeout(initializeClient, 5000);
});

client.on("message", async msg => {
  try {
    if (!msg || msg.fromMe) return;
    if (isGroupChat(msg.from)) return;

    const body = String(msg.body || "").trim();
    if (!body) return;

    let contact = null;
    try {
      contact = await msg.getContact();
    } catch (_err) {
      contact = null;
    }

    const senderName =
      contact?.pushname ||
      contact?.name ||
      contact?.shortName ||
      contact?.number ||
      msg.from;

    const payload = {
      id: msg.id?._serialized || "",
      from: msg.from,
      sender: senderName,
      message: body,
      timestamp: msg.timestamp || Math.floor(Date.now() / 1000),
      type: msg.type || "chat",
    };

    console.log(`[JARVIS-WA] Incoming ${payload.sender}: ${payload.message}`);
    await postToJarvis(payload);
  } catch (err) {
    lastError = err?.message || String(err);
    console.error("[JARVIS-WA] Incoming handler error:", lastError);
  }
});

client.on("call", async call => {
  try {
    if (!call || call.fromMe) return;
    if (call.isGroup) return;

    activeCalls.set(call.id, call);
    let contact = null;
    try {
      contact = await client.getContactById(call.from);
    } catch (_err) {
      contact = null;
    }
    const callerName =
      contact?.pushname ||
      contact?.name ||
      contact?.shortName ||
      contact?.number ||
      call.from;

    const payload = {
      event_type: "call",
      id: call.id || "",
      from: call.from || "",
      sender: callerName,
      is_video: Boolean(call.isVideo),
      is_group: Boolean(call.isGroup),
      can_handle_locally: Boolean(call.canHandleLocally),
      web_client_should_handle: Boolean(call.webClientShouldHandle),
      timestamp: call.timestamp || Math.floor(Date.now() / 1000),
      type: call.isVideo ? "video_call" : "voice_call",
    };
    console.log(`[JARVIS-WA] Incoming ${payload.type} from ${payload.sender}`);
    await postToJarvis(payload);
  } catch (err) {
    lastError = err?.message || String(err);
    console.error("[JARVIS-WA] Call handler error:", lastError);
  }
});

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
  if (req.method === "GET" && url.pathname === "/status") {
    jsonResponse(res, 200, {
      ok: true,
      ready,
      me,
      last_qr_at: lastQrAt,
      last_error: lastError,
      browser_path: browserPath || "",
      initializing,
      qr_image_path: QR_IMAGE_PATH,
      active_calls: activeCalls.size,
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/send") {
    try {
      const payload = await readJson(req);
      const to = String(payload.to || payload.from || "").trim();
      const text = String(payload.text || payload.message || "").trim();
      if (!ready) {
        jsonResponse(res, 503, { ok: false, error: "WhatsApp bridge is not ready." });
        return;
      }
      if (!to || !text) {
        jsonResponse(res, 400, { ok: false, error: "Both 'to' and 'text' are required." });
        return;
      }
      if (isGroupChat(to)) {
        jsonResponse(res, 400, { ok: false, error: "Group replies are disabled." });
        return;
      }
      const sent = await client.sendMessage(to, text);
      jsonResponse(res, 200, {
        ok: true,
        id: sent?.id?._serialized || "",
        to,
      });
    } catch (err) {
      lastError = err?.message || String(err);
      jsonResponse(res, 500, { ok: false, error: lastError });
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/reject-call") {
    try {
      const payload = await readJson(req);
      const callId = String(payload.id || payload.call_id || "").trim();
      if (!callId) {
        jsonResponse(res, 400, { ok: false, error: "Call id is required." });
        return;
      }
      const call = activeCalls.get(callId);
      if (!call) {
        jsonResponse(res, 404, { ok: false, error: "Call not found or already ended." });
        return;
      }
      await call.reject();
      activeCalls.delete(callId);
      jsonResponse(res, 200, { ok: true, id: callId });
    } catch (err) {
      lastError = err?.message || String(err);
      jsonResponse(res, 500, { ok: false, error: lastError });
    }
    return;
  }

  jsonResponse(res, 404, { ok: false, error: "Not found" });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[JARVIS-WA] Local send API listening on http://127.0.0.1:${PORT}`);
});

process.on("SIGINT", async () => {
  try {
    await client.destroy();
  } finally {
    process.exit(0);
  }
});

process.on("SIGTERM", async () => {
  try {
    await client.destroy();
  } finally {
    process.exit(0);
  }
});

function initializeClient() {
  if (ready || initializing) return;
  initializing = true;
  console.log("[JARVIS-WA] Initializing WhatsApp Web client...");
  if (browserPath) {
    console.log(`[JARVIS-WA] Browser: ${browserPath}`);
  }
  client.initialize().catch(err => {
    ready = false;
    initializing = false;
    lastError = err?.message || String(err);
    console.error("[JARVIS-WA] Initialize failed:", lastError);
    Promise.resolve()
      .then(() => client.destroy().catch(() => {}))
      .finally(() => {
        setTimeout(initializeClient, Number(cfg.whatsapp_bridge_retry_ms || 8000));
      });
  });
}

initializeClient();
