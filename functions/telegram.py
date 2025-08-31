import json, os, re, base64, asyncio, zipfile
from io import BytesIO
from dotenv import load_dotenv
from PyQt6 import QtWidgets, QtGui, QtCore
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import MessageMediaPhoto
from telethon.sync import TelegramClient
from telethon.tl.types import InputPeerSelf

load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELEGRAM_SESSION", "tg_session")

def message_window(message,type=None, step=None):
    if type == "error":
        print("Error:", message)
        pass
    elif type == "info":
        print("Info:", message)
        # Show info message
        pass
    elif type == "auth":
        if step not in ["phone", "code"]:
            print("Invalid auth step:", step)
            return
        print("Auth step:", step)
        if step == "phone":
            # Show phone input dialog
            pass
        print("Auth step:", step)
        if step == "code":
            pass

        pass
    pass

class TelegramLoginDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Login")
        self.setModal(True)
        self.resize(300, 150)
        self.phone_label = QtWidgets.QLabel("Please enter your phone (or bot token):")
        self.phone_edit = QtWidgets.QLineEdit()
        self.code_label = QtWidgets.QLabel("Please enter the code you received:")
        self.code_edit = QtWidgets.QLineEdit()
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: red")
        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.setEnabled(False)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.phone_label)
        layout.addWidget(self.phone_edit)
        layout.addWidget(self.code_label)
        layout.addWidget(self.code_edit)
        layout.addWidget(self.status_label)
        layout.addWidget(self.ok_button)
        self.phone_edit.textChanged.connect(self._on_text_changed)
        self.code_edit.textChanged.connect(self._on_text_changed)
        self.ok_button.clicked.connect(self.accept)
    def _on_text_changed(self, _):
        if self.phone_label.isVisible():
            self.ok_button.setEnabled(bool(self.phone_edit.text().strip()))
        elif self.code_label.isVisible():
            self.ok_button.setEnabled(bool(self.code_edit.text().strip()))
    def exec_phone(self):
        self.phone_label.show()
        self.phone_edit.show()
        self.code_label.hide()
        self.code_edit.hide()
        self.status_label.clear()
        self.ok_button.setEnabled(False)
        self.phone_edit.clear()
        return self.exec() == QtWidgets.QDialog.DialogCode.Accepted and self.phone_edit.text().strip() or None
    def exec_code(self):
        self.phone_label.hide()
        self.phone_edit.hide()
        self.code_label.show()
        self.code_edit.show()
        self.status_label.clear()
        self.ok_button.setEnabled(False)
        self.code_edit.clear()
        return self.exec() == QtWidgets.QDialog.DialogCode.Accepted and self.code_edit.text().strip() or None
    def set_status(self, message):
        self.status_label.setText(message)


async def login_with_gui():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialog = TelegramLoginDialog()
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        phone = None
        while not phone:
            phone = dialog.exec_phone()
            if phone is None:
                await client.disconnect()
                return None

        try:
            await client.send_code_request(phone)
        except Exception as e:
            dialog.set_status(f" Failed to send code: {e}")
            return None

        code = None
        while not code:
            code = dialog.exec_code()
            if code is None:
                await client.disconnect()
                return None
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                dialog.set_status(" 2FA not supported yet.")
                return None
            except Exception as e:
                dialog.set_status(f" Failed to sign in: {e}")
                code = None
    return client


def send_html_message(message: str, callback=None):
    async def runner():
        html = message
        try:
            client = await login_with_gui()
        except Exception as e:
            html = f"Failed to connect to Telegram: {e}"
            if callback:
                callback(html)
            return
        if client and message:
            await client.send_message("me", message, parse_mode="html")
            await client.disconnect()
        if not message:
            html += "Error: No message to send."
        if not client:
            html += "Failed to connect to Telegram."
        if callback:
            callback(html)
    try:
        asyncio.get_running_loop()
        asyncio.create_task(runner())
    except RuntimeError:
        asyncio.run(runner())

