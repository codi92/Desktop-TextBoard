import ctypes
from PyQt6.QtGui import QImage, QColor
from PyQt6.QtCore import QFileInfo
import winreg

def windows_is_dark_mode():
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(reg, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        # 0 = dark mode, 1 = light mode
        return value == 0
    except Exception:
        return False

def get_wallpaper_path():
    buffer = ctypes.create_unicode_buffer(260)
    ctypes.windll.user32.SystemParametersInfoW(0x0073, 260, buffer, 0)  # SPI_GETDESKWALLPAPER
    return buffer.value

def get_average_wallpaper_color(image_path):
    image = QImage(image_path)
    if image.isNull():
        return QColor(0, 0, 0)
    r = g = b = count = 0
    step = max(1, image.width() // 100)
    for x in range(0, image.width(), step):
        for y in range(0, image.height(), step):
            r += image.pixelColor(x, y).red()
            g += image.pixelColor(x, y).green()
            b += image.pixelColor(x, y).blue()
            count += 1
    return QColor(r // count, g // count, b // count) if count > 0 else QColor(0, 0, 0)

def get_default_desktop_color():
    COLOR_DESKTOP = 1
    colorref = ctypes.windll.user32.GetSysColor(COLOR_DESKTOP)
    r = colorref & 0xFF
    g = (colorref >> 8) & 0xFF
    b = (colorref >> 16) & 0xFF
    return QColor(r, g, b)

def get_desktop_base_color():
    path = get_wallpaper_path()
    if QFileInfo(path).exists():
        return get_average_wallpaper_color(path)
    else:
        return get_default_desktop_color()

if __name__ == "__main__":
    color = get_desktop_base_color()
    print(color.name())
# This code retrieves the desktop wallpaper path, calculates the average color of the wallpaper,