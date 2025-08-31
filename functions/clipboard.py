# Clipboard functions
import base64, re, os, requests
from PyQt6 import QtGui, QtCore
from functions.youtube import show_youtube_preview_dialog, show_youtube_playlist_dialog
from urllib.parse import urlparse


def has_image(image_data):
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    image_data.save(buffer, "PNG")
    base64_data = base64.b64encode(buffer.data()).decode("utf-8")
    content = f'<img src="data:image/png;base64,{base64_data}" width="{image_data.width()}" height="{image_data.height()}">'
    return content

# This function converts a size in bytes to a human-readable format.
def human_readable_size(size_bytes):
    for unit in ["Bytes", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


# This function calculates the total size of a folder and its contents.
def get_folder_size(path):
    total_size = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                fp = os.path.join(root, f)
                total_size += os.path.getsize(fp)
            except Exception:
                pass
    return total_size

# This function replaces external image URLs in HTML with embedded base64 images.
def embed_external_images(html):
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
        return f'<img src=""'

    return re.sub(r'<img\s+[^>]*src="(http[^"]+)"', replacer, html)


# This function sanitizes font sizes in HTML, replacing 0px and negative sizes with a default size.
def sanitize_font_sizes(html):
    html = re.sub(r"font-size\s*:\s*0px", "font-size:10px", html, flags=re.IGNORECASE)
    html = re.sub(
        r'font-size\s*:\s*-[^;"]+', "font-size:10px", html, flags=re.IGNORECASE
    )
    return html


# This function processes the clipboard content and returns a formatted string based on its type.
def clipboard_output(self, clipboard):
    html_data = clipboard.mimeData().html() if clipboard.mimeData().hasHtml() else None
    image_data = (
        clipboard.mimeData().imageData() if clipboard.mimeData().hasImage() else None
    )
    files_data = clipboard.mimeData().urls() if clipboard.mimeData().hasUrls() else None
    text = clipboard.mimeData().text() if clipboard.mimeData().hasText() else None
    image = QtGui.QImage(image_data) if image_data else None
    self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
    if image_data:
        content = has_image(image_data)
    elif html_data:
        content = sanitize_font_sizes(embed_external_images(html_data))
    elif files_data:
        content = "<br>".join(
            f'<a href="{url.toLocalFile()}"> {url.fileName()}</a> {url.toLocalFile() if url.isLocalFile() else "(remote)"} / {(human_readable_size(get_folder_size(url.toLocalFile())) if QtCore.QFileInfo(url.toLocalFile()).isDir() else human_readable_size(QtCore.QFileInfo(url.toLocalFile()).size()))} '
            for url in files_data
        )
    else:
        content = clipboard.mimeData().text()
    return content


# This function wraps text in HTML to ensure no line exceeds 80 characters, replacing URLs with shortened links.


def insert_to_cursor(self, source, cursor):
    if source.hasText():
        text = source.text().strip()
        if "youtube.com/playlist" in text or "list=" in text and "yt" in text:
            previews = show_youtube_playlist_dialog(text)
            if previews:
                for preview in previews:
                    cursor.insertHtml(preview + "<br>")
                return
        elif "youtube.com/watch" in text or "youtu.be/" in text:
            preview = show_youtube_preview_dialog(text)
            if preview:
                cursor.insertHtml(preview)
                return
        elif "http:" in text or "https:" in text:
            if "?" in text:
                parameters = {}
                url = text.split("?")[0]
                params = text.split("?")[1] if "?" in text else ""
                url = text.split("?")[0]
                for param in params.split("&"):
                    try:
                        key, value = param.split("=")
                    except ValueError:
                        cursor.insertHtml(
                            f'<a href="{text}">{url}</a> <span style="color:gray">[{len(url)}]</span> <br>Invalid parameter format: {param}<br>'
                        )
                        return
                    parameters[key] = value
                cursor.insertHtml(
                    f'<a href="{text}">{url}</a> <span style="color:gray">[{len(url)}]</span> <br>Parameters: {", ".join(f"{k}={v}" for k, v in parameters.items())}<br>'
                )
                return
            strings = text.split("/")
            cursor.insertHtml(
                f'<a href="{text}">{strings[2]}_{strings[-1]}</a> <span style="color:gray">[{len(text)}]</span>'
            )
            return

    if source.hasImage():
        image = QtGui.QImage(source.imageData())
        if not image.isNull():
            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
            image.save(buffer, "PNG")
            base64_data = base64.b64encode(buffer.data()).decode("utf-8")
            html = f'<img src="data:image/png;base64,{base64_data}" width="{image.width()}" height="{image.height()}">'
            cursor.insertHtml(html)
            return

    if source.hasHtml():
        html = source.html()
        html = embed_external_images(html)
        html = sanitize_font_sizes(html)
        cursor.insertHtml(html)
        return
    if source.hasUrls():
        urls = source.urls()
        if urls:
            content = (
                "<br>".join(
                    f'<a href="{url.toLocalFile()}"> {url.fileName()}</a> {url.toLocalFile() if url.isLocalFile() else "(remote)"} / '
                    f"{human_readable_size(get_folder_size(url.toLocalFile())) if QtCore.QFileInfo(url.toLocalFile()).isDir() else human_readable_size(QtCore.QFileInfo(url.toLocalFile()).size())}"
                    for url in urls
                )
                + "<br>"
            )
            cursor.insertHtml(content)
        return
    if source.hasText():
        text = source.text()
        if text.startswith("~") and text.endswith("~"):
            text = text[1:-1]
        cursor.insertText(text)
        return
    return source
