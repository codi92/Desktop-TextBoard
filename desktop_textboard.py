import sys , os, re, json , base64, html, uuid, requests # Import necessary libraries
from datetime import datetime  # For timestamps
from PyQt6 import QtWidgets, QtCore, QtGui  # PyQt6 GUI classes
from functions.wallpaper_color import get_desktop_base_color , windows_is_dark_mode
from datetime import datetime

# Get the path to the config file in the user's home directory
def get_config_path():
    home = os.path.expanduser("~")  # Get user's home directory
    return os.path.join(home, ".config_desktop_textboard.json")  # Config file path

# Settings dialog for font and save file location
class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent, current_font, current_history_file):
        super().__init__(parent)
        self.setWindowTitle("Settings")  # Dialog title
        self.setModal(True)  # Block input to other windows
        layout = QtWidgets.QFormLayout(self)  # Form layout
        self.font_button = QtWidgets.QPushButton("Choose Font")  # Button to open font dialog
        self.font_label = QtWidgets.QLabel(current_font.family() + ", " + str(current_font.pointSize()))  # Show current font
        self.font = QtGui.QFont(current_font)  # Store font
        self.font_button.clicked.connect(self.choose_font)  # Connect button
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        font_layout = QtWidgets.QHBoxLayout()  # Horizontal layout for font
        font_layout.addWidget(self.font_button)
        font_layout.addWidget(self.font_label)
        # Add a checkbox for disabling transparency
        layout.addRow("Default Font:", font_layout)
        self.disable_transparency_checkbox = QtWidgets.QCheckBox("Disable Transparency")
        self.disable_transparency_checkbox.setChecked(getattr(parent, 'disable_transparency', False))  # Set initial state
        layout.addRow("Disable Transparency:", self.disable_transparency_checkbox)
        # Save file location
        self.path_edit = QtWidgets.QLineEdit(current_history_file)  # Editable path
        self.browse_button = QtWidgets.QPushButton("Browse")  # Browse button
        self.browse_button.clicked.connect(self.choose_file)  # Connect browse
        path_layout = QtWidgets.QHBoxLayout()  # Horizontal layout for path
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)
        layout.addRow("Save File Location:", path_layout)


        # OK/Cancel buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

     
    def choose_font(self):
        font, ok = QtWidgets.QFontDialog.getFont(self.font, self)  # Open font dialog
        if ok:
            self.font = font
            self.font_label.setText(font.family() + ", " + str(font.pointSize()))

    def choose_file(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Choose Save File", self.path_edit.text(), "JSON Files (*.json);;All Files (*)")
        if path:
            self.path_edit.setText(path)

    def accept(self):
        parent = self.parent()
        if parent is not None:
            parent.disable_transparency = self.disable_transparency_checkbox.isChecked()
            parent.update_opacity()
        super().accept()

# Main text board widget
class DesktopTextBoard(QtWidgets.QTextEdit):
    def __init__(self):
        super().__init__()
        self.show_raw = False  # Track raw/rendered mode
        self.history_file = "textboard_history.json"  # Default save file
        self.auto_save_timer = None  # Timer for auto-save
        self.clipboard_catch_enabled = False  # Clipboard catch state
        self.clipboard_timer = None  # Timer for clipboard polling
        self.last_clipboard_text = ""  # Last clipboard content
        self.bg_snippet_threads = {}  # Track background snippet threads and processes
        self.opacity = 1.0  # Set default opacity before loading config
        self.disable_transparency = False  # New config option
        self.setup_ui()  # Set up window
        self.load_config()  # Load config (may overwrite opacity)
        self.load_file()  # Load saved text
        self.setup_auto_save()  # Start auto-save
        self.setup_clipboard_catch()  # Set up clipboard polling
        self.set_theme()  # Set theme based on desktop color
        self.theme_timer = QtCore.QTimer(self)
        self.theme_timer.timeout.connect(self.set_theme)
        self.theme_timer.start(1000)
        self.update_opacity()  # Apply loaded opacity
        self.is_error = False  # Track if an error occurred

    def show_stop_snippet_dialog(self):
        if not self.bg_snippet_threads:
            QtWidgets.QMessageBox.information(self, "No Background Snippets", "No background snippets are currently running.")
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Stop Background Snippet")
        layout = QtWidgets.QVBoxLayout(dlg)
        label = QtWidgets.QLabel("Select a background snippet to stop:")
        layout.addWidget(label)
        list_widget = QtWidgets.QListWidget()
        for span_id in self.bg_snippet_threads.keys():
            list_widget.addItem(span_id)
        layout.addWidget(list_widget)
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(btn_box)
        def stop_selected():
            selected = list_widget.currentItem()
            if selected:
                self.stop_bg_snippet(selected.text())
            dlg.accept()
        btn_box.accepted.connect(stop_selected)
        btn_box.rejected.connect(dlg.reject)
        dlg.exec()

    def setup_ui(self):
        # Set window flags for frameless, always-on-bottom, and tool window
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnBottomHint |
            QtCore.Qt.WindowType.Tool 
        )
        # --- Custom titlebar for drag ---
        self.titlebar = QtWidgets.QWidget(self)
        self.titlebar.setFixedHeight(5)  # Set height for titlebar
        self.titlebar.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self.titlebar.setStyleSheet("background: rgba(80,80,80,0.18);")
        self.titlebar.setGeometry(0, 0, self.width(), 5)
        self.titlebar.mousePressEvent = self._titlebar_mouse_press
        self.titlebar.mouseMoveEvent = self._titlebar_mouse_move
        self.titlebar.mouseReleaseEvent = self._titlebar_mouse_release
        self._drag_pos = None
        # Hide scrollbars
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)  # No line wrap
        
        # Set window size and position (right half of screen)
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen.width() // 2, 0, screen.width() // 2, screen.height())
        self.setWindowOpacity(1.0)
        self.setWindowTitle("Desktop TextBoard")
        self.setMouseTracking(True)  # Enable mouse tracking for hover events
        self.setAcceptDrops(True)  # Enable drag-and-drop

    def _titlebar_mouse_press(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            wh = self.windowHandle()
            if hasattr(wh, 'startSystemMove'):
                wh.startSystemMove()  # Correct: no argument
            else:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _titlebar_mouse_move(self, event):
        if self._drag_pos and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _titlebar_mouse_release(self, event):
        self._drag_pos = None

    def set_theme(self):
        desktop_color = get_desktop_base_color()
        is_dark_mode = windows_is_dark_mode()
        red = desktop_color.red()
        green = desktop_color.green()
        blue = desktop_color.blue()
        if is_dark_mode:
            color = QtGui.QColor(max(0, red - 30), max(0, green - 30), max(0, blue - 30))
            border_color = QtGui.QColor(max(0, red - 50), max(0, green - 50), max(0, blue - 50))
            font_color = QtGui.QColor(200, 200, 200)  # Lighter text for dark mode
            selection_color = QtGui.QColor(max(0, red - 80), max(0, green - 80), max(0, blue - 80))
            selection_bg_color = QtGui.QColor(30, 30, 30)  # Darker selection background for dark mode
        else:
            color = QtGui.QColor(max(0, red + 30), max(0, green + 30), max(0, blue + 30))
            border_color = QtGui.QColor(max(0, red + 50), max(0, green + 50), max(0, blue + 50))
            font_color = QtGui.QColor(30, 30, 30)  # Darker text for light mode
            selection_color = QtGui.QColor(max(0, red + 80), max(0, green + 80), max(0, blue + 80))  # Lighter selection color for light mode
            selection_bg_color = QtGui.QColor(240, 240, 240)  # Lighter selection background for light mode
        # Set editor style
        self.setStyleSheet("""
            QTextEdit {
                background: """ + color.name() + """;
                color: """ + font_color.name() + """;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 15px;
                padding: 12px;
                border: 1.5px solid """ + border_color.name() + """;
                selection-background-color: """ + selection_bg_color.name() + """;
                selection-color: """ + selection_color.name() + """;
            }
        """)
    def update_opacity(self):
        if getattr(self, 'disable_transparency', False):
            self.setWindowOpacity(1.0)
        else:
            self.setWindowOpacity(self.opacity)

    def increase(self):
        if not getattr(self, 'disable_transparency', False):
            self.opacity = min(1.0, self.opacity + 0.1)
            self.update_opacity()
            self.save_config()  # Save config after changing opacity

    def decrease(self):
        if not getattr(self, 'disable_transparency', False):
            self.opacity = max(0.1, self.opacity - 0.1)
            self.update_opacity()
            self.save_config()  # Save config after changing opacity
        
    def load_config(self):
        config_path = get_config_path()
        self._last_search = ""
        self._last_replace_find = ""
        self._last_replace_replace = ""
        self.opacity = 1.0
        self.disable_transparency = False
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                font = QtGui.QFont()
                font.fromString(config.get("font", "Consolas,15,-1,5,50,0,0,0,0,0"))
                self.setFont(font)
                self.history_file = config.get("history_file", self.history_file)
                self._last_search = config.get("last_search", "")
                self._last_replace_find = config.get("last_replace_find", "")
                self._last_replace_replace = config.get("last_replace_replace", "")
                self.disable_transparency = config.get("disable_transparency", False)
                self.opacity = float(config.get("opacity", 1.0))  # Always load last-used opacity
            except Exception as e:
                if not self.is_error:
                    self.is_error = True
                    self.setHtml(f"<p style='color: red;'>Error loading config: {e}</p>")
                
        self.setWindowOpacity(self.opacity if not self.disable_transparency else 1.0)

    def save_config(self, font=None, history_file=None):
        config_path = get_config_path()
        config = {
            "font": (font or self.font()).toString(),
            "history_file": history_file or self.history_file,
            "last_search": getattr(self, "_last_search", ""),
            "last_replace_find": getattr(self, "_last_replace_find", ""),
            "last_replace_replace": getattr(self, "_last_replace_replace", ""),
            "opacity": getattr(self, "opacity", 1.0),
            "disable_transparency": getattr(self, "disable_transparency", False)
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.setHtml(f"<p style='color: red;'>Error saving config: {e}</p>")


    def setup_auto_save(self):
        self.auto_save_timer = QtCore.QTimer()  # Timer for auto-save
        self.auto_save_timer.timeout.connect(self.save_file)  # Save on timeout
        self.auto_save_timer.start(3000)  # Every 3 seconds
        self.textChanged.connect(self.save_file)  # Save on text change

    def load_file(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.setHtml(data.get('text', ''))
            except Exception as e:
                self.setHtml(f"<p style='color: red;'>Error loading file: {e}</p>")

    def save_file(self):
        if not self.is_error:
            try:
                data = {
                    'text': self.toHtml(),
                    'last_updated': datetime.now().isoformat(),
                    'app_version': '2.0'
                }
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.is_error = True
                self.setHtml(f"<p style='color: red;'>Error saving file: {e}</p>")

    def closeEvent(self, event):
        self.save_file()  # Save on close
        self.save_config()  # Save config on close
        if self.auto_save_timer:
            self.auto_save_timer.stop()  # Stop auto-save
        super().closeEvent(event)

    def wheelEvent(self, event):
        modifiers = event.modifiers()
        if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
            h_scrollbar = self.horizontalScrollBar()
            delta = event.angleDelta().y()
            step = delta // 8
            h_scrollbar.setValue(h_scrollbar.value() - step)
            event.accept()
        else:
            super().wheelEvent(event)

    def on_text_changed(self):
        current_text = self.toHtml()
        timestamp = datetime.now().isoformat()
        if self.history and self.history[-1]['text'] == current_text:
            return
        entry = {
            'text': current_text,
            'timestamp': timestamp,
            'cursor_position': self.textCursor().position()
        }
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        self.history.append(entry)
        self.history_index = len(self.history) - 1
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.history_index -= 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_from_history()

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_from_history()

    def restore_from_history(self):
        if 0 <= self.history_index < len(self.history):
            entry = self.history[self.history_index]
            self.textChanged.disconnect(self.on_text_changed)
            self.setHtml(entry['text'])
            if 'cursor_position' in entry:
                cursor = self.textCursor()
                cursor.setPosition(min(entry['cursor_position'], len(self.toPlainText())))
                self.setTextCursor(cursor)
            self.textChanged.connect(self.on_text_changed)

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])
                    self.history_index = len(self.history) - 1
                    if self.history:
                        last_entry = self.history[-1]
                        self.setHtml(last_entry['text'])
                        if 'cursor_position' in last_entry:
                            cursor = self.textCursor()
                            cursor.setPosition(min(last_entry['cursor_position'], len(self.toPlainText())))
                            self.setTextCursor(cursor)
        except Exception as e:
            self.is_error = True
            self.setHtml(f"<p style='color: red;'>Error loading history: {e}</p>")
            self.history = []
            self.history_index = -1

    def save_history(self):
        try:
            data = {
                'history': self.history,
                'current_index': self.history_index,
                'last_updated': datetime.now().isoformat(),
                'app_version': '2.0'
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.setHtml(f"<p style='color: red;'>Error saving history: {e}</p>")

    def setup_clipboard_catch(self):
        if self.clipboard_timer is None:
            self.clipboard_timer = QtCore.QTimer(self)  # Timer for clipboard polling
           
            self.clipboard_timer.setSingleShot(False)  # Repeat timer
            self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.set_clipboard_catch(self.clipboard_catch_enabled)

    def set_clipboard_catch(self, enabled: bool):
        self.clipboard_catch_enabled = enabled  # Set state
        if enabled:
            self.last_clipboard_text = QtWidgets.QApplication.clipboard().text()  # Track last clipboard
            self.clipboard_timer.start(1000)  # Poll every second
        else:
            self.clipboard_timer.stop()  # Stop polling

    def check_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()  # Get clipboard
        text = clipboard.text()  # Get text
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Timestamp
        if clipboard.mimeData().hasImage() and text != self.last_clipboard_text:  # Check for image
            image = QtGui.QImage(clipboard.mimeData().imageData())  # Get image data
            if not image.isNull():
                buffer = QtCore.QBuffer()
                buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
                image.save(buffer, "PNG")
                base64_data = base64.b64encode(buffer.data()).decode("utf-8")
                html = f'<img src="data:image/png;base64,{base64_data}" width="{image.width()}" height="{image.height()}">'
                self.textCursor().insertHtml(f'<br><pre style="color: #00ff00;background: #000000">----- {ts} ---- clipboard ----</pre><br>')   
                self.textCursor().insertHtml(html)
                self.textCursor().insertHtml(f'<br><pre style="color: #00ff00;background: #000000">--- end ---</pre><br>')
                self.last_clipboard_text = text
                return
        
        html_data = clipboard.mimeData().html() if clipboard.mimeData().hasHtml() else None  # Get HTML if present
        if text and text != self.last_clipboard_text:
            self.moveCursor(QtGui.QTextCursor.MoveOperation.End)  # Move to end
            
            # Always wrap clipboard content in a block with timestamp and delimiters
            if html_data:
                html = self.embed_external_images(html_data)
                html = self.sanitize_font_sizes(html)
                content = html  # Use HTML as-is
            else:
                content = html.escape(text)  # Escape plain text
            self.textCursor().insertHtml(f'<br><pre style="color: #00ff00;background: #000000">----- {ts} ---- clipboard ----</pre><br>')   
            self.textCursor().insertHtml(content)
            self.textCursor().insertHtml(f'<br><pre style="color: #00ff00;background: #000000">--- end ---</pre><br>')  # End block

            self.last_clipboard_text = text  # Update last

    def is_clipboard_catch_enabled(self):
        return self.clipboard_catch_enabled  # Return state
    
    def stop_bg_snippet(self, span_id):
        entry = self.bg_snippet_threads.get(span_id)
        if entry:
            thread, process = entry
            try:
                process.terminate()
            except Exception:
                pass
            self.bg_snippet_threads.pop(span_id, None)
    def handle_snippet(self, cursor, snippet_match):
        script_base = snippet_match.group(1)
        script_ext = snippet_match.group(2)
        attr_str = snippet_match.group(4)
        script_name = script_base + ".py"
        script_path = os.path.join(os.path.dirname(__file__), "snippets", script_name)
        env = os.environ.copy()
        if attr_str:
            for pair in attr_str.split(';'):
                if ':' in pair:
                    k, v = pair.split(':', 1)
                    k = k.strip().upper()
                    v = v.strip()
                    env[f"SNIPPET_{k}"] = v
        if os.path.exists(script_path):
            import subprocess
            import threading
            def run_background(span_id):
                try:
                    process = subprocess.Popen([
                        sys.executable, script_path
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                    self.bg_snippet_threads[span_id] = (threading.current_thread(), process)
                    from PyQt6.QtGui import QTextCursor
                    first = True
                    while True:
                        line = process.stdout.readline()
                        if not line:
                            break
                        line = line.strip()
                        if line.startswith("~[") and line.endswith("]"):
                            output = line[2:-1]
                            def update_output():
                                doc = self.document()
                                block = doc.begin()
                                found = False
                                while block.isValid():
                                    text = block.text()
                                    if f'id="{span_id}_out"' in text:
                                        cursor = QTextCursor(block)
                                        html = block.text()
                                        # Replace the span content
                                        import re
                                        new_html = re.sub(rf'<span id="{span_id}_out">.*?</span>', f'<span id="{span_id}_out">{output}</span>', html)
                                        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                                        cursor.removeSelectedText()
                                        cursor.insertHtml(new_html)
                                        found = True
                                        break
                                    block = block.next()
                                if not found:
                                    cursor = self.textCursor()
                                    cursor.movePosition(QTextCursor.MoveOperation.End)
                                    cursor.insertHtml(f'<span id="{span_id}_out">{output}</span>')
                            QtCore.QTimer.singleShot(0, update_output)
                    self.bg_snippet_threads.pop(span_id, None)
                except Exception as e:
                    def show_error():
                        cursor = self.textCursor()
                        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
                        cursor.insertHtml(f'<span id="{span_id}_out">[Error running snippet: {e}]</span>')
                    QtCore.QTimer.singleShot(0, show_error)
            if script_base.startswith("loop_") and False: # Disable looping for now not working
                span_id = str(uuid.uuid4().int)[:8]
                threading.Thread(target=run_background, args=(span_id,), daemon=True).start()
                cursor.removeSelectedText()
                cursor.deletePreviousChar()
                return
            # Otherwise, run as before (one-shot)
            try:
                kwargs = dict(capture_output=True, text=True, env=env)
                result = subprocess.run([
                    sys.executable, script_path
                ], **kwargs)
                output = result.stdout.strip()
                if result.stderr:
                    output += "\n[stderr]:\n" + result.stderr.strip()
            except Exception as e:
                output = f"[Error running snippet: {e}]"
            cursor.removeSelectedText()
            cursor.deletePreviousChar()
            if output.lstrip().startswith("<svg"):
                self.insert_svg_at_cursor(output)
            elif any(tag in output for tag in ("<span", "<b", "<i", "<u", "<font", "style=", "color=", "<br", "</")):
                cursor.insertHtml(output)
            else:
                cursor.insertText(output)
            return


    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & QtCore.Qt.KeyboardModifier.ControlModifier)
        alt = bool(mods & QtCore.Qt.KeyboardModifier.AltModifier)
        win = bool(key & (QtCore.Qt.Key.Key_Super_L | key & QtCore.Qt.Key.Key_Super_R)  )
        if alt and key in [QtCore.Qt.Key.Key_Left, QtCore.Qt.Key.Key_Right] and not ctrl:
            # Handle Win + Alt + Arrow keys for window movement
            if key == QtCore.Qt.Key.Key_Left:
                self.decrease()  # Decrease opacity
            elif key == QtCore.Qt.Key.Key_Right:
                self.increase()  # Increase opacity
        if ctrl and alt:
            # Handle Ctrl + Alt + Arrow keys for window movement
            screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
            if key == QtCore.Qt.Key.Key_Left:
                self.setGeometry(0, 0, screen.width() // 2, screen.height())  # Move to left half
            elif key == QtCore.Qt.Key.Key_Up:
                self.setGeometry(0, 0, screen.width(), screen.height())  # Move to top full screen
            elif key == QtCore.Qt.Key.Key_Right:
                self.setGeometry(screen.width() // 2, 0, screen.width() // 2, screen.height())  # Move to right half
            elif key == QtCore.Qt.Key.Key_Down:
                self.setGeometry(0, screen.height() // 2, screen.width(), screen.height() // 2)  # Move to bottom half


        if (ctrl and key == QtCore.Qt.Key.Key_F) or (not mods and key == QtCore.Qt.Key.Key_F3):
            self.close_search_and_replace_dialogs()
            self._search_dialog = SearchDialog(self, self)
            selected_text = self.textCursor().selectedText()
            if selected_text:
                self._search_dialog.set_query(selected_text)
            self._search_dialog.show()
            self._search_dialog.raise_()
            self._search_dialog.activateWindow()
            QtCore.QTimer.singleShot(0, self._search_dialog.focus_input)
            return
        if (ctrl and key == QtCore.Qt.Key.Key_H) or (alt and key == QtCore.Qt.Key.Key_F3):
            self.close_search_and_replace_dialogs()
            self._replace_dialog = ReplaceDialog(self, self)
            selected_text = self.textCursor().selectedText()
            if selected_text :
                self._replace_dialog.set_query(selected_text)
            self._replace_dialog.show()
            self._replace_dialog.raise_()
            self._replace_dialog.activateWindow()
            #QtCore.QTimer.singleShot(0, self._replace_dialog.focus_input)
            return
        # Snippet execution logic
        if key == QtCore.Qt.Key.Key_Return or key == QtCore.Qt.Key.Key_Enter:
            cursor = self.textCursor()
            cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
            line_text = cursor.selectedText().strip()
            # If line ends with >). trigger visualization
            if line_text.endswith('>).'):
                self.handle_html_tag_visualization(cursor)
            # Support both ~snippet.py{...} and ~snippet{...} (alias)
            snippet_match = re.match(r"~([\w_\-]+)(\.py)?(\{([^}]*)\})?", line_text)
            if snippet_match:
                self.handle_snippet(cursor, snippet_match)
                return
        # Scale image if selection is on image and + or - is pressed (no Ctrl)
        if (
            mods == QtCore.Qt.KeyboardModifier.NoModifier and
            key in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal, QtCore.Qt.Key.Key_Minus) and
            self.textCursor().charFormat().isImageFormat() and len(self.textCursor().selectedText())== 1
        ):
            cursor = self.textCursor()
            selected_text = cursor.selectedText()
            image = cursor.charFormat().toImageFormat()
            name = image.name()
            if not name:
                return  # no image name
            width = image.width()
            height = image.height()
            step = 10
            if key in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal):
                width += step
                height += step
            elif key == QtCore.Qt.Key.Key_Minus and width > 10 and height > 10:
                width -= step
                height -= step
            start = cursor.selectionStart()
            cursor.removeSelectedText()
            cursor.setPosition(start)
            image.setWidth(width)
            image.setHeight(height)
            cursor.insertImage(image)
            cursor.setPosition(start)
            cursor.setPosition(start + 1, QtGui.QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
            return

        if mods == ctrl and not alt and not win:
            if key == QtCore.Qt.Key.Key_C:
                self.copy()
                return
            elif key == QtCore.Qt.Key.Key_Z:
                super().undo()
                return
            elif key == QtCore.Qt.Key.Key_Y:
                super().redo()
                return
            elif key == QtCore.Qt.Key.Key_S:
                self.save_file()
                return
        # After all other logic, handle HTML tag visualization
        if event.text() in ('>', '/', '.'):
            cursor = self.textCursor()
            self.handle_html_tag_visualization(cursor)
        super().keyPressEvent(event)

    def handle_html_tag_visualization(self, cursor):
        import re
        # Get the current line
        cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()
        # Custom tag delimiters: .( ... ).
        tag_pattern = r'\.\((.*?)\)\.'
        match = re.search(tag_pattern, line_text, re.DOTALL)
        if match:
            # Tag is complete, render as HTML (activate)
            html_content = match.group(1)
            cursor.removeSelectedText()
            cursor.insertHtml(html_content)
        else:
            # Not a complete tag, show as plain text
            cursor.removeSelectedText()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
            cursor.insertText(line_text)

    def copy(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_html = cursor.selection().toHtml()
            selected_text = cursor.selectedText()
            clipboard = QtWidgets.QApplication.clipboard()
            mime = QtCore.QMimeData()
            mime.setHtml(selected_html)
            mime.setText(selected_text)
            clipboard.setMimeData(mime)
        else:
            super().copy()
    def embed_external_images(self, html):
        def replacer(match):
            url = match.group(1)
            try:
                response = requests.get(url)
                if response.ok:
                    img_data = response.content
                    base64_data = base64.b64encode(img_data).decode("utf-8")
                    return f'<img src="data:image/png;base64,{base64_data}"'
            except:
                pass
            return f'<img src=""'  # fallback

        # Replace all <img src="http..."> with embedded base64
        return re.sub(r'<img\s+[^>]*src="(http[^"]+)"', replacer, html)

    def sanitize_font_sizes(self, html):
        # Replace font-size: 0px or negative with a minimal valid size (e.g., 10px)
        html = re.sub(r'font-size\s*:\s*0px', 'font-size:10px', html, flags=re.IGNORECASE)
        html = re.sub(r'font-size\s*:\s*-[^;"]+', 'font-size:10px', html, flags=re.IGNORECASE)
        return html

    def insertFromMimeData(self, source: QtCore.QMimeData):
        if source.hasImage():
            image = QtGui.QImage(source.imageData())
            if not image.isNull():
                buffer = QtCore.QBuffer()
                buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
                image.save(buffer, "PNG")
                base64_data = base64.b64encode(buffer.data()).decode("utf-8")
                html = f'<img src="data:image/png;base64,{base64_data}" width="{image.width()}" height="{image.height()}">'
                self.textCursor().insertHtml(html)
                return
        if source.hasHtml():
            html = source.html()
            html = self.embed_external_images(html)
            html = self.sanitize_font_sizes(html)
            self.textCursor().insertHtml(html)
            return
        super().insertFromMimeData(source)

    def set_show_raw(self, raw: bool):
        self.show_raw = raw
        if raw:
            self.setPlainText(self.toHtml())
        else:
            # Always render the current plain text (raw HTML) as HTML
            self.setHtml(self.toPlainText())

    def setHtml(self, html):
        self._last_html = html  # Save last HTML for toggling
        super().setHtml(html)

    def close_search_and_replace_dialogs(self):
        if hasattr(self, '_search_dialog') and self._search_dialog is not None:
            self._search_dialog.close()
            self._search_dialog = None
        if hasattr(self, '_replace_dialog') and self._replace_dialog is not None:
            self._replace_dialog.close()
            self._replace_dialog = None

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        char_format = cursor.charFormat()
        if char_format.isAnchor():
            self.viewport().setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().setCursor(QtCore.Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            char_format = cursor.charFormat()
            if char_format.isAnchor():
                import webbrowser
                hrefs = char_format.anchorHref()
                if hrefs:
                    webbrowser.open(hrefs)
                    return  # Don't pass to super to avoid selection
        super().mousePressEvent(event)

class TrayManager(QtWidgets.QSystemTrayIcon):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.clipboard_action = None
        self.create_icon(show_red_dot=self.editor.is_clipboard_catch_enabled())
        self.create_menu()
        self.setup_signals()
        self.show()

    def create_icon(self, show_red_dot=False, change_color_to_gray=False):
        # Create a 32x32 tray icon for better appearance
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        # Draw main green square
        painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.green, 4))
        painter.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.darkGreen))
        painter.drawRect(4, 4, 24, 24)
        # Draw red dot if clipboard catch is enabled
        if show_red_dot:
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.red))
            painter.drawEllipse(11, 11, 10, 10)  # middle center 10 px width and height
        painter.end()
        self.setIcon(QtGui.QIcon(pixmap))
        if self.editor.show_raw:
            # Change icon color to gray if show_raw is enabled
            gray_pixmap = pixmap.toImage().convertToFormat(QtGui.QImage.Format.Format_ARGB32)
            for x in range(gray_pixmap.width()):
                for y in range(gray_pixmap.height()):
                    color = gray_pixmap.pixelColor(x, y)
                    gray_color = QtGui.QColor(color.red() // 2, color.green() // 2, color.blue() // 2)
                    gray_pixmap.setPixelColor(x, y, gray_color)
            self.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(gray_pixmap)))

    def update_icon(self):
        self.create_icon(show_red_dot=self.editor.is_clipboard_catch_enabled())

    def toggle_clipboard_catch(self):
        enabled = not self.editor.is_clipboard_catch_enabled()
        self.editor.set_clipboard_catch(enabled)
        self.clipboard_action.setText(self.get_clipboard_action_label())
        self.clipboard_action.setChecked(enabled)
        self.update_icon()

    def create_menu(self):
        menu = QtWidgets.QMenu()
        # Clipboard catch toggle
        self.clipboard_action = menu.addAction(self.get_clipboard_action_label())
        self.clipboard_action.setCheckable(True)
        self.clipboard_action.setChecked(self.editor.is_clipboard_catch_enabled())
        self.clipboard_action.triggered.connect(self.toggle_clipboard_catch)
        # Show Raw toggle
        self.show_raw_action = menu.addAction("Show Raw")
        self.show_raw_action.setCheckable(True)
        self.show_raw_action.setChecked(self.editor.show_raw)
        self.show_raw_action.triggered.connect(self.toggle_show_raw)
        self.show_raw_action.hovered.connect(self.handle_show_raw_hover)
        menu.addSeparator()
        settings_action = menu.addAction("⚙️ Settings")
        settings_action.triggered.connect(self.show_settings)
        menu.addSeparator()
        exit_action = menu.addAction("❌ Exit")
        exit_action.triggered.connect(self.exit_app)
        self.setContextMenu(menu)

    def toggle_show_raw(self):
        self.editor.set_show_raw(not self.editor.show_raw)
        self.show_raw_action.setChecked(self.editor.show_raw)

    def handle_show_raw_hover(self):
        # If right mouse button is pressed while hovering, toggle back to rendered
        import ctypes
        if ctypes.windll.user32.GetAsyncKeyState(0x02):  # VK_RBUTTON
            self.editor.set_show_raw(False)
            self.show_raw_action.setChecked(False)

    def setup_signals(self):
        self.activated.connect(self.on_tray_activated)

    def toggle_editor_visibility(self):
        if self.editor.isVisible():
            self.editor.hide()
        else:
            self.editor.show()
            self.editor.raise_()
            self.editor.activateWindow()

    def show_settings(self):
        dlg = SettingsDialog(self.editor, self.editor.font(), self.editor.history_file)
        if dlg.exec():
            self.editor.setFont(dlg.font)
            self.editor.history_file = dlg.path_edit.text()
            self.editor.save_config(font=dlg.font, history_file=dlg.path_edit.text())

    def on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_editor_visibility()

    def exit_app(self):
        self.editor.save_file()
        self.editor.save_config()
        QtWidgets.QApplication.quit()

    def get_clipboard_action_label(self):
        return ("Disable Clipboard Catch" if self.editor.is_clipboard_catch_enabled() else "Enable Clipboard Catch")

