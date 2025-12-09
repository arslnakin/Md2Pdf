import sys
import os
import json
import requests
import re
import markdown
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QTextEdit, QLabel, QPushButton, QSplitter, QMessageBox, QInputDialog,
                             QLineEdit, QDialog, QFormLayout, QFileDialog, QToolBar, QComboBox,
                             QScrollArea, QFrame, QSizePolicy, QCheckBox)
from PyQt6.QtGui import QAction, QKeySequence, QTextCursor, QIcon, QFont, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl, QSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from converter import Md2PdfConverter

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

class ChatWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, provider, api_key, model, messages):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.messages = messages

    def run(self):
        try:
            if self.provider == "Google Gemini":
                self.call_gemini()
            elif self.provider == "OpenRouter":
                self.call_openrouter()
            else:
                self.error.emit("Geçersiz Sağlayıcı")
        except Exception as e:
            self.error.emit(str(e))

    def call_gemini(self):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.api_key}"
        headers = {'Content-Type': 'application/json'}
        contents = []
        for msg in self.messages:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        data = {"contents": contents}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            try:
                answer = result['candidates'][0]['content']['parts'][0]['text']
                self.finished.emit(answer)
            except (KeyError, IndexError):
                self.finished.emit("Alınan cevap işlenemedi.")
        else:
            self.error.emit(f"API Hatası: {response.text}")

    def call_openrouter(self):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model or "openai/gpt-3.5-turbo",
            "messages": self.messages
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            try:
                answer = result['choices'][0]['message']['content']
                self.finished.emit(answer)
            except (KeyError, IndexError):
                self.finished.emit("Alınan cevap işlenemedi.")
        else:
            self.error.emit(f"API Hatası: {response.text}")

class SettingsDialog(QDialog):
    # ... (SettingsDialog remains same)
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or {}
        self.setWindowTitle("Ayarlar")
        self.setFixedSize(400, 250)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")
        layout = QFormLayout(self)
        
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["Google Gemini", "OpenRouter"])
        self.combo_provider.setCurrentText(self.config.get("provider", "Google Gemini"))
        self.combo_provider.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")
        
        self.txt_gemini_key = QLineEdit(self.config.get("gemini_key", ""))
        self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gemini_key.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")
        
        self.txt_openrouter_key = QLineEdit(self.config.get("open_router_key", ""))
        self.txt_openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_openrouter_key.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")
        
        self.txt_model = QLineEdit(self.config.get("model", "google/gemini-2.0-flash-exp:free")) 
        self.txt_model.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")

        layout.addRow("Sağlayıcı:", self.combo_provider)
        layout.addRow("Gemini API Key:", self.txt_gemini_key)
        layout.addRow("OpenRouter API Key:", self.txt_openrouter_key)
        layout.addRow("Model (OpenRouter):", self.txt_model)
        
        btn_save = QPushButton("Kaydet")
        btn_save.setStyleSheet("background-color: #89b4fa; color: #1e1e2e; padding: 8px; font-weight: bold;")
        btn_save.clicked.connect(self.save_settings)
        layout.addRow(btn_save)
        
    def save_settings(self):
        self.config["provider"] = self.combo_provider.currentText()
        self.config["gemini_key"] = self.txt_gemini_key.text()
        self.config["open_router_key"] = self.txt_openrouter_key.text()
        self.config["model"] = self.txt_model.text()
        self.accept()