def wrap_text_in_html(text, max_length=80):
    lines = []
    for line in text.splitlines():
        if len(line) > max_length:
            wrapped_lines = [line[i:i + max_length] for i in range(0, len(line), max_length)]
            lines.extend(wrapped_lines)
        else:
            lines.append(line)
    return "<br>".join(lines)

def get_saved_messages_html(limit=1, callback=None):
    async def runner():
        try:
            client = await login_with_gui()
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, "Error", f"Failed to connect to Telegram: {e}")
            return
        if not client:
            return
        html = "<table style='border: 1px solid black; width: 500px; border-collapse: collapse; text-align: left; '>"
        import getpass
        username = getpass.getuser()
        download_folder = os.path.join(os.path.expanduser('~'), 'Downloads', 'Telegram Desktop')
        os.makedirs(download_folder, exist_ok=True)
        me = await client.get_me()
        async for msg in client.iter_messages("me", limit=limit):
            html += "<tr style='border: 1px solid black;'>"
            local_date = msg.date.astimezone()
            html += f"<td style='border: 1px solid black;'>{local_date.strftime('%Y-%m-%d %H:%M:%S')}</td>"
            if msg.text:
                html += f"<td style='border: 1px solid black;'>{wrap_text_in_html(msg.text)}</td>"
            # Photo
            if isinstance(msg.media, MessageMediaPhoto):
                img = await client.download_media(msg.media.photo, file=BytesIO())
                if img:
                    img.seek(0)
                    data = img.read()
                    image = QtGui.QImage()
                    if image.loadFromData(data):
                        orig_width = image.width()
                        orig_height = image.height()
                        new_width = 300
                        new_height = int(orig_height * new_width / orig_width)
                        buffer = QtCore.QBuffer()
                        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
                        image.save(buffer, "PNG")
                        base64_data = base64.b64encode(buffer.data()).decode("utf-8")
                        html += f'<td style="border: 1px solid black;"><img src="data:image/png;base64,{base64_data}" width="{new_width}" height="{new_height}"></td>'
                    else:
                        html += f"<td style='border: 1px solid black;'>Failed to load image</td>"
            elif msg.file:
                file_name = msg.file.name if hasattr(msg.file, 'name') and msg.file.name else f"file_{msg.id}"
                local_path = os.path.join(download_folder, file_name)
                if os.path.exists(local_path):
                    base, ext = os.path.splitext(file_name)
                    dt_str = msg.date.strftime("_%Y%m%d_%H%M%S")
                    file_name_new = f"{base}{dt_str}{ext}"
                    local_path = os.path.join(download_folder, file_name_new)
                if not os.path.exists(local_path):
                    if msg.file.size > 10 * 1024 * 1024:  # 10 MB limit
                        html += f"<td style='border: 1px solid black;'>File too large to download<br>"
                        html += f"The file can be downloaded by <a href='telegram_msg_id={msg.id}'>Message</a></td>"
                        await client.disconnect()
                        if callback:
                            callback(html)
                        return
                    try:
                        await client.download_media(msg, file=local_path)
                    except Exception as e:
                        html += f"<td style='border: 1px solid black;'>Download failed: {e}</td>"
                        local_path = None
                if local_path and os.path.exists(local_path):
                    file_url = 'file:///' + local_path.replace('\\', '/')
                    html += f"<td style='border: 1px solid black;'><a href='{file_url}' target='_blank'>Open file</a></td>"
                else:
                    html += "<td style='border: 1px solid black;'>File not found</td>"
            else:
                html += "<td style='border: 1px solid black;'></td>"
            msg_dict = {
                "id": msg.id,
                "date": msg.date.isoformat(),
                "text": msg.text,
                "sender_id": getattr(msg.sender_id, 'user_id', msg.sender_id) if hasattr(msg, 'sender_id') else None,
                "media": "photo" if isinstance(msg.media, MessageMediaPhoto) else str(type(msg.media)) if msg.media else None
            }
            html += f'<td style="border: 1px solid black;">{json.dumps(msg_dict, ensure_ascii=False)}</td><td style="border: 1px solid black;">{msg}</td>'
            html += "</tr>"
        html += "</table>"
        await client.disconnect()

        if callback:
            callback(html)

    try:
        asyncio.get_running_loop()
        asyncio.create_task(runner())
    except RuntimeError:
        asyncio.run(runner())