class SearchDialog(QtWidgets.QDialog):
    __m = None
    def __init__(self, parent, editor):
        super().__init__(parent)
        self.editor = editor
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setFixedSize(250, 70)
        self.setStyleSheet('''
            QDialog { background: rgba(30,30,30,0.98); border-radius: 6px; }
            QLineEdit { background: #222; color: #fff; border: none; padding: 4px 8px; min-width: 120px; }
            QPushButton { background: transparent; border: none; min-width: 24px; min-height: 24px; }
            QPushButton:hover { background: #333; }
        ''')
        # --- SearchDialog layout update with count label ---
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        self.search_btn = QtWidgets.QPushButton(self)
        self.search_btn.setIcon(QtGui.QIcon.fromTheme('edit-find'))
        self.search_btn.setToolTip('Search')
        self.search_btn.setFixedSize(24, 24)
        self.search_btn.clicked.connect(lambda: self.find_next(backward=False))
        layout.addWidget(self.search_btn)
        self.input = QtWidgets.QLineEdit(self)
        self.input.setPlaceholderText("Find...")
        self.input.returnPressed.connect(self._handle_return)
        layout.addWidget(self.input)
        # Add count label
        self.count_label = QtWidgets.QLabel(self)
        self.count_label.setStyleSheet('color: #aaa; min-width: 48px;')
        self.count_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.count_label)
        self.close_btn = QtWidgets.QPushButton(self)
        self.close_btn.setIcon(QtGui.QIcon.fromTheme('window-close'))
        self.close_btn.setToolTip('Close')
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self._restore_focus_widget = None
        self.finished.connect(self._on_dialog_closed)
        if hasattr(self.editor, '_last_search'):
            self.input.setText(self.editor._last_search)
        self.input.textChanged.connect(self._persist_last_search)

    def _persist_last_search(self):
        if hasattr(self.editor, '_last_search'):
            self.editor._last_search = self.input.text()
            self.editor.save_config()

    def set_query(self, text):
        self.input.setText(text)
        self.input.selectAll()
        QtCore.QTimer.singleShot(0, self.find_next)  # Immediately search after setting query

    def focus_input(self):
        QtCore.QTimer.singleShot(0, self._focus_input)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            parent_geom = self.parent().geometry()
            x = parent_geom.x() + parent_geom.width() - self.width() - 16
            y = parent_geom.y() 
            self.move(x, y)
        self._restore_focus_widget = self.editor
        self.focus_input()

    def _focus_input(self):
        self.input.setFocus()
        self.input.selectAll()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focus_input()

    def closeEvent(self, event):
        # Save last value on close
        if hasattr(self.editor, '_last_search'):
            self.editor._last_search = self.input.text()
            self.editor.save_config()
        super().closeEvent(event)
        # Restore focus to editor after dialog closes
        if self._restore_focus_widget:
            QtCore.QTimer.singleShot(0, self._restore_focus_widget.setFocus)

    def _on_dialog_closed(self, result):
        # Ensure focus returns to editor after dialog closes
        if self._restore_focus_widget:
            QtCore.QTimer.singleShot(0, self._restore_focus_widget.setFocus)

    def _handle_return(self):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
            self.find_next(backward=True)
        else:
            self.find_next(backward=False)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key.Key_F3, QtCore.Qt.Key.Key_F) and (
            event.modifiers() in [QtCore.Qt.KeyboardModifier.NoModifier, QtCore.Qt.KeyboardModifier.ControlModifier]
        ):
            self.find_next(backward=False)
            return
        if event.key() in (QtCore.Qt.Key.Key_F3, QtCore.Qt.Key.Key_F) and (
            event.modifiers() in [QtCore.Qt.KeyboardModifier.ShiftModifier, QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier]
        ):
            self.find_next(backward=True)
            return
        super().keyPressEvent(event)

    def update_count_label(self, current=0, total=0):
        if total > 0:
            self.count_label.setText(f"{current} / {total}")
        else:
            self.count_label.setText("")

    def find_next(self, backward=False):
        query = self.input.text()
        if not query:
            self.update_count_label(0, 0)
            return
        doc = self.editor.document()
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()
        is_current_match = selected_text == query
        if not backward:
            if is_current_match:
                start_pos = cursor.selectionEnd()
            else:
                start_pos = cursor.position()
        else:
            if is_current_match:
                start_pos = cursor.selectionStart()
            else:
                start_pos = cursor.position()
        flags = QtGui.QTextDocument.FindFlag(0)
        if backward:
            flags = QtGui.QTextDocument.FindFlag.FindBackward
        found = doc.find(query, start_pos, flags)
        if found.isNull():
            if backward:
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            else:
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            found = doc.find(query, cursor, flags)
        if not found.isNull():
            self.editor.setTextCursor(found)
            self.editor.ensureCursorVisible()
        all_matches = []
        match_cursor = doc.find(query, 0)
        while not match_cursor.isNull():
            all_matches.append(match_cursor.selectionStart())
            match_cursor = doc.find(query, match_cursor.selectionEnd())
        total = len(all_matches)
        current = 0
        if total > 0:
            cur_pos = self.editor.textCursor().selectionStart()
            try:
                current = all_matches.index(cur_pos) + 1
            except ValueError:
                current = 1
        self.update_count_label(current, total)

