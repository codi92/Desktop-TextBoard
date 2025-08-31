import sys, os, re, json, base64, html, uuid, requests,ctypes
from datetime import datetime
from PyQt6 import QtWidgets, QtCore, QtGui
from functions.wallpaper_color import get_desktop_base_color, windows_is_dark_mode
from functions.clipboard import clipboard_output, insert_to_cursor
from functions.secondmenu import show_rich_context_menu
from functions.modules import FindReplaceDialog , TrayManager
from datetime import datetime
from functions.telegram import send_html_message, get_saved_messages_html, send_file_to_saved, download_large_file
import asyncio, threading, subprocess
from threading import Thread

def restart_script():
    print("Restarting...")
    python = sys.executable
    os.execl(python, python, *sys.argv)

def get_config_path():
    home = os.path.expanduser("~")
    return os.path.join(home, ".config_desktop_textboard.json")


class DesktopTextBoard(QtWidgets.QTextEdit):
    def __init__(self):
        super().__init__()
        self.show_raw = False
        self.history_file = "textboard_history.json"
        self.auto_save_timer = None
        self.clipboard_catch_enabled = False
        self.clipboard_timer = None
        self.last_clipboard = [image, html, text, files] = [None] * 4
        self.bg_snippet_threads = {}
        self.opacity = 1.0
        self.disable_transparency = False
        self.setup_ui()
        self.load_config()
        self.load_file()
        self.setup_auto_save()
        self.setup_clipboard_catch()
        self.set_theme()
        self.theme_timer = QtCore.QTimer(self)
        self.theme_timer.timeout.connect(self.set_theme)
        self.theme_timer.start(1000)
        self.update_opacity()
        self.is_error = False




    def show_stop_snippet_dialog(self):
        if not self.bg_snippet_threads:
            QtWidgets.QMessageBox.information(
                self,
                "No Background Snippets",
                "No background snippets are currently running.",
            )
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
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
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
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnBottomHint
            | QtCore.Qt.WindowType.Tool
        )

        self.titlebar = QtWidgets.QWidget(self)
        self.titlebar.setFixedHeight(5)
        self.titlebar.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self.titlebar.setStyleSheet("background: rgba(80,80,80,0.18);")
        self.titlebar.setGeometry(0, 0, self.width(), 5)
        self.titlebar.mousePressEvent = self._titlebar_mouse_press
        self.titlebar.mouseMoveEvent = self._titlebar_mouse_move
        self.titlebar.mouseReleaseEvent = self._titlebar_mouse_release
        self._drag_pos = None
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen.width() // 2, 0, screen.width() // 2, screen.height())
        self.setWindowOpacity(1.0)
        self.setWindowTitle("Desktop TextBoard")
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    def _titlebar_mouse_press(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            wh = self.windowHandle()
            if hasattr(wh, "startSystemMove"):
                wh.startSystemMove()
            else:
                self._drag_pos = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )

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
            color = QtGui.QColor(
                max(0, red - 30), max(0, green - 30), max(0, blue - 30)
            )
            border_color = QtGui.QColor(
                max(0, red - 50), max(0, green - 50), max(0, blue - 50)
            )
            font_color = QtGui.QColor(200, 200, 200)
            selection_color = QtGui.QColor(
                max(0, red - 80), max(0, green - 80), max(0, blue - 80)
            )
            selection_bg_color = QtGui.QColor(30, 30, 30)
        else:
            color = QtGui.QColor(
                max(0, red + 30), max(0, green + 30), max(0, blue + 30)
            )
            border_color = QtGui.QColor(
                max(0, red + 50), max(0, green + 50), max(0, blue + 50)
            )
            font_color = QtGui.QColor(30, 30, 30)
            selection_color = QtGui.QColor(
                max(0, red + 80), max(0, green + 80), max(0, blue + 80)
            )
            selection_bg_color = QtGui.QColor(240, 240, 240)
        self.toolTipStyle = f"QToolTip {{ background-color: {color.name()}; color: {font_color.name()}; border: 1px solid {border_color.name()}; padding: 5px; }}"
        self.setStyleSheet(
            """
            QTextEdit {
                background: """
            + color.name()
            + """;
                color: """
            + font_color.name()
            + """;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 15px;
                padding: 12px;
                border: 1.5px solid """
            + border_color.name()
            + """;
                selection-background-color: """
            + selection_bg_color.name()
            + """;
                selection-color: """
            + selection_color.name()
            + """;
            }
        """
        )

    def update_opacity(self):
        if getattr(self, "disable_transparency", False):
            self.setWindowOpacity(1.0)
        else:
            self.setWindowOpacity(self.opacity)

    def increase(self):
        if not getattr(self, "disable_transparency", False):
            self.opacity = min(1.0, self.opacity + 0.1)
            self.update_opacity()
            self.save_config()

    def decrease(self):
        if not getattr(self, "disable_transparency", False):
            self.opacity = max(0.1, self.opacity - 0.1)
            self.update_opacity()
            self.save_config()

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
                self.opacity = float(config.get("opacity", 1.0))
            except Exception as e:
                if not self.is_error:
                    self.is_error = True
                    self.setHtml(
                        f"<p style='color: red;'>Error loading config: {e}</p>"
                    )
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
            "disable_transparency": getattr(self, "disable_transparency", False),
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.setHtml(f"<p style='color: red;'>Error saving config: {e}</p>")

    def setup_auto_save(self):
        self.auto_save_timer = QtCore.QTimer()
        self.auto_save_timer.timeout.connect(self.save_file)
        self.auto_save_timer.start(3000)
        self.textChanged.connect(self.save_file)

    def load_file(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.setHtml(data.get("text", ""))
            except Exception as e:
                self.setHtml(f"<p style='color: red;'>Error loading file: {e}</p>")

    def save_file(self):
        if not self.is_error:
            try:
                data = {
                    "text": self.toHtml(),
                    "last_updated": datetime.now().isoformat(),
                    "app_version": "2.0",
                }
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.is_error = True
                self.setHtml(f"<p style='color: red;'>Error saving file: {e}</p>")

    def closeEvent(self, event):
        self.save_file()
        self.save_config()
        if self.auto_save_timer:
            self.auto_save_timer.stop()
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
        if self.history and self.history[-1]["text"] == current_text:
            return
        entry = {
            "text": current_text,
            "timestamp": timestamp,
            "cursor_position": self.textCursor().position(),
        }
        if self.history_index < len(self.history) - 1:
            self.history = self.history[: self.history_index + 1]
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
            self.setHtml(entry["text"])
            if "cursor_position" in entry:
                cursor = self.textCursor()
                cursor.setPosition(
                    min(entry["cursor_position"], len(self.toPlainText()))
                )
                self.setTextCursor(cursor)
            self.textChanged.connect(self.on_text_changed)

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
                    self.history_index = len(self.history) - 1
                    if self.history:
                        last_entry = self.history[-1]
                        self.setHtml(last_entry["text"])
                        if "cursor_position" in last_entry:
                            cursor = self.textCursor()
                            cursor.setPosition(
                                min(
                                    last_entry["cursor_position"],
                                    len(self.toPlainText()),
                                )
                            )
                            self.setTextCursor(cursor)
        except Exception as e:
            self.is_error = True
            self.setHtml(f"<p style='color: red;'>Error loading history: {e}</p>")
            self.history = []
            self.history_index = -1

    def save_history(self):
        try:
            data = {
                "history": self.history,
                "current_index": self.history_index,
                "last_updated": datetime.now().isoformat(),
                "app_version": "2.0",
            }
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.setHtml(f"<p style='color: red;'>Error saving history: {e}</p>")

    def setup_clipboard_catch(self):
        if self.clipboard_timer is None:
            self.clipboard_timer = QtCore.QTimer(self)
            self.clipboard_timer.setSingleShot(False)
            self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.set_clipboard_catch(self.clipboard_catch_enabled)

    def set_clipboard_catch(self, enabled: bool):
        self.clipboard_catch_enabled = enabled
        if enabled:
            self.last_clipboard = [None] * 4
            self.clipboard_timer.start(1000)
        else:
            self.clipboard_timer.stop()

    def check_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        html_data = (
            clipboard.mimeData().html() if clipboard.mimeData().hasHtml() else None
        )
        image_data = (
            clipboard.mimeData().imageData()
            if clipboard.mimeData().hasImage()
            else None
        )
        files_data = (
            clipboard.mimeData().urls() if clipboard.mimeData().hasUrls() else None
        )
        text = clipboard.mimeData().text() if clipboard.mimeData().hasText() else None
        image = QtGui.QImage(image_data) if image_data else None
        if (
            text != self.last_clipboard[2]
            or image != self.last_clipboard[1]
            or html_data != self.last_clipboard[0]
            or files_data != self.last_clipboard[3]
        ):
            content = clipboard_output(self, clipboard)
            self.last_clipboard = [html_data, image, text, files_data]
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            header = f'<pre style="color: #00ff00;background: #000000">--- {ts} - clipboard ---</pre><br>'
            footer = f'<br><pre style="color: #00ff00;background: #000000"> --- end ---</pre><br>'
            self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
            self.textCursor().insertHtml(header)
            self.textCursor().insertHtml(content)
            self.textCursor().insertHtml(footer)
            return

    def is_clipboard_catch_enabled(self):
        return self.clipboard_catch_enabled

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
            for pair in attr_str.split(";"):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    k = k.strip().upper()
                    v = v.strip()
                    env[f"SNIPPET_{k}"] = v
        if os.path.exists(script_path):
            import subprocess
            import threading

            def run_background(span_id):
                try:
                    process = subprocess.Popen(
                        [sys.executable, script_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=env,
                    )
                    self.bg_snippet_threads[span_id] = (
                        threading.current_thread(),
                        process,
                    )
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
                                        new_html = re.sub(
                                            rf'<span id="{span_id}_out">.*?</span>',
                                            f'<span id="{span_id}_out">{output}</span>',
                                            html,
                                        )
                                        cursor.select(
                                            QTextCursor.SelectionType.BlockUnderCursor
                                        )
                                        cursor.removeSelectedText()
                                        cursor.insertHtml(new_html)
                                        found = True
                                        break
                                    block = block.next()
                                if not found:
                                    cursor = self.textCursor()
                                    cursor.movePosition(QTextCursor.MoveOperation.End)
                                    cursor.insertHtml(
                                        f'<span id="{span_id}_out">{output}</span>'
                                    )
                            QtCore.QTimer.singleShot(0, update_output)
                    self.bg_snippet_threads.pop(span_id, None)
                except Exception as e:

                    def show_error():
                        cursor = self.textCursor()
                        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
                        cursor.insertHtml(
                            f'<span id="{span_id}_out">[Error running snippet: {e}]</span>'
                        )

                    QtCore.QTimer.singleShot(0, show_error)
            if script_base.startswith("loop_") and False:
                span_id = str(uuid.uuid4().int)[:8]
                threading.Thread(
                    target=run_background, args=(span_id,), daemon=True
                ).start()
                cursor.removeSelectedText()
                cursor.deletePreviousChar()
                return
            try:
                kwargs = dict(capture_output=True, text=True, env=env)
                result = subprocess.run([sys.executable, script_path], **kwargs)
                output = result.stdout.strip()
                if result.stderr:
                    output += "\n[stderr]:\n" + result.stderr.strip()
            except Exception as e:
                output = f"[Error running snippet: {e}]"
            cursor.removeSelectedText()
            cursor.deletePreviousChar()
            if output.lstrip().startswith("<svg"):
                self.insert_svg_at_cursor(output)
            elif any(
                tag in output
                for tag in (
                    "<span",
                    "<b",
                    "<i",
                    "<u",
                    "<font",
                    "style=",
                    "color=",
                    "<br",
                    "</",
                )
            ):
                cursor.insertHtml(output)
            else:
                cursor.insertText(output)
            return

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & QtCore.Qt.KeyboardModifier.ControlModifier)
        alt = bool(mods & QtCore.Qt.KeyboardModifier.AltModifier)
        win = bool(key & (QtCore.Qt.Key.Key_Super_L | key & QtCore.Qt.Key.Key_Super_R))
        shift = bool(mods & QtCore.Qt.KeyboardModifier.ShiftModifier)
        if ctrl and shift and key == QtCore.Qt.Key.Key_V:
            clipboard = QtWidgets.QApplication.clipboard()
            text = clipboard.mimeData().text()
            if text:
                cursor = self.textCursor()
                cursor.insertText(text)
            return
        if ctrl and key == QtCore.Qt.Key.Key_R:
            restart_script()
        if (
            alt
            and key in [QtCore.Qt.Key.Key_Left, QtCore.Qt.Key.Key_Right]
            and not ctrl
        ):
            if key == QtCore.Qt.Key.Key_Left:
                self.decrease()
            elif key == QtCore.Qt.Key.Key_Right:
                self.increase()
        if ctrl and alt:
            screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
            if key == QtCore.Qt.Key.Key_Left:
                self.setGeometry(0, 0, screen.width() // 2, screen.height())
            elif key == QtCore.Qt.Key.Key_Up:
                self.setGeometry(0, 0, screen.width(), screen.height())
            elif key == QtCore.Qt.Key.Key_Right:
                self.setGeometry(
                    screen.width() // 2, 0, screen.width() // 2, screen.height()
                )
            elif key == QtCore.Qt.Key.Key_Down:
                self.setGeometry(
                    0, screen.height() // 2, screen.width(), screen.height() // 2
                )
        if (ctrl and key == QtCore.Qt.Key.Key_F) or (
            not mods and key == QtCore.Qt.Key.Key_F3
        ):
            self.close_search_and_replace_dialogs()
            self._search_dialog = FindReplaceDialog(self, mode="search")
            selected_text = self.textCursor().selectedText()
            if selected_text:
                self._search_dialog.set_query(selected_text)
            self._search_dialog.show()
            self._search_dialog.raise_()
            self._search_dialog.activateWindow()
            QtCore.QTimer.singleShot(0, self._search_dialog.focus_input)
            return
        if (ctrl and key == QtCore.Qt.Key.Key_H) or (
            alt and key == QtCore.Qt.Key.Key_F3
        ):
            self.close_search_and_replace_dialogs()
            self._replace_dialog = FindReplaceDialog(self, mode="replace")
            selected_text = self.textCursor().selectedText()
            if selected_text:
                self._replace_dialog.set_query(selected_text)
            self._replace_dialog.show()
            self._replace_dialog.raise_()
            self._replace_dialog.activateWindow()
            return

        if key == QtCore.Qt.Key.Key_Return or key == QtCore.Qt.Key.Key_Enter:
            cursor = self.textCursor()
            cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
            line_text = cursor.selectedText().strip()
            check_box = re.match(r"^\[([ x])\] (.*)", line_text)
            snippet_match = re.match(r"~([\w_\-]+)(\.py)?(\{([^}]*)\})?", line_text)
            ctrl = bool(mods & QtCore.Qt.KeyboardModifier.ControlModifier)
            # The telegram catching part
            if line_text.startswith("[t]") or line_text.startswith("[T]"):
                #left text beafore Error
                if "Error" in line_text :
                    line_text = line_text.split("Error", 1)[0]
                elif "Failed" in line_text:
                    line_text = line_text.split("Failed", 1)[0]
                text_to_send = line_text[3:].strip()
                if not text_to_send or text_to_send == " ":
                    return
                def send_to_telegram(html):
                    cursor.beginEditBlock()
                    cursor.removeSelectedText()
                    if not html or not ("Error" in html  or "Failed" in html):
                        cursor.insertText(f"[s] {html}")
                        cursor.endEditBlock()
                    else:
                        cursor.insertHtml(f'{line_text} <span style="color: red;"> {html}</span>')
                        cursor.endEditBlock()
                send_html_message(text_to_send, callback=send_to_telegram)
                return
            elif line_text.startswith("[p]") or line_text.startswith("[P]"):
                def run():
                    asyncio.run(send_file_to_saved(line_text))
                Thread(target=run, daemon=True).start()
                return
            elif line_text.startswith("[gt]"):
                def insert_messages_table(html):
                    cursor = self.textCursor()
                    cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
                    cursor.insertHtml("<br><b>Saved Messages:</b><br>" + html)

                get_saved_messages_html(callback=insert_messages_table)
                return

            if line_text.endswith(">)."):
                self.handle_html_tag_visualization(cursor)
            elif snippet_match:
                self.handle_snippet(cursor, snippet_match)
                return
            elif check_box and ctrl:
                block = cursor.block()
                block_pos = block.position()
                checked = check_box.group(1) == "x"
                content = check_box.group(2)
                new_line = f"[ ] {content}" if checked else f"[x] {content}"
                cursor.setPosition(block_pos)
                cursor.movePosition(
                    QtGui.QTextCursor.MoveOperation.EndOfBlock,
                    QtGui.QTextCursor.MoveMode.KeepAnchor
                )
                cursor.insertText(new_line)
                fmt = QtGui.QTextCharFormat()
                cursor.setPosition(block_pos)
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock, QtGui.QTextCursor.MoveMode.KeepAnchor)
                if not checked:
                    fmt.setFontStrikeOut(True)
                else:
                    fmt.setFontStrikeOut(False)
                cursor.setCharFormat(fmt)
                return
            elif shift:
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Up)
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
                self.setTextCursor(cursor)
                return
            elif ctrl:
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Down)
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
                self.setTextCursor(cursor)
                return
        if (
            mods == QtCore.Qt.KeyboardModifier.NoModifier
            and key
            in (
                QtCore.Qt.Key.Key_Plus,
                QtCore.Qt.Key.Key_Equal,
                QtCore.Qt.Key.Key_Minus,
            )
            and self.textCursor().charFormat().isImageFormat()
            and len(self.textCursor().selectedText()) == 1
        ):
            cursor = self.textCursor()
            selected_text = cursor.selectedText()
            image = cursor.charFormat().toImageFormat()
            name = image.name()
            if not name:
                return
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

        if event.text() in (">", "/", "."):
            cursor = self.textCursor()
            self.handle_html_tag_visualization(cursor)
        super().keyPressEvent(event)

    def handle_html_tag_visualization(self, cursor):
        import re

        cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()
        tag_pattern = r"\.\((.*?)\)\."
        match = re.search(tag_pattern, line_text, re.DOTALL)
        if match:
            html_content = match.group(1)
            cursor.removeSelectedText()
            cursor.insertHtml(html_content)
        else:
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

    def insertFromMimeData(self, source):
        insert_to_cursor(self, source, self.textCursor())

    def set_show_raw(self, raw: bool):
        self.show_raw = raw
        if raw:
            self.setPlainText(self.toHtml())
        else:
            self.setHtml(self.toPlainText())

    def setHtml(self, html):
        self._last_html = html
        super().setHtml(html)

    def close_search_and_replace_dialogs(self):
        if hasattr(self, "_search_dialog") and self._search_dialog is not None:
            self._search_dialog.close()
            self._search_dialog = None
        if hasattr(self, "_replace_dialog") and self._replace_dialog is not None:
            self._replace_dialog.close()
            self._replace_dialog = None

    def contextMenuEvent(self, event):
        ctrl = bool(event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier)
        alt = bool(event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier)
        cursor = self.cursorForPosition(event.pos())
        char_format = cursor.charFormat()
        if char_format.isAnchor():
            menu = self.createStandardContextMenu()
            url = char_format.anchorHref()
            if url and not url.startswith("teletelegram_msg_id"):
                return
            if url:
                copy_url_action = menu.addAction("Copy Link URL")
                copy_url_action.triggered.connect(
                    lambda: QtWidgets.QApplication.clipboard().setText(url)
                )
            menu.exec(event.globalPos())
        elif ctrl:
            super().copy()
            return
        elif alt:
            super().paste()
            return
        else:
            show_rich_context_menu(self, event)

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        char_format = cursor.charFormat()
        if char_format.isAnchor():
            self.viewport().setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            url = char_format.anchorHref()
            if url:
                tooltip = f"Link: {url}"
                QtWidgets.QToolTip.showText(
                    event.globalPosition().toPoint(), tooltip, self.viewport()
                )
        else:
            self.viewport().setCursor(QtCore.Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        ctrl = bool(event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier)
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            char_format = cursor.charFormat()
            if char_format.isAnchor():
                import webbrowser
                hrefs = char_format.anchorHref()
                if not hrefs.startswith("teletelegram_msg_id"):
                    id=hrefs.split("=")[-1]
                    if id.isdigit():
                        #
                        try:          
                            def run():                
                                asyncio.run(download_large_file(int(id)))
                            Thread(target=run, daemon=True).start()
                            #todo add update the message to the file path store the pozition of the message than is received to update the message

                        except Exception as e:
                            QtWidgets.QMessageBox.warning(None, "Error", f"Failed to download file: {e}")
                    return
                if hrefs:
                    webbrowser.open(hrefs)
                    return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        cursor = self.cursorForPosition(event.position().toPoint())
        block = cursor.block()
        block_pos = block.position()
        text = block.text()
        match = re.match(r'^\[(x| )\] (.*)', text)
        if match:
            checked = match.group(1) == "x"
            content = match.group(2)
            new_line = f"[ ] {content}" if checked else f"[x] {content}"
            cursor.setPosition(block_pos)
            cursor.movePosition(
                QtGui.QTextCursor.MoveOperation.EndOfBlock,
                QtGui.QTextCursor.MoveMode.KeepAnchor
            )
            cursor.insertText(new_line)
            fmt = QtGui.QTextCharFormat()
            cursor.setPosition(block_pos)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock, QtGui.QTextCursor.MoveMode.KeepAnchor)
            if not checked:
                fmt.setFontStrikeOut(True)
            else:
                fmt.setFontStrikeOut(False)
            cursor.setCharFormat(fmt)
            return
        

        super().mouseDoubleClickEvent(event)





def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    editor = DesktopTextBoard()
    tray = TrayManager(editor, parent=editor)
    editor.setWindowTitle("Desktop TextBoard")
    editor.show()
    app.setApplicationName("Desktop TextBoard")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("TextBoard")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

