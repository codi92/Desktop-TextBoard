from PyQt6 import QtWidgets, QtGui, QtCore
from functions.wallpaper_color import get_desktop_base_color, windows_is_dark_mode

def show_rich_context_menu(parent, event):
    menu = QtWidgets.QMenu(parent)
    desktop_color = get_desktop_base_color()
    is_dark = windows_is_dark_mode()
    border_color = desktop_color.darker(150) if is_dark else desktop_color.lighter(150)
    font_color = QtGui.QColor(220, 220, 220) if is_dark else QtGui.QColor(30, 30, 30)
    def blend(color1, color2, ratio):
        return QtGui.QColor(
            int(color1.red() * (1 - ratio) + color2.red() * ratio),
            int(color1.green() * (1 - ratio) + color2.green() * ratio),
            int(color1.blue() * (1 - ratio) + color2.blue() * ratio),
        )
    accent_hover = blend(desktop_color, QtGui.QColor(255,255,255) if is_dark else QtGui.QColor(0,0,0), 0.18)
    accent_hover_text = QtGui.QColor(30,30,30) if is_dark else QtGui.QColor(240,240,240)
    menu.setStyleSheet(f'''
        QMenu {{
            background: {desktop_color.name()};
            color: {font_color.name()};
            border: 1.5px solid {border_color.name()};
        }}
        QMenu::item:selected {{
            background: {accent_hover.name()};
            color: {accent_hover_text.name()};
        }}
        QMenu::separator {{
            height: 1px;
            background: {border_color.name()};
            margin: 4px 0 4px 0;
        }}
    ''')

    cursor = parent.textCursor()
    has_selection = cursor.hasSelection()

    # Group 1: Font actions (only if selection and not in raw mode)
    show_raw = getattr(parent, 'show_raw', False)
    if has_selection and not show_raw:
        font_action = menu.addAction("Change Font…")
        font_action.triggered.connect(lambda: change_font(parent))
        size_menu = menu.addMenu("Font Size")
        for size in [10, 12, 14, 16, 18, 20, 24, 28, 32]:
            size_action = size_menu.addAction(f"{size} pt")
            size_action.triggered.connect(lambda checked, s=size: set_font_size(parent, s))
        color_action = menu.addAction("Text Color…")
        color_action.triggered.connect(lambda: change_color(parent))
        highlight_action = menu.addAction("Highlight…")
        highlight_action.triggered.connect(lambda: change_highlight(parent))
        menu.addSeparator()

    # Group 2: Raw mode (always shown)
    raw_mode_action = menu.addAction("Toggle Raw Mode")
    raw_mode_action.setCheckable(True)
    raw_mode_action.setChecked(show_raw)
    def toggle_raw_mode():
        new_raw = not getattr(parent, 'show_raw', False)
        if hasattr(parent, 'set_show_raw'):
            parent.set_show_raw(new_raw)
        else:
            setattr(parent, 'show_raw', new_raw)
        update_tray_state(parent)
        # Also update right-click menu immediately for sync
        show_rich_context_menu(parent, event)
    raw_mode_action.triggered.connect(toggle_raw_mode)
    if show_raw:
        raw_mode_action.setText("Disable Raw Mode")
    else:
        raw_mode_action.setText("Enable Raw Mode")
    menu.addSeparator()

    # Group 3: Clipboard actions and catcher
    copy_action = menu.addAction("Copy")
    copy_action.setEnabled(has_selection)
    copy_action.triggered.connect(parent.copy)
    cut_action = menu.addAction("Cut")
    cut_action.setEnabled(has_selection)
    cut_action.triggered.connect(parent.cut)
    paste_action = menu.addAction("Paste")
    paste_action.triggered.connect(parent.paste)
    # Clipboard catcher toggle
    def tray_update():
        tray = getattr(parent, 'tray', None)
        if tray:
            if hasattr(tray, 'clipboard_action') and hasattr(tray, 'get_clipboard_action_label'):
                tray.clipboard_action.setText(tray.get_clipboard_action_label())
                tray.clipboard_action.setChecked(parent.is_clipboard_catch_enabled())
            if hasattr(tray, 'update_icon'):
                tray.update_icon()
            if hasattr(tray, 'show_raw_action'):
                tray.show_raw_action.setChecked(getattr(parent, 'show_raw', False))
    if hasattr(parent, 'is_clipboard_catch_enabled') and hasattr(parent, 'set_clipboard_catch'):
        if parent.is_clipboard_catch_enabled():
            cc_action = menu.addAction("Disable Clipboard Catch")
            def disable_cc():
                parent.set_clipboard_catch(False)
                tray_update()
                show_rich_context_menu(parent, event)
            cc_action.triggered.connect(disable_cc)
        else:
            cc_action = menu.addAction("Enable Clipboard Catch")
            def enable_cc():
                parent.set_clipboard_catch(True)
                tray_update()
                show_rich_context_menu(parent, event)
            cc_action.triggered.connect(enable_cc)

    menu.exec(event.globalPos())

def change_font(parent):
    cursor = parent.textCursor()
    if not cursor.hasSelection():
        return
    font, ok = QtWidgets.QFontDialog.getFont(parent.font(), parent)
    if ok:
        fmt = QtGui.QTextCharFormat()
        fmt.setFont(font)
        cursor.mergeCharFormat(fmt)

def set_font_size(parent, size):
    cursor = parent.textCursor()
    if not cursor.hasSelection():
        return
    fmt = QtGui.QTextCharFormat()
    fmt.setFontPointSize(size)
    cursor.mergeCharFormat(fmt)

def change_color(parent):
    cursor = parent.textCursor()
    if not cursor.hasSelection():
        return
    color = QtWidgets.QColorDialog.getColor(parent.palette().color(QtGui.QPalette.ColorRole.Text), parent)
    if color.isValid():
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QBrush(color))
        cursor.mergeCharFormat(fmt)

def change_highlight(parent):
    cursor = parent.textCursor()
    if not cursor.hasSelection():
        return
    color = QtWidgets.QColorDialog.getColor(parent.palette().color(QtGui.QPalette.ColorRole.Highlight), parent)
    if color.isValid():
        fmt = QtGui.QTextCharFormat()
        fmt.setBackground(QtGui.QBrush(color))
        cursor.mergeCharFormat(fmt)

def start_clipboard_catcher(parent, callback):
    """
    Starts a clipboard catcher that calls `callback(text)` whenever the clipboard text changes.
    `parent` should be a QWidget or QApplication instance.
    `callback` is a function that takes a single string argument (the clipboard text).
    """
    clipboard = QtWidgets.QApplication.clipboard()
    def on_clipboard_change():
        text = clipboard.text()
        callback(text)
    clipboard.dataChanged.connect(on_clipboard_change)

def update_tray_state(parent):
    tray = getattr(parent, 'tray', None)
    if tray:
        if hasattr(tray, 'clipboard_action') and hasattr(tray, 'get_clipboard_action_label'):
            tray.clipboard_action.setText(tray.get_clipboard_action_label())
            tray.clipboard_action.setChecked(parent.is_clipboard_catch_enabled())
        if hasattr(tray, 'show_raw_action'):
            tray.show_raw_action.setChecked(getattr(parent, 'show_raw', False))
        if hasattr(tray, 'update_icon'):
            tray.update_icon()