class ReplaceDialog(QtWidgets.QDialog):
    def __init__(self, parent, editor):
        super().__init__(parent)
        self.editor = editor
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setFixedSize(250, 70)
        self.setStyleSheet('''
            QDialog { background: rgba(30,30,30,0.98); border-radius: 6px; }
            QLineEdit { background: #222; color: #fff; border: none; padding: 4px 8px; min-width: 120px; }
            QPushButton { background: transparent; border: none; min-width: 24px; min-height: 24px; }
            QPushButton:hover { background: #333; }
        ''')
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(8, 4, 8, 4)
        grid.setHorizontalSpacing(2)
        grid.setVerticalSpacing(2)
        self.search_btn = QtWidgets.QPushButton(self)
        self.search_btn.setIcon(QtGui.QIcon.fromTheme('edit-find'))
        self.search_btn.setToolTip('Search')
        self.search_btn.setFixedSize(24, 24)
        self.search_btn.clicked.connect(lambda: self.find_next(backward=False))
        grid.addWidget(self.search_btn, 0, 0, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.input_find = QtWidgets.QLineEdit(self)
        self.input_find.setPlaceholderText("Find…")
        self.input_find.setMinimumWidth(120)
        self.input_find.setMaximumWidth(120)
        self.input_find.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        grid.addWidget(self.input_find, 0, 1)
        self.count_label = QtWidgets.QLabel(self)
        self.count_label.setStyleSheet('color: #aaa; min-width: 48px;')
        self.count_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.count_label, 0, 2)
        self.close_btn = QtWidgets.QPushButton(self)
        self.close_btn.setIcon(QtGui.QIcon.fromTheme('window-close'))
        self.close_btn.setToolTip('Close')
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.close)
        grid.addWidget(self.close_btn, 0, 3, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.replace_this_btn = QtWidgets.QPushButton(self)
        self.replace_this_btn.setIcon(QtGui.QIcon.fromTheme('go-next'))
        self.replace_this_btn.setToolTip('Replace This')
        self.replace_this_btn.setFixedSize(24, 24)
        self.replace_this_btn.clicked.connect(lambda: self.replace_one(find_next=True))
        grid.addWidget(self.replace_this_btn, 1, 0, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.input_replace = QtWidgets.QLineEdit(self)
        self.input_replace.setPlaceholderText("Replace…")
        self.input_replace.setMinimumWidth(120)
        self.input_replace.setMaximumWidth(120)
        self.input_replace.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        grid.addWidget(self.input_replace, 1, 1)
        self.replace_all_btn = QtWidgets.QPushButton(self)
        self.replace_all_btn.setIcon(QtGui.QIcon.fromTheme('replace-all', QtGui.QIcon.fromTheme('edit-select-all')))
        self.replace_all_btn.setToolTip('Replace All')
        self.replace_all_btn.setFixedSize(24, 24)
        self.replace_all_btn.clicked.connect(self.replace_all)
        grid.addWidget(self.replace_all_btn, 1, 3, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self._restore_focus_widget = None
        self.finished.connect(self._on_dialog_closed)
        self.input_find.returnPressed.connect(self._handle_return)
        self.input_find.textChanged.connect(lambda: self.find_next(backward=False))

        if hasattr(self.editor, '_last_replace_find'):
            self.input_find.setText(self.editor._last_replace_find)
        if hasattr(self.editor, '_last_replace_replace'):
            self.input_replace.setText(self.editor._last_replace_replace)
        self.input_find.textChanged.connect(self._persist_last_replace_find)
        self.input_replace.textChanged.connect(self._persist_last_replace_replace)

    def _persist_last_replace_find(self):
        if hasattr(self.editor, '_last_replace_find'):
            self.editor._last_replace_find = self.input_find.text()
            self.editor.save_config()
    def _persist_last_replace_replace(self):
        if hasattr(self.editor, '_last_replace_replace'):
            self.editor._last_replace_replace = self.input_replace.text()
            self.editor.save_config()
    def closeEvent(self, event):
        if hasattr(self.editor, '_last_replace_find'):
            self.editor._last_replace_find = self.input_find.text()
        if hasattr(self.editor, '_last_replace_replace'):
            self.editor._last_replace_replace = self.input_replace.text()
        self.editor.save_config()
        super().closeEvent(event)
        if self._restore_focus_widget:
            QtCore.QTimer.singleShot(0, self._restore_focus_widget.setFocus)

    def _on_dialog_closed(self, result):
        if self._restore_focus_widget:
            QtCore.QTimer.singleShot(0, self._restore_focus_widget.setFocus)

    def _handle_return(self):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
            self.find_next(backward=True)
        else:
            self.find_next(backward=False)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key.Key_F3, QtCore.Qt.Key.Key_H) and (
            event.modifiers() in [QtCore.Qt.KeyboardModifier.NoModifier, QtCore.Qt.KeyboardModifier.ControlModifier]
        ):
            self.find_next(backward=False)
            return
        if event.key() in (QtCore.Qt.Key.Key_F3, QtCore.Qt.Key.Key_H) and (
            event.modifiers() in [QtCore.Qt.KeyboardModifier.ShiftModifier, QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier]
        ):
            self.find_next(backward=True)
            return
        if event.modifiers() == QtCore.Qt.KeyboardModifier.AltModifier and event.key() in (QtCore.Qt.Key.Key_F, QtCore.Qt.Key.Key_H):
            self.replace_one(find_next=True)
            return
        super().keyPressEvent(event)

    def update_count_label(self, current=0, total=0):
        if total > 0:
            self.count_label.setText(f"{current} / {total}")
        else:
            self.count_label.setText("")

    def find_next(self, backward=False):
        query = self.input_find.text()
        if not query:
            self.update_count_label(0, 0)
            return
        doc = self.editor.document()
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()
        is_current_match = selected_text == query
        if not backward:
            if is_current_match:
                start_pos = cursor.selectionEnd()
            else:
                start_pos = cursor.position()
        else:
            if is_current_match:
                start_pos = cursor.selectionStart()
            else:
                start_pos = cursor.position()
        flags = QtGui.QTextDocument.FindFlag(0)
        if backward:
            flags = QtGui.QTextDocument.FindFlag.FindBackward
        found = doc.find(query, start_pos, flags)
        if found.isNull():
            if backward:
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            else:
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            found = doc.find(query, cursor, flags)
        if not found.isNull():
            self.editor.setTextCursor(found)
            self.editor.ensureCursorVisible()
        all_matches = []
        match_cursor = doc.find(query, 0)
        while not match_cursor.isNull():
            all_matches.append(match_cursor.selectionStart())
            match_cursor = doc.find(query, match_cursor.selectionEnd())
        total = len(all_matches)
        current = 0
        if total > 0:
            cur_pos = self.editor.textCursor().selectionStart()
            try:
                current = all_matches.index(cur_pos) + 1
            except ValueError:
                current = 1
        self.update_count_label(current, total)

    def replace_one(self, find_next=False):
        query = self.input_find.text()
        replace_text = self.input_replace.text()
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()
        if selected_text == query:
            cursor.insertText(replace_text)
            self.editor.setTextCursor(cursor)
        if find_next:
            self.find_next(backward=False)
        else:
            self.find_next(backward=False)

    def replace_all(self):
        query = self.input_find.text()
        replace_text = self.input_replace.text()
        if not query:
            self.update_count_label(0, 0)
            return
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        doc = self.editor.document()
        found = doc.find(query, 0)
        replaced = 0
        while not found.isNull():
            found.insertText(replace_text)
            replaced += 1
            pos = found.position() + len(replace_text)
            found = doc.find(query, pos)
        cursor.endEditBlock()
        self.find_next(backward=False)
    def showEvent(self, event):
        super().showEvent(event)
        # Position at top-right of parent
        if self.parent():
            parent_geom = self.parent().geometry()
            x = parent_geom.x() + parent_geom.width() - self.width() - 16
            y = parent_geom.y()
            self.move(x, y)
        # Save the widget to restore focus to after closing
        self._restore_focus_widget = self.editor
        # Use a single-shot timer to focus/select after rendering
        self.focus_input()
        # Remove _first_show logic
    def focus_input(self):
        QtCore.QTimer.singleShot(0, self._focus_input)
    def _focus_input(self):
        self.input_find.setFocus()
        self.input_find.selectAll()
    def set_query(self, text):
        self.input_find.setText(text)
        self.input_find.selectAll()
        QtCore.QTimer.singleShot(0, self.find_next)  # Immediately search after setting query

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    editor = DesktopTextBoard()
    tray = TrayManager(editor, parent=editor)
    editor.show()
    app.setApplicationName("Desktop TextBoard")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("TextBoard")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
