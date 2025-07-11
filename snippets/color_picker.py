# color_picker.py: Minimal color picker dialog for Desktop TextBoard (PyQt6)
#
# Usage:
#   Run this file directly to launch the color picker dialog as a standalone tool.
#
# Features:
#   - Triangle-based RGB picker (corners: red, green, blue; center: white)
#   - SV (saturation-value) square for fine-tuning color
#   - Real-time editable RGB and Hue fields (two-way sync)
#   - All UI elements update instantly and stay in sync
#   - Outputs HTML color preview and hex code for use in the app
#
# Example: ~color_picker.py
#
# Parameters (when embedding):
#   None (interactive dialog)


import sys
import os
from PyQt6 import QtWidgets, QtGui, QtCore

# --- Helper functions ---
def clamp(val, mn, mx):
    return max(mn, min(mx, val))

def rgb_to_hsv(r, g, b):
    color = QtGui.QColor(int(r*255), int(g*255), int(b*255))
    return color.getHsvF()[:3]

def hsv_to_rgb(h, s, v):
    color = QtGui.QColor()
    color.setHsvF(h, s, v)
    r, g, b, _ = color.getRgb()
    return r/255.0, g/255.0, b/255.0

class ColorSquare(QtWidgets.QWidget):
    colorChanged = QtCore.pyqtSignal(float, float)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.hue = 0.0
        self.sat = 1.0
        self.val = 1.0
        self.selected_pos = QtCore.QPoint(self.width()-1, 0)
        self.selector_color = QtGui.QColor(255,255,255)
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        w, h = self.width(), self.height()
        for y in range(h):
            v = 1.0 - y / (h - 1)
            for x in range(w):
                s = x / (w - 1)
                color = QtGui.QColor()
                color.setHsvF(self.hue, s, v)
                painter.setPen(color)
                painter.drawPoint(x, y)
        painter.setPen(QtGui.QPen(QtGui.QColor(0,0,0), 2))
        painter.setBrush(QtGui.QBrush(self.selector_color))
        painter.drawEllipse(self.selected_pos, 8, 8)
    def mousePressEvent(self, event):
        self.set_color_from_pos(event.pos())
    def mouseMoveEvent(self, event):
        self.set_color_from_pos(event.pos())
    def set_color_from_pos(self, pos):
        w, h = self.width(), self.height()
        x = clamp(pos.x(), 0, w-1)
        y = clamp(pos.y(), 0, h-1)
        s = x / (w - 1)
        v = 1.0 - y / (h - 1)
        self.sat, self.val = s, v
        self.selected_pos = QtCore.QPoint(x, y)
        self.selector_color = QtGui.QColor(); self.selector_color.setHsvF(self.hue, s, v)
        self.colorChanged.emit(s, v)
        self.update()
    def set_selector(self, hue, sat, val):
        self.hue, self.sat, self.val = hue, sat, val
        w, h = self.width(), self.height()
        x = int(sat * (w - 1))
        y = int((1.0 - val) * (h - 1))
        self.selected_pos = QtCore.QPoint(x, y)
        self.selector_color = QtGui.QColor(); self.selector_color.setHsvF(hue, sat, val)
        self.update()

