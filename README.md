# Desktop TextBoard

**Desktop TextBoard** is a floating, always-on-bottom, frameless text editor for Windows, built with PyQt6.

---

## Features
- Floating, always-on-bottom, frameless window for quick notes or reference
- Theme support: automatic color adjustment based on desktop wallpaper and Windows dark mode
- Manual window transparency/opacity control (Alt+Arrow keys)
- Window size/position control (Ctrl+Alt+Arrow keys)
- Auto-save and persistent history (undo/redo)
- Rich text editing: font, color, highlight (right-click menu)
- Paste and resize images (Ctrl+V, +/=/- keys)
- Horizontal scroll (Shift+Wheel)
- System tray integration: show/hide, clipboard auto-capture, raw mode, settings, exit
- Settings dialog for font and save file location
- Snippet system: run Python scripts from the `snippets/` folder with parameter passing and HTML/plain text output
- URL detection and clickable links
- Custom HTML tag visualization with `.( ... ).` syntax
- Clipboard catch mode (auto-paste clipboard content)
- HTML clipboard support (auto-converts HTML to rich text)
- Search and replace dialogs with match count and navigation
- External image embedding (auto-converts `<img src="http...">` to base64)
- Font size sanitization for pasted HTML
- Interactive to-do checkboxes: type `[_]` to insert, click to toggle, copy/paste supported

---

## Usage

- **Right-click text:** Change font, text color, or highlight
- **Select image:** Use + / = / - to change image size
- **Paste image:** Ctrl+V
- **Horizontal scroll:** Shift+Wheel
- **System tray:** Right-click for menu, double-click to show/hide
- **Snippets:** Type `~snippet.py{param:value}` and press Enter to run a Python snippet with parameters
- **Custom HTML tag:** Type `.(<b>bold</b>).` and press `.`, `/`, or `>` to render as HTML
- **Search:** Ctrl+F, F3, or use the search dialog
- **Replace:** Ctrl+H or use the replace dialog
- **Clipboard catch:** Enable/disable from tray menu to auto-paste clipboard changes
- **To-do checkbox:** Type `[_]` and press space to insert a clickable checkbox; click to toggle

---

## Installation

1. Install Python 3.10+
2. Install dependencies:
    ```sh
    pip install PyQt6 requests
    ```
3. Run the app:
    ```sh
    python desktop_textboard.py
    ```

---

## Build as EXE (Windows)

1. Install PyInstaller:
    ```sh
    pip install pyinstaller
    ```
2. Build:
    ```sh
    pyinstaller --noconfirm --onefile --windowed desktop_textboard.py
    ```
3. The EXE will be in the `dist` folder.

---

## Configuration

- Settings (font, save file location, opacity, etc.) are stored in `~/.config_desktop_textboard.json`
- Text and images are saved as HTML in the configured JSON file
- Snippets are in the `snippets/` folder. Use `~snippet.py{param:value}` to run

---

## Shortcuts

| Shortcut                | Action                          |
|-------------------------|---------------------------------|
| Ctrl+Z / Ctrl+Y         | Undo / Redo                     |
| Shift+Wheel             | Horizontal scroll               |
| Right-click on text     | Font/color/highlight menu       |
| Ctrl+V                  | Paste image                     |
| Ctrl+F / F3             | Search                          |
| Ctrl+H                  | Replace                         |
| Ctrl+Q                  | Exit                            |
| Ctrl+Alt+Arrows         | Move window                     |
| Alt+Arrows              | Change the window transparency  |
| [ ]                     | Insert interactive checkbox     |

---

## Snippets

Place Python scripts in the `snippets/` folder. Run with `~snippet.py{param:value}` syntax. Example scripts included:

- `text.py`, `now.py`, `gpt.py`, `googlesearch.py`, `drawtable.py`, `diagram.py`, `color_picker.py`, etc.

---

## File Structure

- `desktop_textboard.py` — Main application
- `functions/` — Core logic (context menu, clipboard, theming, search, etc.)
- `snippets/` — Python scripts for snippet system
- `start_textboard.bat` — Windows batch file to start the app (pythonw, no console)
- `youtube_preview.html` — HTML preview for YouTube links

---

## License

MIT License

---

## Author

Slajnev Pavel
