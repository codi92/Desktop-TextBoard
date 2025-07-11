# Desktop TextBoard

**Desktop TextBoard** is a floating, always-on-bottom, frameless text editor for Windows, built with PyQt6.

---

## Features
- Theme support (light/dark mode)
- Automatic window color adjustment based on desktop wallpaper color and Windows dark mode
- Manual change window transparency and opacity
- Change window size and position with keyboard shortcuts
- Frameless, always-on-bottom window for quick notes or reference
- Auto-save and persistent history (undo/redo)
- Rich text editing: font, color, highlight (right-click menu)
- Paste and resize images (Ctrl+V, right-click image; scaling only via context menu when image is selected)
- Horizontal scroll (Shift+Wheel)
- System tray integration (show/hide{by double-clicking on the tray icon}, clipboard auto-capture , show the raw content in the text area, settings, exit)
- Settings dialog for font and save file location
- Snippet system: Run Python scripts from the `snippets/` folder with parameter passing and HTML/plain text output
- URL detection and clickable links
- Custom HTML tag visualization with `.( ... ).` syntax
- Clipboard catch mode (optionally auto-paste clipboard content)
- Html clipboard support (auto-converts HTML to rich text) and supports pasting images with auto-conversion to base64
- Search and replace dialogs with match count and navigation
- External image embedding (auto-converts `<img src="http...">` to base64)
- Font size sanitization for pasted HTML (prevents font errors)

---

## Usage

- **Right-click text:** Change font, text color, or highlight
- **Selct Image:** Use the buttons + / = /- to change image size (width/height, aspect ratio lock)
- **Paste image:** Ctrl+V
- **Horizontal scroll:** Shift+Wheel
- **System tray:** Right-click for menu, double-click to show/hide
- **Snippets:** Type `~snippet.py{param:value}` and press Enter to run a Python snippet with parameters
- **Custom HTML tag:** Type `.(<b>bold</b>).` and press `.`, `/`, or `>` to render as HTML
- **Search:** Ctrl+F, F3, or use the search dialog
- **Replace:** Ctrl+H or use the replace dialog
- **Clipboard catch:** Enable/disable from tray menu to auto-paste clipboard changes

---

## Installation

1. Install Python 3.10+ ([python.org](https://www.python.org/downloads/))
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
| Ctrl+S                  | Save now                        |
| Ctrl+N                  | Clear text                      |
| Shift+Wheel             | Horizontal scroll               |
| Right-click on text     | Font/color/highlight menu       |
| Right-click on image    | Change image size (context)     |
| Ctrl+V                  | Paste image                     |
| Ctrl+F / F3             | Search                          |
| Ctrl+H                  | Replace                         |
| Ctrl+Q                  | Exit                            |
| Ctrl+Alt+Arrows         | Move window                     |
| Alt+Arrows              | Change the window transparency  |

---

## License

MIT License

---

## Author

Slajnev Pavel

---

# TODO

- [ ] Consider implementing configurable or per-snippet timeout logic in the future. Currently, all snippet executions run with no timeout (unlimited runtime).
- [ ] Add more built-in snippets for common tasks.
- [ ] Improve image resizing functionality to allow more intuitive resizing directly from the image.
- [ ] Add more customization options for themes and colors.
- [ ] Improve error handling and user feedback for snippet execution.
- [ ] Minimize the code size by removing unused imports and optimizing the code structure.
