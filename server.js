const net = require('net');
const fs = require('fs');
const PORT = 12345;
const HISTORY_FILE = 'chat_history.json';

let clients = {};
let history = [];

// Charger l'historique des messages
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

// Sauvegarder l'historique des messages
function saveHistory() {
    try {
        fs.writeFileSync(HISTORY_FILE, JSON.stringify(history, null, 2), 'utf-8');
    } catch (err) {
        console.error(`[ERREUR] Sauvegarde historique :`, err);
    }
}

// Diffuser un message à tous les clients concernés
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

// Envoyer la liste des utilisateurs connectés
function sendUsers() {
    const userList = Object.keys(clients);
    const msg = JSON.stringify({ type: 'users', data: userList }) + '\n';
    Object.values(clients).forEach(sock => {
        try { sock.write(msg); } catch {}
    });
}

// Envoyer l'historique des messages à un client
function sendHistory(sock) {
    const msg = JSON.stringify({ type: 'history', data: history }) + '\n';
    sock.write(msg);
}

// Supprimer un message de l'historique
function deleteMessage(timestamp, sender) {
    const index = history.findIndex(msg => msg.timestamp === timestamp && msg.from === sender);
    if (index !== -1) {
        history.splice(index, 1); // Supprime le message
        saveHistory(); // Sauvegarde l'historique mis à jour
        return true;
    }
    return false; // Retourne false si le message n'existe pas
}

// Création du serveur
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
            } else if (obj.type === 'delete') {
                const success = deleteMessage(obj.timestamp, pseudo);
                if (success) {
                    const deleteNotification = {
                        type: 'delete',
                        timestamp: obj.timestamp,
                        from: pseudo
                    };
                    Object.values(clients).forEach(client => {
                        try {
                            client.write(JSON.stringify(deleteNotification) + '\n');
                        } catch {}
                    });
                } else {
                    sock.write(JSON.stringify({ type: 'error', msg: 'Message introuvable ou déjà supprimé' }) + '\n');
                }
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

// Démarrage du serveur
server.listen(PORT, () => {
    loadHistory();
    console.log(`✅ Serveur TCP Node.js en écoute sur port ${PORT}`);
});