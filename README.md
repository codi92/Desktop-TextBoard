# Desktop TextBoard

**Desktop TextBoard** is a floating, always-on-bottom, frameless text editor for Windows, built with PyQt6.  
It supports rich text, image pasting (with scaling), auto-save, font and color customization, and system tray integration.

---

## Features

- **Frameless, always-on-bottom window** (great for sticky notes or quick reference)
- **Auto-save** to a JSON file (configurable location)
- **Rich text editing** (font, color, highlight via right-click menu)
- **Paste images** (Ctrl+V, supports base64-embedded images)
- **Resize images** via right-click context menu
- **Font scaling** (Ctrl+Mouse Wheel or Ctrl++/Ctrl+-)
- **Horizontal scroll** (Shift+Mouse Wheel)
- **System tray integration** (hide/show, save, clear, settings, about, exit)
- **Settings dialog** for font and save file location
- **No in-memory undo/redo/history** — always works directly with the file

---

## Usage

- **Right-click on text:** Change font, text color, or highlight.
- **Right-click on image:** Change image size (width/height, with aspect ratio lock).
- **Paste image:** Ctrl+V (from clipboard).
- **Zoom text:** Ctrl+Mouse Wheel or Ctrl++/Ctrl+-.
- **Scroll horizontally:** Shift+Mouse Wheel.
- **System tray:** Right-click tray icon for menu, double-click to show/hide.

---

## Installation

1. **Install Python 3.10+** (recommended from [python.org](https://www.python.org/downloads/))
2. **Install dependencies:**
    ```sh
    pip install PyQt6
    ```
3. **Run the app:**
    ```sh
    python desktop_textboard.py
    ```

---

## Build as EXE (Windows)

1. **Install PyInstaller:**
    ```sh
    pip install pyinstaller
    ```
2. **Build:**
    ```sh
    pyinstaller --noconfirm --onefile --windowed desktop_textboard.py
    ```
3. The EXE will be in the `dist` folder.

---

## Configuration

- **Settings** (font, save file location) are stored in `~/.config_desktop_textboard.json`
- **Text and images** are saved as HTML in the configured JSON file.

---

## Shortcuts

| Shortcut                | Action                        |
|-------------------------|-------------------------------|
| Ctrl+Z / Ctrl+Y         | Undo / Redo (built-in)        |
| Ctrl+S                  | Save now                      |
| Ctrl+N                  | Clear text                    |
| Ctrl++ / Ctrl+- / Wheel | Zoom in/out                   |
| Shift+Wheel             | Horizontal scroll             |
| Right-click on text     | Font/color/highlight menu     |
| Right-click on image    | Change image size             |
| Ctrl+V                  | Paste image                   |

---

## License

MIT License

---

## Author

Slajnev Pavel
