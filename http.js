const http = require('http');
const fs = require('fs');
const path = require('path');

const server = http.createServer((req, res) => {
    if (req.url === '/') req.url = '/client/client.html';
    const filePath = path.join(__dirname, req.url);
    fs.readFile(filePath, (err, data) => {
        if (err) {
            res.writeHead(404); res.end("404 Not Found");
        } else {
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(data);
        }
    });
});

server.listen(8000, '0.0.0.0', () => {
    console.log("📡 Serveur HTTP sur http://TON-IP-LOCALE:8000");
});
