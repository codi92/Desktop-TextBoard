import sys
import os
import json
from datetime import datetime
from PyQt6 import QtWidgets, QtCore, QtGui
import base64

def get_config_path():
    home = os.path.expanduser("~")
    return os.path.join(home, ".config_desktop_textboard.json")

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent, current_font, current_history_file):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        layout = QtWidgets.QFormLayout(self)

        # Font selector
        self.font_button = QtWidgets.QPushButton("Choose Font")
        self.font_label = QtWidgets.QLabel(current_font.family() + ", " + str(current_font.pointSize()))
        self.font = QtGui.QFont(current_font)
        self.font_button.clicked.connect(self.choose_font)
        font_layout = QtWidgets.QHBoxLayout()
        font_layout.addWidget(self.font_button)
        font_layout.addWidget(self.font_label)
        layout.addRow("Default Font:", font_layout)

        # Save file location
        self.path_edit = QtWidgets.QLineEdit(current_history_file)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.browse_button.clicked.connect(self.choose_file)
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)
        layout.addRow("Save File Location:", path_layout)

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

    def choose_font(self):
        font, ok = QtWidgets.QFontDialog.getFont(self.font, self)
        if ok:
            self.font = font
            self.font_label.setText(font.family() + ", " + str(font.pointSize()))

    def choose_file(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Choose Save File", self.path_edit.text(), "JSON Files (*.json);;All Files (*)")
        if path:
            self.path_edit.setText(path)

class DesktopTextBoard(QtWidgets.QTextEdit):
    def __init__(self):
        super().__init__()
        self.history_file = "textboard_history.json"
        self.auto_save_timer = None

        self.setup_ui()
        self.load_config()
        self.load_file()
        self.setup_auto_save()

    def setup_ui(self):
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnBottomHint |
            QtCore.Qt.WindowType.Tool
        )
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        self.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 15px;
                padding: 12px;
                border: 1.5px solid #333;
                selection-background-color: #264f78;
                selection-color: #fff;
            }
        """)
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        width = screen.width() // 2
        height = screen.height()
        x = screen.width() - width
        y = 0
        self.setGeometry(x, y, width, height)
        self.setWindowOpacity(1.0)
        self.setWindowTitle("Desktop TextBoard")

    def load_config(self):
        config_path = get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                font = QtGui.QFont()
                font.fromString(config.get("font", "Consolas,15,-1,5,50,0,0,0,0,0"))
                self.setFont(font)
                self.history_file = config.get("history_file", self.history_file)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self, font=None, history_file=None):
        config_path = get_config_path()
        config = {
            "font": (font or self.font()).toString(),
            "history_file": history_file or self.history_file
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def setup_auto_save(self):
        self.auto_save_timer = QtCore.QTimer()
        self.auto_save_timer.timeout.connect(self.save_file)
        self.auto_save_timer.start(3000)
        self.textChanged.connect(self.save_file)

    def load_file(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.setHtml(data.get('text', ''))
            except Exception as e:
                print(f"Error loading file: {e}")

    def save_file(self):
        try:
            data = {
                'text': self.toHtml(),
                'last_updated': datetime.now().isoformat(),
                'app_version': '2.0'
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving file: {e}")

    def clear(self):
        self.setPlainText("")
        self.save_file()

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
        elif modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def zoom_in(self):
        font = self.font()
        size = font.pointSize()
        if size <= 0:
            size = 12
        if size < 48:
            font.setPointSize(size + 1)
            self.setFont(font)
            self.document().setDefaultFont(font)

    def zoom_out(self):
        font = self.font()
        size = font.pointSize()
        if size <= 0:
            size = 12
        if size > 6:
            font.setPointSize(size - 1)
            self.setFont(font)
            self.document().setDefaultFont(font)

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
            print(f"Error loading history: {e}")
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
            print(f"Error saving history: {e}")

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()
        # Scale image if selection is on image and + or - is pressed (no Ctrl)
        if modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
            cursor = self.textCursor()
            char_format = cursor.charFormat()
            if char_format.isImageFormat():
                if key in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal):
                    # Remove or replace with right-click scaling
                    return
                elif key == QtCore.Qt.Key.Key_Minus:
                    # Remove or replace with right-click scaling
                    return
        # Font scaling (entire document) with Ctrl
        if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
            if key == QtCore.Qt.Key.Key_Z:
                super().undo()
                return
            elif key == QtCore.Qt.Key.Key_Y:
                super().redo()
                return
            elif key == QtCore.Qt.Key.Key_S:
                self.save_file()
                return
            elif key == QtCore.Qt.Key.Key_N:
                self.clear()
                return
            elif key in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal):
                self.zoom_in()
                return
            elif key == QtCore.Qt.Key.Key_Minus:
                self.zoom_out()
                return
        elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
            if key == QtCore.Qt.Key.Key_F4:
                self.close()
                return
        super().keyPressEvent(event)

    def scale_selected_image(self, scale_factor):
        cursor = self.textCursor()
        found = False

        # Try character under cursor
        temp_cursor = QtGui.QTextCursor(cursor)
        temp_cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right, QtGui.QTextCursor.MoveMode.KeepAnchor, 1)
        char_format = temp_cursor.charFormat()
        if char_format.isImageFormat():
            found = True
        else:
            # Try character to the left
            temp_cursor = QtGui.QTextCursor(cursor)
            temp_cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left, QtGui.QTextCursor.MoveMode.MoveAnchor, 1)
            temp_cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right, QtGui.QTextCursor.MoveMode.KeepAnchor, 1)
            char_format = temp_cursor.charFormat()
            if char_format.isImageFormat():
                found = True
            else:
                # Try character to the right
                temp_cursor = QtGui.QTextCursor(cursor)
                temp_cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right, QtGui.QTextCursor.MoveMode.MoveAnchor, 1)
                temp_cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right, QtGui.QTextCursor.MoveMode.KeepAnchor, 1)
                char_format = temp_cursor.charFormat()
                if char_format.isImageFormat():
                    found = True

        if found:
            img_format = char_format.toImageFormat()
            img_name = img_format.name()
            doc_resource = self.document().resource(
                QtGui.QTextDocument.ResourceType.ImageResource, QtCore.QUrl(img_name)
            )
            if isinstance(doc_resource, QtGui.QImage):
                orig_width = doc_resource.width()
                orig_height = doc_resource.height()
                current_width = img_format.width() if img_format.width() > 0 else orig_width
                aspect_ratio = orig_height / orig_width if orig_width else 1
                new_width = max(8, current_width * scale_factor)
                new_height = max(8, new_width * aspect_ratio)
                img_format.setWidth(new_width)
                img_format.setHeight(new_height)
                temp_cursor.insertImage(img_format)
        else:
            QtWidgets.QMessageBox.warning(self, "No image", "Please place the cursor on or next to an image to scale it.")

    def insertFromMimeData(self, source: QtCore.QMimeData):
        if source.hasImage():
            image = QtGui.QImage(source.imageData())
            if not image.isNull():
                buffer = QtCore.QBuffer()
                buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
                image.save(buffer, "PNG")
                base64_data = base64.b64encode(buffer.data()).decode("utf-8")
                html = f'<img src="data:image/png;base64,{base64_data}">'
                self.textCursor().insertHtml(html)
                return
        super().insertFromMimeData(source)

    def clear(self):
        self.setPlainText("")

    def closeEvent(self, event):
        self.save_file()
        self.save_config()
        if self.auto_save_timer:
            self.auto_save_timer.stop()
        super().closeEvent(event)

    def contextMenuEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        # Try to select the image under the mouse
        temp_cursor = QtGui.QTextCursor(cursor)
        temp_cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right, QtGui.QTextCursor.MoveMode.KeepAnchor, 1)
        char_format = temp_cursor.charFormat()
        if char_format.isImageFormat():
            menu = QtWidgets.QMenu(self)
            scale_action = menu.addAction("Change Image Size…")
            action = menu.exec(event.globalPos())
            if action == scale_action:
                img_format = char_format.toImageFormat()
                img_name = img_format.name()
                doc_resource = self.document().resource(
                    QtGui.QTextDocument.ResourceType.ImageResource, QtCore.QUrl(img_name)
                )
                if isinstance(doc_resource, QtGui.QImage):
                    orig_width = doc_resource.width()
                    orig_height = doc_resource.height()
                    current_width = img_format.width() if img_format.width() > 0 else orig_width
                    current_height = img_format.height() if img_format.height() > 0 else orig_height
                    aspect_ratio = orig_height / orig_width if orig_width else 1

                    # Ask user for new width and height
                    dialog = QtWidgets.QDialog(self)
                    dialog.setWindowTitle("Change Image Size")
                    layout = QtWidgets.QFormLayout(dialog)
                    width_edit = QtWidgets.QLineEdit(str(int(current_width)))
                    height_edit = QtWidgets.QLineEdit(str(int(current_height)))
                    keep_aspect = QtWidgets.QCheckBox("Preserve aspect ratio")
                    keep_aspect.setChecked(True)
                    layout.addRow("Width (px):", width_edit)
                    layout.addRow("Height (px):", height_edit)
                    layout.addRow(keep_aspect)
                    buttons = QtWidgets.QDialogButtonBox(
                        QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
                    )
                    layout.addRow(buttons)
                    buttons.accepted.connect(dialog.accept)
                    buttons.rejected.connect(dialog.reject)
                    width_edit.textChanged.connect(
                        lambda: height_edit.setText(
                            str(int(float(width_edit.text()) * aspect_ratio)) if keep_aspect.isChecked() and width_edit.text().isdigit() else height_edit.text()
                        )
                    )
                    height_edit.textChanged.connect(
                        lambda: width_edit.setText(
                            str(int(float(height_edit.text()) / aspect_ratio)) if keep_aspect.isChecked() and height_edit.text().isdigit() else width_edit.text()
                        )
                    )
                    keep_aspect.stateChanged.connect(
                        lambda state: (
                            height_edit.setText(str(int(float(width_edit.text()) * aspect_ratio)))
                            if state and width_edit.text().isdigit() else None
                        )
                    )
                    if dialog.exec():
                        try:
                            new_width = int(width_edit.text())
                            new_height = int(height_edit.text())
                            if new_width < 8 or new_height < 8:
                                raise ValueError
                            img_format.setWidth(new_width)
                            img_format.setHeight(new_height)
                            temp_cursor.insertImage(img_format)
                        except Exception:
                            QtWidgets.QMessageBox.warning(self, "Invalid size", "Please enter valid positive integers for width and height.")
            return  # Don't show the default menu for images

        # Otherwise, show the normal context menu with text actions
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        font_action = menu.addAction("Change Font…")
        text_color_action = menu.addAction("Change Font Color…")
        bg_color_action = menu.addAction("Change Highlight/Background…")
        action = menu.exec(event.globalPos())
        cursor = self.textCursor()
        if action == font_action:
            font, ok = QtWidgets.QFontDialog.getFont(self.font(), self)
            if ok and cursor.hasSelection():
                fmt = QtGui.QTextCharFormat()
                fmt.setFont(font)
                cursor.mergeCharFormat(fmt)
        elif action == text_color_action:
            color = QtWidgets.QColorDialog.getColor(QtCore.Qt.GlobalColor.white, self, "Select Font Color")
            if color.isValid() and cursor.hasSelection():
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(QtGui.QBrush(color))
                cursor.mergeCharFormat(fmt)
        elif action == bg_color_action:
            color = QtWidgets.QColorDialog.getColor(QtCore.Qt.GlobalColor.yellow, self, "Select Highlight/Background Color")
            if color.isValid() and cursor.hasSelection():
                fmt = QtGui.QTextCharFormat()
                fmt.setBackground(QtGui.QBrush(color))
                cursor.mergeCharFormat(fmt)

class TrayManager(QtWidgets.QSystemTrayIcon):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.create_icon()
        self.create_menu()
        self.setup_signals()
        self.show()

    def create_icon(self):
        pixmap = QtGui.QPixmap(16, 16)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.green, 2))
        painter.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.darkGreen))
        painter.drawRect(2, 2, 12, 12)
        painter.end()
        self.setIcon(QtGui.QIcon(pixmap))

    def create_menu(self):
        menu = QtWidgets.QMenu()
        show_action = menu.addAction("📝 Show")
        show_action.triggered.connect(self.show_editor)
        hide_action = menu.addAction("🔽 Hide")
        hide_action.triggered.connect(self.hide_editor)
        menu.addSeparator()
        save_action = menu.addAction("💾 Save")
        save_action.triggered.connect(self.editor.save_file)
        clear_action = menu.addAction("🗑️ Clear")
        clear_action.triggered.connect(self.editor.clear)
        menu.addSeparator()
        settings_action = menu.addAction("⚙️ Settings")
        settings_action.triggered.connect(self.show_settings)
        menu.addSeparator()
        about_action = menu.addAction("ℹ️ About")
        about_action.triggered.connect(self.show_about)
        exit_action = menu.addAction("❌ Exit")
        exit_action.triggered.connect(self.exit_app)
        self.setContextMenu(menu)

    def setup_signals(self):
        self.activated.connect(self.on_tray_activated)

    def show_editor(self):
        self.editor.show()
        self.editor.raise_()
        self.editor.activateWindow()

    def hide_editor(self):
        self.editor.hide()

    def show_settings(self):
        dlg = SettingsDialog(self.editor, self.editor.font(), self.editor.history_file)
        if dlg.exec():
            self.editor.setFont(dlg.font)
            self.editor.history_file = dlg.path_edit.text()
            self.editor.save_config(font=dlg.font, history_file=dlg.path_edit.text())

    def on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.editor.isVisible():
                self.hide_editor()
            else:
                self.show_editor()

    def show_about(self):
        QtWidgets.QMessageBox.about(
            None,
            "Desktop TextBoard",
            """<h3>Desktop TextBoard v2.0</h3>
            <p>A floating desktop text editor with history tracking.</p>
            <p><b>Features:</b></p>
            <ul>
            <li>Auto-save with history</li>
            <li>Undo/Redo (Ctrl+Z/Y)</li>
            <li>Horizontal scroll (Shift+Wheel)</li>
            <li>Zoom (Ctrl+Wheel or Ctrl++/=/-)</li>
            <li>Image paste and scaling (+/-)</li>
            <li>System tray integration</li>
            <li>Settings for font and save file</li>
            </ul>
            <p><b>Shortcuts:</b></p>
            <ul>
            <li>Ctrl+Z: Undo</li>
            <li>Ctrl+Y: Redo</li>
            <li>Ctrl+S: Save</li>
            <li>Ctrl+N: Clear</li>
            <li>Ctrl+Plus/Equal/Minus: Zoom</li>
            <li>+/- on image: Scale image</li>
            </ul>"""
        )

    def exit_app(self):
        self.editor.save_file()
        self.editor.save_config()
        QtWidgets.QApplication.quit()

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