class ColorTriangle(QtWidgets.QWidget):
    colorChanged = QtCore.pyqtSignal(float, float, float)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 180)
        self.triangle = self._triangle_points()
        self.selector_bary = (1/3, 1/3, 1/3)
        self.selector_color = QtGui.QColor(255,255,255)
    def _triangle_points(self):
        w, h = self.width(), self.height()
        return [QtCore.QPointF(w/2, 10), QtCore.QPointF(10, h-10), QtCore.QPointF(w-10, h-10)]
    def _barycentric(self, pt):
        a, b, c = self.triangle
        v0 = QtCore.QPointF(b.x()-a.x(), b.y()-a.y())
        v1 = QtCore.QPointF(c.x()-a.x(), c.y()-a.y())
        v2 = QtCore.QPointF(pt.x()-a.x(), pt.y()-a.y())
        d00 = v0.x()*v0.x() + v0.y()*v0.y()
        d01 = v0.x()*v1.x() + v0.y()*v1.y()
        d11 = v1.x()*v1.x() + v1.y()*v1.y()
        d20 = v2.x()*v0.x() + v2.y()*v0.y()
        d21 = v2.x()*v1.x() + v2.y()*v1.y()
        denom = d00 * d11 - d01 * d01
        if denom == 0: return (1/3, 1/3, 1/3)
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w
        return (u, v, w)
    def _from_bary(self, bary):
        a, b, c = self.triangle
        u, v, w = bary
        return QtCore.QPointF(u*a.x() + v*b.x() + w*c.x(), u*a.y() + v*b.y() + w*c.y())
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        img = QtGui.QImage(self.width(), self.height(), QtGui.QImage.Format.Format_RGB32)
        for y in range(self.height()):
            for x in range(self.width()):
                bary = self._barycentric(QtCore.QPointF(x, y))
                u, v, w = bary
                if min(u, v, w) >= 0 and max(u, v, w) <= 1:
                    r, g, b = u, v, w
                    img.setPixelColor(x, y, QtGui.QColor(int(r*255), int(g*255), int(b*255)))
                else:
                    img.setPixelColor(x, y, QtGui.QColor(0,0,0,0))
        painter.drawImage(0, 0, img)
        painter.setPen(QtGui.QPen(QtGui.QColor(0,0,0), 2))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawPolygon(QtGui.QPolygonF(self.triangle))
        sel_pt = self._from_bary(self.selector_bary)
        painter.setPen(QtGui.QPen(QtGui.QColor(0,0,0), 2))
        painter.setBrush(QtGui.QBrush(self.selector_color))
        painter.drawEllipse(sel_pt, 10, 10)
    def mousePressEvent(self, event):
        self.set_color_from_pos(event.pos())
    def mouseMoveEvent(self, event):
        self.set_color_from_pos(event.pos())
    def set_color_from_pos(self, pos):
        bary = self._barycentric(pos)
        u, v, w = bary
        if min(u, v, w) >= 0 and max(u, v, w) <= 1:
            self.selector_bary = bary
            self.selector_color = QtGui.QColor(int(u*255), int(v*255), int(w*255))
            self.update()
            self.colorChanged.emit(u, v, w)
    def set_selector(self, r, g, b):
        total = r + g + b
        bary = (1/3, 1/3, 1/3) if total == 0 else (r/total, g/total, b/total)
        self.selector_bary = bary
        self.selector_color = QtGui.QColor(int(r*255), int(g*255), int(b*255))
        self.update()

class ColorPickerDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Picker")
        self.setFixedSize(420, 320)
        layout = QtWidgets.QGridLayout(self)
        self.r = self.g = self.b = 1.0
        self.sat = self.val = 1.0
        self._updating = False
        self.triangle = ColorTriangle(self)
        self.square = ColorSquare(self)
        layout.addWidget(self.triangle, 0, 0)
        layout.addWidget(self.square, 0, 1)
        rgb_layout = QtWidgets.QHBoxLayout()
        self.r_edit = QtWidgets.QLineEdit("255"); self.g_edit = QtWidgets.QLineEdit("255"); self.b_edit = QtWidgets.QLineEdit("255")
        self.hue_edit = QtWidgets.QLineEdit("0")
        for edit, label in zip([self.r_edit, self.g_edit, self.b_edit, self.hue_edit], ["R", "G", "B", "Hue"]):
            edit.setFixedWidth(40)
            rgb_layout.addWidget(QtWidgets.QLabel(label+":")); rgb_layout.addWidget(edit)
        layout.addLayout(rgb_layout, 1, 0, 1, 2)
        self.result_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.result_label, 2, 0, 1, 2)
        self.send_button = QtWidgets.QPushButton("Send Color to App")
        layout.addWidget(self.send_button, 3, 0, 1, 2)
        self.triangle.colorChanged.connect(self.on_rgb_changed)
        self.square.colorChanged.connect(self.on_sv_changed)
        self.send_button.clicked.connect(self.send_color)
        for edit in [self.r_edit, self.g_edit, self.b_edit]:
            edit.textChanged.connect(self.on_rgb_field_changed)
        self.hue_edit.textChanged.connect(self.on_hue_field_changed)
        self.update_color()
        self.square.setFocus()
    def on_rgb_changed(self, u, v, w):
        self.r, self.g, self.b = u, v, w
        h, s, v_ = rgb_to_hsv(u, v, w)
        self.square.set_selector(h, self.sat, self.val)
        self.triangle.set_selector(self.r, self.g, self.b)
        self.update_color()
    def on_sv_changed(self, sat, val):
        self.sat, self.val = sat, val
        r, g, b = hsv_to_rgb(self.square.hue, sat, val)
        self.r, self.g, self.b = r, g, b
        self.triangle.set_selector(self.r, self.g, self.b)
        self.update_color()
    def on_rgb_field_changed(self):
        if self._updating: return
        try:
            r = clamp(int(self.r_edit.text()), 0, 255)
            g = clamp(int(self.g_edit.text()), 0, 255)
            b = clamp(int(self.b_edit.text()), 0, 255)
        except Exception:
            return
        self.r, self.g, self.b = r/255.0, g/255.0, b/255.0
        h, s, v_ = rgb_to_hsv(self.r, self.g, self.b)
        self.square.set_selector(h, self.sat, self.val)
        self.triangle.set_selector(self.r, self.g, self.b)
        self.update_color()
    def on_hue_field_changed(self):
        if self._updating: return
        try:
            hue = float(self.hue_edit.text())
        except Exception:
            return
        hue = clamp(hue, 0, 359)
        r, g, b = hsv_to_rgb(hue/359.0, self.sat, self.val)
        self.r, self.g, self.b = r, g, b
        self.square.set_selector(hue/359.0, self.sat, self.val)
        self.triangle.set_selector(self.r, self.g, self.b)
        self.update_color()
    def update_color(self):
        self._updating = True
        color = QtGui.QColor(int(self.r*255), int(self.g*255), int(self.b*255))
        h, s, v_ = color.getHsvF()[:3]
        out_color = QtGui.QColor(); out_color.setHsvF(h, self.sat, self.val)
        hex_code = out_color.name().lower()
        self.result_label.setText(f"{hex_code}")
        self.result_label.setStyleSheet(f"background:{hex_code}; color:{'#000' if self.val > 0.6 else '#fff'}; font-size:16px; padding:8px;")
        # Update fields only if needed
        for edit, val in zip([self.r_edit, self.g_edit, self.b_edit], [self.r, self.g, self.b]):
            if edit.text() != str(int(val*255)):
                edit.setText(str(int(val*255)))
        if self.hue_edit.text() != str(int(h*359)):
            self.hue_edit.setText(str(int(h*359)))
        self._updating = False
    def send_color(self):
        color = QtGui.QColor(int(self.r*255), int(self.g*255), int(self.b*255))
        h, s, v_ = color.getHsvF()[:3]
        out_color = QtGui.QColor(); out_color.setHsvF(h, self.sat, self.val)
        hex_code = out_color.name()
        store_used_color(hex_code)
        html = f'<span style="background:{hex_code};">___</span>' \
               f'<span style="color:{hex_code};"> {hex_code} </span>'
        print(html)
        sys.stdout.flush()
        self.accept()

# Utility: Store all used colors in an environment variable
USED_COLORS_ENV = "DESKTOP_TEXTBOARD_COLORS"

def store_used_color(hex_code):
    """Add a color hex code to the DESKTOP_TEXTBOARD_COLORS env variable (comma-separated, unique)."""
    colors = os.environ.get(USED_COLORS_ENV, "")
    color_list = [c for c in colors.split(",") if c]
    if hex_code.lower() not in [c.lower() for c in color_list]:
        color_list.append(hex_code)
        os.environ[USED_COLORS_ENV] = ",".join(color_list)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = ColorPickerDialog()
    dlg.exec()
