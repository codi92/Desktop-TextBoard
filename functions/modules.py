from PyQt6 import QtCore, QtGui, QtWidgets
from functions.wallpaper_color import get_desktop_base_color, windows_is_dark_mode
import ctypes
class FindReplaceDialog(QtWidgets.QDialog):
    def __init__(self, parent, editor=None, mode="search"):
        super().__init__(parent)
        self._style_timer = QtCore.QTimer(self)
        self._style_timer.timeout.connect(self.update_style)
        self._style_timer.start(3000)

        resolved_editor = None
        if editor and hasattr(editor, "document") and callable(getattr(editor, "document")):
            resolved_editor = editor
        else:
            for attr_name in ['editor', '_editor', 'text_editor', 'textEdit']:
                candidate = getattr(parent, attr_name, None)
                if candidate and hasattr(candidate, "document") and callable(getattr(candidate, "document")):
                    resolved_editor = candidate
                    break
        if not resolved_editor and hasattr(parent, "document") and callable(getattr(parent, "document")):
            resolved_editor = parent
        if not resolved_editor:
            raise AttributeError("Could not resolve a valid editor with 'document()' method.")
        self.editor = resolved_editor
        self.mode = mode

        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self.setModal(False)
        self.setFixedSize(250, 40 if mode == "search" else 80)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setHorizontalSpacing(1)
        layout.setVerticalSpacing(1)

        self.search_btn = QtWidgets.QPushButton(self)
        self.search_btn.setIcon(QtGui.QIcon.fromTheme("edit-find"))
        self.search_btn.setToolTip("Search")
        self.search_btn.setFixedSize(24, 24)
        self.search_btn.clicked.connect(lambda: self.find_next(backward=False))
        layout.addWidget(self.search_btn, 0, 0)

        self.input_find = QtWidgets.QLineEdit(self)
        self.input_find.setPlaceholderText("Find…")
        self.input_find.returnPressed.connect(self._handle_return)
        layout.addWidget(self.input_find, 0, 1)

        self.opacity_effect_find = QtWidgets.QGraphicsOpacityEffect(self.input_find)
        self.opacity_effect_find.setOpacity(0.5)
        self.input_find.setGraphicsEffect(self.opacity_effect_find)
        self.input_find.installEventFilter(self)

        self.count_label = QtWidgets.QLabel(self)

        self.count_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.count_label, 0, 2)
        self.opacity_effect_replace = QtWidgets.QGraphicsOpacityEffect(self.count_label)
        self.opacity_effect_replace.setOpacity(0.5)
        self.count_label.setGraphicsEffect(self.opacity_effect_replace)
        self.count_label.installEventFilter(self)


        self.close_btn = QtWidgets.QPushButton(self)
        self.close_btn.setIcon(QtGui.QIcon.fromTheme("window-close"))
        self.close_btn.setToolTip("Close")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn, 0, 3)

        if self.mode == "replace":
            self.replace_this_btn = QtWidgets.QPushButton(self)
            self.replace_this_btn.setIcon(QtGui.QIcon.fromTheme("go-next"))
            self.replace_this_btn.setToolTip("Replace This")
            self.replace_this_btn.setFixedSize(24, 24)
            self.replace_this_btn.clicked.connect(lambda: self.replace_one(find_next=True))
            layout.addWidget(self.replace_this_btn, 1, 0)

            self.input_replace = QtWidgets.QLineEdit(self)
            self.input_replace.setPlaceholderText("Replace…")
            layout.addWidget(self.input_replace, 1, 1)

            self.opacity_effect_replace = QtWidgets.QGraphicsOpacityEffect(self.input_replace)
            self.opacity_effect_replace.setOpacity(0.5)
            self.input_replace.setGraphicsEffect(self.opacity_effect_replace)
            self.input_replace.installEventFilter(self)

            self.replace_all_btn = QtWidgets.QPushButton(self)
            self.replace_all_btn.setIcon(
                QtGui.QIcon.fromTheme("replace-all", QtGui.QIcon.fromTheme("edit-select-all"))
            )
            self.replace_all_btn.setToolTip("Replace All")
            self.replace_all_btn.setFixedSize(24, 24)
            self.replace_all_btn.clicked.connect(self.replace_all)
            layout.addWidget(self.replace_all_btn, 1, 3)

        self._restore_focus_widget = None
        self.finished.connect(self._on_dialog_closed)
        self.input_find.textChanged.connect(lambda: self.find_next(backward=False))
        self.input_find.textChanged.connect(self._persist_find_text)

        if self.mode == "replace":
            self.input_replace.textChanged.connect(self._persist_replace_text)

        if hasattr(self.editor, "_last_search"):
            self.input_find.setText(self.editor._last_search)
        if self.mode == "replace" and hasattr(self.editor, "_last_replace_replace"):
            self.input_replace.setText(self.editor._last_replace_replace)

    def _persist_find_text(self):
        if hasattr(self.editor, "_last_search"):
            self.editor._last_search = self.input_find.text()
        if hasattr(self.editor, "save_config"):
            self.editor.save_config()

    def _persist_replace_text(self):
        if hasattr(self.editor, "_last_replace_replace"):
            self.editor._last_replace_replace = self.input_replace.text()
        if hasattr(self.editor, "save_config"):
            self.editor.save_config()

    def _handle_return(self):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        self.find_next(backward=modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier)

    def keyPressEvent(self, event):
        k = event.key()
        m = event.modifiers()
        if k in (QtCore.Qt.Key.Key_F3, QtCore.Qt.Key.Key_F):
            self.find_next(backward=m & QtCore.Qt.KeyboardModifier.ShiftModifier)
            return
        if (
            self.mode == "replace"
            and m == QtCore.Qt.KeyboardModifier.AltModifier
            and k in (QtCore.Qt.Key.Key_F, QtCore.Qt.Key.Key_H)
        ):
            self.replace_one(find_next=True)
            return
        super().keyPressEvent(event)

    def update_count_label(self, current=0, total=0):
        self.count_label.setText(f"{current} / {total}" if total > 0 else "0 / 0")

    def find_next(self, backward=False):
        query = self.input_find.text()
        if not query:
            self.update_count_label(0, 0)
            return
        doc = self.editor.document()
        cursor = self.editor.textCursor()
        is_current = cursor.selectedText() == query
        start_pos = (
            cursor.selectionStart()
            if backward and is_current
            else (
                cursor.selectionEnd()
                if not backward and is_current
                else cursor.position()
            )
        )
        flags = (
            QtGui.QTextDocument.FindFlag.FindBackward
            if backward
            else QtGui.QTextDocument.FindFlag(0)
        )
        found = doc.find(query, start_pos, flags)
        if found.isNull():
            cursor.movePosition(
                QtGui.QTextCursor.MoveOperation.End
                if backward
                else QtGui.QTextCursor.MoveOperation.Start
            )
            found = doc.find(query, cursor, flags)
        if not found.isNull():
            self.editor.setTextCursor(found)
            self.editor.ensureCursorVisible()
        all_matches = []
        match_cursor = doc.find(query, 0)
        while not match_cursor.isNull():
            all_matches.append(match_cursor.selectionStart())
            match_cursor = doc.find(query, match_cursor.selectionEnd())
        cur_pos = self.editor.textCursor().selectionStart()
        current = all_matches.index(cur_pos) + 1 if cur_pos in all_matches else 1
        self.update_count_label(current, len(all_matches))

    def replace_one(self, find_next=False):
        if self.input_find.text() == self.editor.textCursor().selectedText():
            self.editor.textCursor().insertText(self.input_replace.text())
        if find_next:
            self.find_next(backward=False)

    def replace_all(self):
        query = self.input_find.text()
        if not query:
            self.update_count_label(0, 0)
            return

        replace_text = self.input_replace.text()
        doc = self.editor.document()

        cursor = QtGui.QTextCursor(doc)
        cursor.beginEditBlock()

        count = 0
        while True:
            found = doc.find(query, cursor)
            if found.isNull():
                break
            found.beginEditBlock()
            found.removeSelectedText()
            found.insertText(replace_text)
            found.endEditBlock()
            cursor.setPosition(found.position())  # move after the inserted text
            count += 1

        cursor.endEditBlock()
        self.find_next()
        self.update_count_label(count, count)


    def set_query(self, text):
        self.input_find.setText(text)
        self.input_find.selectAll()
        QtCore.QTimer.singleShot(0, self.find_next)

    def focus_input(self):
        QtCore.QTimer.singleShot(0, lambda: (self.input_find.setFocus(), self.input_find.selectAll()))

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            # Получаем позицию родителя относительно экрана
            top_left_global = self.parent().mapToGlobal(QtCore.QPoint(0, 0))
            # Перемещаем диалог справа сверху родителя
            self.move(top_left_global.x() + self.parent().width() - self.width(), top_left_global.y() + 5)
        self._restore_focus_widget = self.editor
        self.update_style()
        self.focus_input()

    def closeEvent(self, event):
        if hasattr(self.editor, "_last_search"):
            self.editor._last_search = self.input_find.text()
        if self.mode == "replace" and hasattr(self.editor, "_last_replace_replace"):
            self.editor._last_replace_replace = self.input_replace.text()
        if hasattr(self.editor, "save_config"):
            self.editor.save_config()
        super().closeEvent(event)
        if self._restore_focus_widget:
            QtCore.QTimer.singleShot(0, self._restore_focus_widget.setFocus)

    def _on_dialog_closed(self, result):
        if self._restore_focus_widget:
            QtCore.QTimer.singleShot(0, self._restore_focus_widget.setFocus)

    def update_style(self):
        desktop_color = get_desktop_base_color()
        is_dark_mode = windows_is_dark_mode()
        red = desktop_color.red()
        green = desktop_color.green()
        blue = desktop_color.blue()

        new_style_key = (red, green, blue, is_dark_mode)
        if getattr(self, "_last_style_key", None) == new_style_key:
            return
        self._last_style_key = new_style_key

        if is_dark_mode:
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            border_color = "rgba(255, 255, 255, 0.2)"
            self.setStyleSheet(f"""
                QDialog {{
                    background: rgba({red}, {green}, {blue}, 0.88);
                    border-radius: 6px;
                    border: 1px solid {border_color};
                }}

                QLineEdit {{
                    background: #222;
                    color: #fff;
                    border: none;
                    padding: 4px 8px;
                    min-width: 120px;
                }}
                QPushButton {{
                    background: transparent;
                    border: none;
                    min-width: 24px;
                    min-height: 24px;
                }}
                QPushButton:hover {{
                    background-color: #444;
                    border-radius: 4px;
                }}
                QtWidgets.QLabel{{
                    color: rgba(255, 255, 255, 0.8);
                    min-width: 48px;
                }}
                QtWidgets.QLabel:hover {{
                    color: rgba(255, 255, 255, 1.0);
                    min-width: 48px;
                }}

            """)
        else:
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)
            border_color = "rgba(0, 0, 0, 0.2)"
            self.setStyleSheet(f"""
                QDialog {{
                    background: rgb(255, 255, 255);
                    border-radius: 6px;
                    border: 1px solid {border_color};
                }}
                QLineEdit {{
                    background: #fff;
                    color: #000;
                    border: 1px solid #ccc;
                    padding: 4px 8px;
                    min-width: 120px;
                }}
                QPushButton {{
                    background: transparent;
                    border: none;
                    min-width: 24px;
                    min-height: 24px;
                }}
                QPushButton:hover {{
                    background-color: #ddd;
                    border-radius: 4px;
                }}
                QtWidgets.QLabel{{
                    color: rgba(255, 255, 255, 0.8);
                    min-width: 48px;
                }}
                QtWidgets.QLabel:hover {{
                    color: rgba(0, 0, 0, 0.8);
                    min-width: 48px;
                }}
            """)


    def eventFilter(self, obj, event):
        if obj == self.input_find and hasattr(self, "opacity_effect_find"):
            if event.type() == QtCore.QEvent.Type.Enter:
                self.opacity_effect_find.setOpacity(1.0)
            elif event.type() == QtCore.QEvent.Type.Leave:
                self.opacity_effect_find.setOpacity(0.5)
        if self.mode == "replace" and obj == self.input_replace and hasattr(self, "opacity_effect_replace"):
            if event.type() == QtCore.QEvent.Type.Enter:
                self.opacity_effect_replace.setOpacity(1.0)
            elif event.type() == QtCore.QEvent.Type.Leave:
                self.opacity_effect_replace.setOpacity(0.5)
        if obj == self.count_label and hasattr(self, "opacity_effect_replace"):
            if event.type() == QtCore.QEvent.Type.Enter:
                self.opacity_effect_replace.setOpacity(1.0)
            elif event.type() == QtCore.QEvent.Type.Leave:
                self.opacity_effect_replace.setOpacity(0.5)
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if obj == self.input_find or obj == self.input_replace:
                QtCore.QTimer.singleShot(0, lambda: (obj.setFocus(), obj.selectAll()))
        if event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            if obj == self.close_btn:
                self.close()
            elif obj == self.search_btn:
                self.find_next(backward=False)
            elif self.mode == "replace" and obj == self.replace_this_btn:
                self.replace_one(find_next=True)
            elif self.mode == "replace" and obj == self.replace_all_btn:
                self.replace_all()
        return super().eventFilter(obj, event)


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
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.green, 4))
        painter.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.darkGreen))
        painter.drawRect(4, 4, 24, 24)
        if show_red_dot:
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.red))
            painter.drawEllipse(11, 11, 10, 10)
        painter.end()
        self.setIcon(QtGui.QIcon(pixmap))
        if self.editor.show_raw:
            gray_pixmap = pixmap.toImage().convertToFormat(
                QtGui.QImage.Format.Format_ARGB32
            )
            for x in range(gray_pixmap.width()):
                for y in range(gray_pixmap.height()):
                    color = gray_pixmap.pixelColor(x, y)
                    gray_color = QtGui.QColor(
                        color.red() // 2, color.green() // 2, color.blue() // 2
                    )
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
        self.clipboard_action = menu.addAction(self.get_clipboard_action_label())
        self.clipboard_action.setCheckable(True)
        self.clipboard_action.setChecked(self.editor.is_clipboard_catch_enabled())
        self.clipboard_action.triggered.connect(self.toggle_clipboard_catch)
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
        if ctypes.windll.user32.GetAsyncKeyState(0x02):
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
        return (
            "Disable Clipboard Catch"
            if self.editor.is_clipboard_catch_enabled()
            else "Enable Clipboard Catch"
        )
    