class FindReplaceDialog(QDialog):
    def __init__(self, parent=None, editor=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Bul ve Değiştir")
        self.setFixedSize(350, 180)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")
        layout = QFormLayout(self)
        self.find_input = QLineEdit()
        self.find_input.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")
        self.replace_input = QLineEdit()
        self.replace_input.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")
        layout.addRow("Aranan:", self.find_input)
        layout.addRow("Yeni Değer:", self.replace_input)
        
        btn_box = QHBoxLayout()
        btn_find = QPushButton("Sonrakini Bul")
        btn_find.clicked.connect(self.find_next)
        btn_find.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")
        
        btn_replace = QPushButton("Değiştir")
        btn_replace.clicked.connect(self.replace)
        btn_replace.setStyleSheet("background-color: #89b4fa; color: #1e1e2e; padding: 5px;")
        
        btn_box.addWidget(btn_find)
        btn_box.addWidget(btn_replace)
        layout.addRow(btn_box)

    def find_next(self):
        text = self.find_input.text()
        if not text: return
        if not self.editor.find(text):
             self.editor.moveCursor(QTextCursor.MoveOperation.Start)
             if not self.editor.find(text):
                 QMessageBox.information(self, "Bilgi", "Eşleşme bulunamadı")
    
    def replace(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
            self.find_next()
        else:
            self.find_next()

class EditorWindow(QMainWindow):
    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.parent_window = parent
        self.config = self.load_config()
        self.messages = [] 
        
        self.setWindowTitle(f"Editör - {file_path if file_path else 'Yeni Dosya'}")
        self.resize(1500, 900)
        self.setStyleSheet("QMainWindow { background-color: #1e1e2e; color: #cdd6f4; }")
        
        # System Prompt
        self.system_prompt_base = (
            "Sen Markdown editörüne entegre edilmiş bir yapay zeka asistanısın. "
            "Kullanıcı düzenleme veya içerik üretimi istediğinde yardımcı ol. "
        )
        
        # --- Toolbar ---
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setStyleSheet("""
            QToolBar { background-color: #262636; border-bottom: 1px solid #313244; padding: 5px; spacing: 8px; }
            QToolButton { background-color: #313244; color: #cdd6f4; padding: 5px; border-radius: 4px; font-weight: bold; }
            QToolButton:hover { background-color: #45475a; }
            QToolButton:checked { background-color: #89b4fa; color: #1e1e2e; }
        """)
        self.addToolBar(toolbar)
        
        save_act = QAction("💾 Kaydet", self)
        save_act.triggered.connect(self.save_file)
        toolbar.addAction(save_act)
        toolbar.addSeparator()
        
        fmt_actions = [
            ("Bold", "**B**", "**Kalın**"),
            ("Italic", "*I*", "*İtalik*"),
            ("H1", "H1", "\n# "),
            ("H2", "H2", "\n## "),
            ("Link", "🔗", "[](url)"),
            ("Img", "🖼️", "![](url)"),
            ("Code", "</>", "\n```\n\n```\n"),
            ("Mermaid", "📊", "\n```mermaid\ngraph TD;\nA-->B;\n```\n"),
        ]
        for name, icon, snippet in fmt_actions:
            act = QAction(icon, self)
            act.setToolTip(name)
            act.triggered.connect(lambda checked, s=snippet: self.insert_snippet(s))
            toolbar.addAction(act)
            
        toolbar.addSeparator()
        
        # Toggles
        self.act_preview = QAction("👁️ Önizleme (Sol)", self)
        self.act_preview.setCheckable(True)
        self.act_preview.setChecked(True)
        self.act_preview.triggered.connect(self.toggle_preview)
        toolbar.addAction(self.act_preview)
        
        self.act_chatbot = QAction("🤖 Asistan", self)
        self.act_chatbot.setCheckable(True)
        self.act_chatbot.setChecked(True)
        self.act_chatbot.triggered.connect(self.toggle_chatbot)
        toolbar.addAction(self.act_chatbot)
        
        # Canvas Mode Toggle
        self.act_canvas = QAction("✏️ Canvas Modu", self)
        self.act_canvas.setCheckable(True)
        self.act_canvas.setChecked(True) # Default ON
        self.act_canvas.setToolTip("Açıkken yapay zeka editördeki metni değiştirebilir.")
        toolbar.addAction(self.act_canvas)
        
        toolbar.addSeparator()
        settings_act = QAction("⚙️ Ayarlar", self)
        settings_act.triggered.connect(self.open_settings)
        toolbar.addAction(settings_act)

        # --- Main Layout (3 Panes Ordered: Preview | Editor | Chatbot) ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # 1. Preview Pane (LEFT)
        self.preview_widget = QWidget()
        prev_layout = QVBoxLayout(self.preview_widget)
        prev_layout.setContentsMargins(0,0,0,0)
        prev_lbl = QLabel("  Canlı Önizleme")
        prev_lbl.setStyleSheet("background-color: #262636; color: #bac2de; font-size: 11px; padding: 4px;")
        prev_layout.addWidget(prev_lbl)
        self.preview_pane = QWebEngineView()
        self.preview_pane.setStyleSheet("background-color: white;")
        prev_layout.addWidget(self.preview_pane)
        self.splitter.addWidget(self.preview_widget)
        
        # 2. Editor Pane (CENTER / Canvas)
        self.editor_widget = QWidget()
        edit_layout = QVBoxLayout(self.editor_widget)
        edit_layout.setContentsMargins(0,0,0,0)
        edit_lbl = QLabel("  Editör (Canvas)")
        edit_lbl.setStyleSheet("background-color: #262636; color: #89b4fa; font-size: 11px; padding: 4px; font-weight: bold;")
        edit_layout.addWidget(edit_lbl)
        self.editor_pane = QTextEdit()
        self.editor_pane.setStyleSheet("""
            background-color: #1e1e2e; color: #cdd6f4; 
            font-family: 'Consolas', monospace; font-size: 14px; border: none; padding: 10px;
        """)
        self.editor_pane.setPlaceholderText("Markdown yaz...")
        self.editor_pane.textChanged.connect(self.on_text_changed)
        edit_layout.addWidget(self.editor_pane)
        self.splitter.addWidget(self.editor_widget)
        
        # 3. Chatbot Pane (RIGHT)
        self.chatbot_widget = QWidget()
        chat_layout = QVBoxLayout(self.chatbot_widget)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_chat = QLabel("AI Asistanı")
        lbl_chat.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 16px;")
        chat_layout.addWidget(lbl_chat)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background-color: #262636; color: #cdd6f4; border-radius: 8px; padding: 10px;")
        chat_layout.addWidget(self.chat_history)
        
        inp_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Komut ver...")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        self.chat_input.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 6px; border-radius: 4px;")
        inp_layout.addWidget(self.chat_input)
        
        btn_send = QPushButton("Gönder")
        btn_send.clicked.connect(self.send_chat_message)
        btn_send.setStyleSheet("background-color: #89b4fa; color: #1e1e2e; font-weight: bold; border-radius: 4px; padding: 6px;")
        inp_layout.addWidget(btn_send)
        chat_layout.addLayout(inp_layout)
        
        self.splitter.addWidget(self.chatbot_widget)
        
        # Initial Sizes: Preview(25%), Editor(45%), Chat(30%)
        self.splitter.setSizes([400, 700, 400]) 
        
        self.converter = Md2PdfConverter()
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.interval = 500
        self.preview_timer.timeout.connect(self.update_preview)
        
        self.setup_shortcuts()
        if self.file_path:
            self.load_file_content()
            
    def setup_shortcuts(self):
        QAction("Kaydet", self, shortcut=QKeySequence("Ctrl+S"), triggered=self.save_file)
        
    def toggle_preview(self):
        self.preview_widget.setVisible(self.act_preview.isChecked())
        if self.act_preview.isChecked():
            self.update_preview()

    def toggle_chatbot(self):
        self.chatbot_widget.setVisible(self.act_chatbot.isChecked())

    def on_text_changed(self):
        if self.act_preview.isChecked():
            self.preview_timer.start(800)

    def update_preview(self):
        if not self.act_preview.isChecked(): return
        
        md_content = self.editor_pane.toPlainText()
        html_body = markdown.markdown(
            md_content, 
            extensions=['extra', 'codehilite', 'tables', 'fenced_code', 'nl2br', 'pymdownx.arithmatex', 'pymdownx.superfences']
        )
        full_html = self.converter.html_template.format(content=html_body)
        
        if self.file_path:
            base_url = QUrl.fromLocalFile(os.path.dirname(os.path.abspath(self.file_path)) + os.sep)
        else:
            base_url = QUrl.fromLocalFile(os.getcwd() + os.sep)
            
        settings = self.preview_pane.settings()
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.preview_pane.setHtml(full_html, base_url)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
             try:
                 with open(CONFIG_FILE, "r") as f:
                     return json.load(f)
             except:
                 return {}
        return {}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def open_settings(self):
        dlg = SettingsDialog(self, self.config)
        if dlg.exec():
            self.save_config()
            QMessageBox.information(self, "Ayarlar", "Ayarlar kaydedildi.")

    def load_file_content(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.editor_pane.setPlainText(content)
                self.update_preview()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya açılamadı: {e}")

    def save_file(self):
        if not self.file_path:
            fname, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", "", "Markdown Files (*.md)")
            if fname:
                self.file_path = fname
                self.setWindowTitle(f"Editör - {self.file_path}")
                if self.parent_window and hasattr(self.parent_window, "add_file_paths"):
                    self.parent_window.add_file_paths([fname])
            else:
                return
        try:
            content = self.editor_pane.toPlainText()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.statusBar().showMessage("Kaydedildi", 2000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydedilemedi: {e}")

    def insert_snippet(self, snippet):
        cursor = self.editor_pane.textCursor()
        cursor.insertText(snippet)
        self.editor_pane.setFocus()

    def open_find_replace(self):
        dialog = FindReplaceDialog(self, self.editor_pane)
        dialog.show()

    def send_chat_message(self):
        msg = self.chat_input.text().strip()
        if not msg: return
        
        provider = self.config.get("provider", "Google Gemini")
        api_key = self.config.get("gemini_key") if provider == "Google Gemini" else self.config.get("open_router_key")
        if not api_key:
            QMessageBox.warning(self, "Eksik Anahtar", "Ayarlardan API anahtarı ekleyin.")
            self.open_settings()
            return

        current_text = self.editor_pane.toPlainText()
        is_canvas_on = self.act_canvas.isChecked()
        
        # Build Context Instruction
        instruction = ""
        if is_canvas_on:
            instruction = (
                "\n[SİSTEM: Canvas Modu AÇIK]\n"
                "Kullanıcı düzenleme isterse, aşağıdaki metni güncelle. "
                "Cevabında yeni içeriği sadece <<<UPDATE>>> ve <<<END>>> etiketleri arasına yaz. "
                "Açıklamaları etiketlerin dışına yaz."
            )
        else:
            instruction = (
                "\n[SİSTEM: Canvas Modu KAPALI]\n"
                "Kullanıcının metnini oku ama DEĞİŞTİRME YETKİN YOK. "
                "Sadece sohbet penceresinden cevap ver, önerilerde bulun. "
                "<<<UPDATE>>> etiketini ASLA kullanma."
            )

        full_msg = f"{self.system_prompt_base}\n{instruction}\n\nKullanıcı İsteği: {msg}\n\nAktif Editör İçeriği (Referans):\n```markdown\n{current_text}\n```"
        
        self.chat_history.append(f"<div style='color: #89b4fa;'><b>Sen:</b> {msg}</div>")
        self.chat_input.clear()
        self.chat_history.append(f"<div style='color: #bac2de;'><i>Asistan çalışıyor...</i></div>")
        
        # Send clean messages structure (keeping roles simpler for API compatibility)
        # We append the full context message as "user"
        self.messages.append({"role": "user", "content": full_msg})
        
        self.worker = ChatWorker(provider, api_key, self.config.get("model"), self.messages)
        self.worker.finished.connect(self.on_chat_response)
        self.worker.error.connect(self.on_chat_error)
        self.worker.start()

    def on_chat_response(self, response):
        # Only process updates if Canvas Mode is ON
        if self.act_canvas.isChecked():
            update_match = re.search(r'<<<UPDATE>>>(.*?)<<<END>>>', response, re.DOTALL)
            if update_match:
                new_content = update_match.group(1).strip()
                self.editor_pane.setPlainText(new_content)
                # Remove the update block from display to keep chat clean
                display_response = response.replace(update_match.group(0), "<i>[✅ Editör içeriği güncellendi]</i>")
            else:
                display_response = response
        else:
            # If AI accidentally sent tags (shouldn't if instucted), ignore them visually or strip?
            # Let's just show as is, no auto-update.
            display_response = response

        self.chat_history.append(f"<div style='color: #a6e3a1;'><b>Asistan:</b> {display_response}</div><br>")
        self.messages.append({"role": "assistant", "content": response})

    def on_chat_error(self, err):
        self.chat_history.append(f"<div style='color: #f38ba8;'><b>Hata:</b> {err}</div><br>")
