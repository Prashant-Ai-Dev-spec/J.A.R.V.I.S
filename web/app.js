const els = {
  health: document.querySelector("#health"),
  platform: document.querySelector("#platform"),
  cpu: document.querySelector("#cpu"),
  ram: document.querySelector("#ram"),
  disk: document.querySelector("#disk"),
  location: document.querySelector("#location"),
  command: document.querySelector("#commandInput"),
  speak: document.querySelector("#speakToggle"),
  send: document.querySelector("#sendCommand"),
  clear: document.querySelector("#clearLog"),
  refresh: document.querySelector("#refreshStatus"),
  token: document.querySelector("#tokenInput"),
  saveToken: document.querySelector("#saveToken"),
  pending: document.querySelector("#pending"),
  log: document.querySelector("#log"),
};

const savedToken = localStorage.getItem("jarvis_web_token") || "";
els.token.value = savedToken;

function headers() {
  const token = els.token.value.trim();
  const result = { "Content-Type": "application/json" };
  if (token) result["X-Jarvis-Token"] = token;
  return result;
}

function addLog(kind, title, text) {
  const item = document.createElement("div");
  item.className = `entry ${kind}`;
  item.innerHTML = `<span>${title}</span><strong></strong>`;
  item.querySelector("strong").textContent = text || "";
  els.log.prepend(item);
}

async function health() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    els.health.textContent = data.ok
      ? `Online · ${data.local_ips.join(", ")}`
      : "Offline";
    els.platform.textContent = data.platform || "--";
  } catch (err) {
    els.health.textContent = "Offline";
  }
}

function pct(value) {
  if (typeof value === "number") return `${Math.round(value)}%`;
  return "--";
}

async function status() {
  try {
    const res = await fetch("/api/status", { headers: headers() });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Status failed");
    const hw = data.hardware || {};
    els.cpu.textContent = pct(hw.cpu_percent);
    els.ram.textContent = pct(hw.memory_percent);
    els.disk.textContent = pct(hw.disk_percent);
    els.location.textContent = data.location || "--";
  } catch (err) {
    els.cpu.textContent = "--";
    els.ram.textContent = "--";
    els.disk.textContent = "--";
    els.location.textContent = String(err.message || err);
  }
}

async function sendCommand() {
  const command = els.command.value.trim();
  if (!command) return;
  addLog("user", "You", command);
  els.pending.textContent = "Thinking";
  els.send.disabled = true;
  try {
    const res = await fetch("/api/command", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ command, speak: els.speak.checked }),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Command failed");
    addLog("jarvis", "JARVIS", data.reply);
    els.command.value = "";
    status();
  } catch (err) {
    addLog("error", "Error", String(err.message || err));
  } finally {
    els.pending.textContent = "Ready";
    els.send.disabled = false;
    els.command.focus();
  }
}

els.send.addEventListener("click", sendCommand);
els.refresh.addEventListener("click", status);
els.clear.addEventListener("click", () => {
  els.log.innerHTML = "";
});
els.saveToken.addEventListener("click", () => {
  localStorage.setItem("jarvis_web_token", els.token.value.trim());
  status();
});
els.command.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) sendCommand();
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/service-worker.js").catch(() => {});
}

health();
status();
setInterval(health, 30000);
