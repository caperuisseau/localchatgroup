import sys
import socket
import json
import threading
from queue import Queue
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from datetime import datetime

SERVER_IP = '0.0.0.0'
PORT = 12345

class ReceiverThread(threading.Thread):
    def __init__(self, sock, queue):
        super().__init__(daemon=True)
        self.sock = sock
        self.queue = queue
        self.running = True
        self.buffer = ''

    def run(self):
        while self.running:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    self.running = False
                    break
                self.buffer += data
                while '\n' in self.buffer:
                    line, self.buffer = self.buffer.split('\n',1)
                    if line.strip():
                        try:
                            obj = json.loads(line)
                            self.queue.put(obj)
                        except:
                            pass
            except:
                self.running = False
                break

class Signals(QObject):
    new_message = pyqtSignal(dict)
    user_list = pyqtSignal(list)
    error = pyqtSignal(str)
    history = pyqtSignal(list)

class ChatClient(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Messagerie')
        self.resize(800,700)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.queue = Queue()
        self.signals = Signals()
        self.pseudo = ''
        self.users = []
        self.text_edits = {}
        self.displayed = set()

        self.setup_ui()
        self.signals.new_message.connect(self.on_new_message)
        self.signals.user_list.connect(self.on_user_list)
        self.signals.error.connect(self.on_error)
        self.signals.history.connect(self.on_history)

        self.connect_to_server()
        self.receiver = ReceiverThread(self.sock, self.queue)
        self.receiver.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_queue)
        self.timer.start(100)

    def setup_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        general_text = QTextEdit()
        general_text.setReadOnly(True)
        general_text.setStyleSheet("font-size:20px;")
        self.text_edits['ALL'] = general_text
        self.tabs.addTab(general_text, 'Général')

        hbox = QHBoxLayout()
        self.recipient_combo = QComboBox()
        self.recipient_combo.addItem('Général')
        self.recipient_combo.setStyleSheet("font-size:16px;")
        hbox.addWidget(self.recipient_combo)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText('Tapez votre message...')
        self.input_line.setStyleSheet("font-size:18px; padding:8px;")
        self.input_line.returnPressed.connect(self.send_message)
        hbox.addWidget(self.input_line,1)

        send_btn = QPushButton('Envoyer')
        send_btn.setStyleSheet("font-size:18px; padding:8px;")
        send_btn.clicked.connect(self.send_message)
        hbox.addWidget(send_btn)

        layout.addLayout(hbox)
        self.setLayout(layout)

    def connect_to_server(self):
        self.pseudo, ok = QInputDialog.getText(self, 'Pseudo', 'Entrez votre pseudo :')
        if not ok or not self.pseudo.strip():
            self.pseudo = 'jenesaispaschoisir'
        try:
            self.sock.connect((SERVER_IP, PORT))
            self.sock.sendall((self.pseudo+'\n').encode())
        except Exception as e:
            QMessageBox.critical(self, 'Erreur', f'Impossible de se connecter:\n{e}')
            sys.exit(1)

    def process_queue(self):
        while not self.queue.empty():
            obj = self.queue.get()
            t = obj.get('type')
            if t == 'msg':
                self.signals.new_message.emit(obj)
            elif t == 'users':
                self.signals.user_list.emit(obj.get('data',[]))
            elif t == 'error':
                self.signals.error.emit(obj.get('msg','Erreur'))
            elif t == 'history':
                self.signals.history.emit(obj.get('data',[]))

    def on_new_message(self, msg):
        sender = msg.get('from')
        target = msg.get('to')
        message = msg.get('msg')
        timestamp = msg.get('timestamp', datetime.now().strftime('%H:%M:%S'))
        uid = f"{timestamp}_{sender}_{target}_{message}"
        if uid in self.displayed:
            return
        self.displayed.add(uid)
        tab_key = 'ALL' if target == 'ALL' else (sender if sender != self.pseudo else target)
        if tab_key not in self.text_edits:
            te = QTextEdit()
            te.setReadOnly(True)
            te.setStyleSheet("font-size:20px;")
            self.text_edits[tab_key] = te
            self.tabs.addTab(te, f"🔒 {tab_key}")
        text = f"[{timestamp}] {sender} ➜ {target if target != 'ALL' else 'Tous'} : {message}"
        self.text_edits[tab_key].append(text)
        self.text_edits[tab_key].verticalScrollBar().setValue(self.text_edits[tab_key].verticalScrollBar().maximum())

    def on_user_list(self, users):
        users = sorted([u for u in users if u != self.pseudo])
        if users != self.users:
            self.users = users
            self.recipient_combo.blockSignals(True)
            self.recipient_combo.clear()
            self.recipient_combo.addItem('🌐 Général')
            self.recipient_combo.addItems(users)
            self.recipient_combo.blockSignals(False)

    def on_error(self, msg):
        QMessageBox.warning(self, 'Erreur', msg)

    def on_history(self, msgs):
        self.displayed.clear()
        for te in self.text_edits.values():
            te.clear()
        for msg in msgs:
            self.on_new_message(msg)

    def send_message(self):
        text = self.input_line.text().strip()
        if not text:
            return
        recipient = self.recipient_combo.currentText()
        to = 'ALL' if recipient == 'Général' else recipient
        obj = {'type':'msg', 'msg': text}
        if to != 'ALL':
            obj['to'] = to
        try:
            self.sock.sendall((json.dumps(obj)+'\n').encode())
            self.input_line.clear()
        except:
            QMessageBox.critical(self, 'Erreur', 'Déconnecté du serveur')

    def closeEvent(self, event):
        try:
            self.receiver.running = False
            self.sock.close()
        except:
            pass
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client = ChatClient()
    client.show()
    sys.exit(app.exec_())