class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent, current_font, current_history_file):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        layout = QtWidgets.QFormLayout(self)
        self.font_button = QtWidgets.QPushButton("Choose Font")
        self.font_label = QtWidgets.QLabel(
            current_font.family() + ", " + str(current_font.pointSize())
        )
        self.font = QtGui.QFont(current_font)
        self.font_button.clicked.connect(self.choose_font)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        font_layout = QtWidgets.QHBoxLayout()
        font_layout.addWidget(self.font_button)
        font_layout.addWidget(self.font_label)
        layout.addRow("Default Font:", font_layout)
        self.disable_transparency_checkbox = QtWidgets.QCheckBox("Disable Transparency")
        self.disable_transparency_checkbox.setChecked(
            getattr(parent, "disable_transparency", False)
        )
        layout.addRow("Disable Transparency:", self.disable_transparency_checkbox)
        self.path_edit = QtWidgets.QLineEdit(current_history_file)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.browse_button.clicked.connect(self.choose_file)
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)
        layout.addRow("Save File Location:", path_layout)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
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
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Choose Save File",
            self.path_edit.text(),
            "JSON Files (*.json);;All Files (*)",
        )
        if path:
            self.path_edit.setText(path)

    def accept(self):
        parent = self.parent()
        if parent is not None:
            parent.disable_transparency = self.disable_transparency_checkbox.isChecked()
            parent.update_opacity()
        super().accept()