def parse_p_line(line_text):
    raw = line_text[3:].strip()
    if " / " not in raw:
        return None, None
    main_part, size = raw.rsplit(" / ", 1)
    match = re.match(r"(.+?)\s+([B-Zb-z]:[\\/].+)", main_part)
    if not match:
        return None, None
    filename = match.group(1).strip()
    path = match.group(2).strip()
    return filename, path

async def send_file_to_saved(line_text: str):
    filename, file_path = parse_p_line(line_text)
    if not filename or not file_path:
        print("Invalid line format.")
        return
    try:
        if not line_text.startswith("[p]"):
            return
        main_part = line_text[3:].strip().split(" / ")[0]
        match = re.match(r"(.+?)\s+([A-Za-z]:[\\/].+)", main_part)
        if not match:
            return
        name = match.group(1).strip()
        path = match.group(2).strip().strip('"')
        try:
            client = await login_with_gui()
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, "Error", f"Failed to connect to Telegram: {e}")
            return
        if not client:
            return

        if os.path.isdir(path):
            safe_name = name.replace(' ', '_')
            zip_path = QtCore.QDir.tempPath() + f"/{safe_name}.zip"
            #determine size of the directory
            total_size = 0
            for root, dirs, files in os.walk(path):
                for file in files:
                    full_path = os.path.join(root, file)
                    total_size += os.path.getsize(full_path)
            if total_size > 2048 * 1024 * 1024:  # 2 GB limit
                QtCore.QTimer.singleShot(0, lambda: QtWidgets.QMessageBox.warning(None, "Error", "Directory size exceeds 2 GB limit."))
                await client.disconnect()
                return
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        arcname = os.path.relpath(full_path, start=path)
                        zipf.write(full_path, arcname)
            try:
                result = await client.send_file("me", zip_path, caption=f"{name}.zip")
                os.remove(zip_path)
                await client.disconnect()
            except Exception as e:
                QtCore.QTimer.singleShot(0, lambda: QtWidgets.QMessageBox.warning(None, "Error", f"Failed to send file: {e}"))
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                await client.disconnect()
                return
        elif os.path.isfile(path):
            try:
                result = await client.send_file("me", path, caption=name)
                await client.disconnect()
            except Exception as e:
                QtCore.QTimer.singleShot(0, lambda: QtWidgets.QMessageBox.warning(None, "Error", f"Failed to send file: {e}"))
                await client.disconnect()
                return
        else:
            QtCore.QTimer.singleShot(0, lambda: QtWidgets.QMessageBox.warning(None, "Error",  "Path is invalid"))
            await client.disconnect()
            return
        return

    except Exception as e:
        QtWidgets.QMessageBox.warning(None, "Error", f"Failed to send file: {e}")
        return

def download_large_file(id):
    async def runner():
        try:
            client = await login_with_gui()
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, "Error", f"Failed to connect to Telegram: {e}")
            return
        if not client:
            return
        try:
            msg = await client.get_messages("me", ids=id)
            if not msg or not msg.file or not msg.file.size:
                QtWidgets.QMessageBox.warning(None, "Error", "No file found in the message.")
                return
            local_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'Telegram Desktop', msg.file.name)
            await client.download_media(msg, file=local_path)
            QtWidgets.QMessageBox.information(None, "Success", f"File downloaded to {local_path}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, "Error", f"Failed to download file: {e}")
        finally:
            await client.disconnect()
    asyncio.run(runner())
    