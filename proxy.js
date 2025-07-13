const WebSocket = require('ws');
const net = require('net');

const wss = new WebSocket.Server({ port: 8080, host: '0.0.0.0' }); // <- 🔥 ici
console.log("🌐 Proxy WebSocket dispo sur ws://IP-LOCALE:8080");

wss.on('connection', ws => {
    const tcp = net.connect(12345, '127.0.0.1');

    ws.on('message', msg => tcp.write(msg + '\n'));
    tcp.on('data', data => ws.send(data.toString()));
    ws.on('close', () => tcp.end());
    tcp.on('close', () => ws.close());
});
