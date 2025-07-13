const net = require('net');
const fs = require('fs');
const PORT = 12345;
const HISTORY_FILE = 'chat_history.json';

let clients = {}; 
let history = [];

function loadHistory() {
    if (fs.existsSync(HISTORY_FILE)) {
        try {
            const content = fs.readFileSync(HISTORY_FILE, 'utf-8');
            if (content.trim()) {
                history = JSON.parse(content);
            }
            console.log(`[INFO] Historique chargé (${history.length} messages)`);
        } catch (err) {
            console.error(`[ERREUR] Chargement historique :`, err);
            history = [];
        }
    }
}

function saveHistory() {
    try {
        fs.writeFileSync(HISTORY_FILE, JSON.stringify(history, null, 2), 'utf-8');
    } catch (err) {
        console.error(`[ERREUR] Sauvegarde historique :`, err);
    }
}

function broadcast(msg, sender = null, recipient = null) {
    const now = new Date();
    const timestamp = now.toTimeString().split(' ')[0];

    const msgObj = {
        type: 'msg',
        from: sender,
        to: recipient || 'ALL',
        msg: msg,
        timestamp: timestamp
    };

    history.push(msgObj);
    saveHistory();

    Object.entries(clients).forEach(([pseudo, client]) => {
        if (!recipient || recipient === pseudo || sender === pseudo) {
            try {
                client.write(JSON.stringify(msgObj) + '\n');
            } catch {}
        }
    });
}

function sendUsers() {
    const userList = Object.keys(clients);
    const msg = JSON.stringify({ type: 'users', data: userList }) + '\n';
    Object.values(clients).forEach(sock => {
        try { sock.write(msg); } catch {}
    });
}

function sendHistory(sock) {
    const msg = JSON.stringify({ type: 'history', data: history }) + '\n';
    sock.write(msg);
}

const server = net.createServer(sock => {
    let buffer = '';
    let pseudo = null;

    sock.on('data', data => {
        buffer += data.toString();
        while (buffer.includes('\n')) {
            const idx = buffer.indexOf('\n');
            const line = buffer.slice(0, idx).trim();
            buffer = buffer.slice(idx + 1);

            if (!pseudo) {
                if (clients[line]) {
                    sock.write(JSON.stringify({ type: 'error', msg: 'Pseudo déjà pris' }) + '\n');
                    sock.end();
                    return;
                }
                pseudo = line;
                clients[pseudo] = sock;
                sendHistory(sock);
                sendUsers();
                return;
            }

            if (!line) continue;

            let obj;
            try {
                obj = JSON.parse(line);
            } catch {
                continue;
            }

            if (obj.type === 'msg') {
                const msg = obj.msg || '';
                const to = obj.to;
                broadcast(msg, pseudo, to);
            } else if (obj.type === 'poll') {
                sendHistory(sock);
                sendUsers();
            }
        }
    });

    sock.on('close', () => {
        if (pseudo && clients[pseudo]) {
            delete clients[pseudo];
            sendUsers();
        }
    });

    sock.on('error', () => {});
});

server.listen(PORT, () => {
    loadHistory();
    console.log(`✅ Serveur TCP Node.js en écoute sur port ${PORT}`);
});
