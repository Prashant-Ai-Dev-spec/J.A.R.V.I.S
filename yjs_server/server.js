const WebSocket = require("ws");
const http = require("http");

const server = http.createServer();
const wss = new WebSocket.Server({ server });

const docs = new Map();

wss.on("connection", (ws) => {
  console.log("Client connected");

  ws.on("message", (data) => {
    try {
      const msg = JSON.parse(data);
      const { doc, update } = msg;

      if (!docs.has(doc)) {
        docs.set(doc, Buffer.alloc(0));
      }

      if (update) {
        const current = docs.get(doc);
        docs.set(doc, Buffer.concat([current, Buffer.from(update)]));

        // Broadcast to all clients
        wss.clients.forEach((client) => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({ doc, update }));
          }
        });
      }
    } catch (err) {
      console.error("Error processing message:", err);
    }
  });

  ws.on("close", () => {
    console.log("Client disconnected");
  });

  ws.on("error", (err) => {
    console.error("WebSocket error:", err);
  });
});

const PORT = process.env.PORT || 1234;
server.listen(PORT, () => {
  console.log(`Yjs WebSocket server listening on port ${PORT}`);
});
