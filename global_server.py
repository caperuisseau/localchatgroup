import socket
import threading
import json
import time
import os

HOST = '0.0.0.0'
PORT = 12345
HISTORY_FILE = 'chat_history.json'

clients = {}  
clients_lock = threading.Lock()
history = []

def load_history():
    global history
    if os.path.isfile(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    history = json.loads(content)
            print(f"[INFO] Historique chargé ({len(history)} messages)")
        except Exception as e:
            print(f"[ERREUR] Chargement historique : {e}")
            history.clear()
    else:
        history.clear()

def save_history():
    global history
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERREUR] Sauvegarde historique : {e}")

def broadcast(msg, sender=None, recipient=None):
    global history
    msg_obj = {
        'from': sender,
        'to': recipient if recipient else 'ALL',
        'msg': msg,
        'timestamp': time.strftime('%H:%M:%S')
    }
    with clients_lock:
        history.append(msg_obj)
        save_history()  
        for p, sock in clients.items():
            if recipient is None or recipient == p or sender == p:
                try:
                    sock.sendall((json.dumps({'type':'msg', **msg_obj}) + '\n').encode())
                except:
                    pass

def send_users():
    with clients_lock:
        users = list(clients.keys())
        for sock in clients.values():
            try:
                sock.sendall((json.dumps({'type':'users', 'data': users}) + '\n').encode())
            except:
                pass

def client_thread(sock, addr):
    buffer = ''
    pseudo = None
    try:
        while True:
            data = sock.recv(1024).decode()
            if not data:
                break
            buffer += data
            if '\n' in buffer:
                pseudo, buffer = buffer.split('\n',1)
                pseudo = pseudo.strip()
                with clients_lock:
                    if pseudo in clients:
                        sock.sendall((json.dumps({'type':'error', 'msg':'Pseudo déjà pris'}) + '\n').encode())
                        sock.close()
                        return
                    clients[pseudo] = sock
                sock.sendall((json.dumps({'type':'history', 'data': history}) + '\n').encode())
                send_users()
                break

        while True:
            data = sock.recv(4096).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n',1)
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except:
                    continue
                if obj.get('type') == 'msg':
                    msg = obj.get('msg','')
                    to = obj.get('to')
                    broadcast(msg, sender=pseudo, recipient=to)
                elif obj.get('type') == 'poll':
                    sock.sendall((json.dumps({'type':'history', 'data': history}) + '\n').encode())
                    send_users()
    except:
        pass
    finally:
        with clients_lock:
            if pseudo in clients:
                del clients[pseudo]
        send_users()
        try:
            sock.close()
        except:
            pass

def main():
    load_history()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen()
    print(f'Serveur en écoute {HOST}:{PORT}')
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=client_thread, args=(conn, addr), daemon=True).start()

if __name__=='__main__':
    main()
