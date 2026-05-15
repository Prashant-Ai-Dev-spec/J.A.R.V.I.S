const http = require('http');
const WebSocket = require('ws');
// y-websocket exposes a setup helper under bin/utils.js
const setupWSConnection = require('y-websocket/bin/utils.js').setupWSConnection;

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('J.A.R.V.I.S Yjs websocket server');
});

const wss = new WebSocket.Server({ server });

wss.on('connection', (conn, req) => {
  // setup Yjs websocket connection
  setupWSConnection(conn, req);
});

const PORT = process.env.PORT || 1234;
server.listen(PORT, () => console.log(`y-websocket server running on port ${PORT}`));
