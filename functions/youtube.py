import re, textwrap, json, requests, base64
from html import escape
from PyQt6 import QtWidgets, QtGui, QtCore
import textwrap

def show_youtube_preview_dialog(url, parent=None):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        html_text = r.text
    except Exception:
        return None
    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html_text)
    title = title_match.group(1) if title_match else "YouTube Video"
    image_match = re.search(r'<meta property="og:image" content="([^"]+)"', html_text)
    image_url = image_match.group(1) if image_match else ""
    desc_match = re.search(r'"shortDescription":"((?:\\.|[^"\\])*)"', html_text)
    description_raw = ""
    if desc_match:
        try:
            description_raw = json.loads(f'"{desc_match.group(1)}"')
        except:
            description_raw = desc_match.group(1)
    urls = []

    def url_replacer(m):
        url_full = m.group(0)
        hostname = re.sub(r"^https?://(www\.)?", "", url_full).split("/")[0]
        if url_full not in urls:
            urls.append(url_full)
        index = urls.index(url_full) + 1
        return f'<a href="{escape(url_full)}" target="_blank">{escape(hostname)}</a> [{index}]'

    url_pattern = re.compile(r'https?://[^\s<>"\']+')
    description_with_links = url_pattern.sub(url_replacer, description_raw)
    timecode_pattern = re.compile(r"(\d{1,2}:)?\d{1,2}:\d{2}")

    def to_seconds(tc):
        parts = list(map(int, tc.split(":")))
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return 0

    vid_match = re.search(r"v=([^&]+)", url)
    video_id = vid_match.group(1) if vid_match else ""

    def timecode_replacer(m):
        tc = m.group(0)
        seconds = to_seconds(tc)
        link = f"https://www.youtube.com/watch?v={escape(video_id)}&t={seconds}"
        return f'<a href="{link}" target="_blank">{escape(tc)}</a>'

    description_with_links = timecode_pattern.sub(
        timecode_replacer, description_with_links
    )

    def wrap_lines_preserving_html(text, width=80):
        wrapped_lines = []
        for line in text.split("\n"):
            parts = re.split(r"(<a [^>]+>.*?</a>)", line)
            wrapped_line = ""
            for part in parts:
                if part.startswith("<a "):
                    wrapped_line += part
                else:
                    wrapped_line += "\n".join(
                        textwrap.wrap(part, width=width, replace_whitespace=False)
                    )
            wrapped_lines.append(wrapped_line)
        return "\n".join(wrapped_lines)

    description_wrapped = wrap_lines_preserving_html(description_with_links)
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("YouTube Preview")
    dialog.resize(600, 600)
    layout = QtWidgets.QVBoxLayout(dialog)
    title_checkbox = QtWidgets.QCheckBox("Show Title")
    title_checkbox.setChecked(True)
    layout.addWidget(title_checkbox)
    title_link = QtWidgets.QLabel(
        f'<a href="{escape(url)}" target="_blank"><b>{escape(title)}</b></a>'
    )
    title_link.setOpenExternalLinks(True)
    title_link.setTextInteractionFlags(
        QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
    )
    layout.addWidget(title_link)
    image_checkbox = QtWidgets.QCheckBox("Show Thumbnail")
    image_checkbox.setChecked(True)
    layout.addWidget(image_checkbox)
    image_label = QtWidgets.QLabel()
    image_label.setText("[No thumbnail]")
    image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    image = None
    if image_url:
        try:
            img_data = requests.get(image_url).content
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(img_data)
            thumb_pixmap = pixmap.scaled(
                120,
                90,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            image_label.setPixmap(thumb_pixmap)
            image = thumb_pixmap.toImage()
        except:
            pass
    layout.addWidget(image_label)
    desc_checkbox = QtWidgets.QCheckBox("Show Description")
    desc_checkbox.setChecked(True)
    layout.addWidget(desc_checkbox)
    desc_edit = QtWidgets.QTextEdit()
    desc_edit.setReadOnly(True)
    desc_edit.setAcceptRichText(True)
    desc_edit.setHtml(
        description_wrapped.replace("\n", "<br>")
        if description_wrapped
        else "[No description]"
    )
    desc_edit.setMinimumHeight(200)
    layout.addWidget(desc_edit)
    button_box = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
        | QtWidgets.QDialogButtonBox.StandardButton.Cancel
    )
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    def update_visibility():
        title_link.setVisible(title_checkbox.isChecked())
        image_label.setVisible(image_checkbox.isChecked())
        desc_edit.setVisible(desc_checkbox.isChecked())

    title_checkbox.stateChanged.connect(update_visibility)
    image_checkbox.stateChanged.connect(update_visibility)
    desc_checkbox.stateChanged.connect(update_visibility)
    update_visibility()
    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        if not (
            title_checkbox.isChecked()
            or image_checkbox.isChecked()
            or desc_checkbox.isChecked()
        ):
            return f'<a href="{escape(url)}" target="_blank"><b>{escape(title)}</b></a><br>'
        final_html = ""
        if title_checkbox.isChecked():
            final_html += f'<a href="{escape(url)}" target="_blank"><b>{escape(title)}</b></a><br>'
        if image is not None and image_checkbox.isChecked():
            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
            image.save(buffer, "PNG")
            base64_data = base64.b64encode(buffer.data()).decode("utf-8")
            final_html += (
                f'<a href="{escape(url)}" target="_blank">'
                f'<img src="data:image/png;base64,{base64_data}" '
                f'width="{image.width()}" height="{image.height()}"></a><br>'
            )
        if desc_checkbox.isChecked():
            final_html += description_wrapped.replace("\n", "<br>")
        return final_html
    return None


def show_youtube_playlist_dialog(playlist_url, parent=None):
    def fetch_video_data(video_url):
        try:
            r = requests.get(video_url, timeout=5)
            r.raise_for_status()
            html_text = r.text
        except Exception:
            return None, None, None
        title_match = re.search(
            r'<meta property="og:title" content="([^"]+)"', html_text
        )
        title = title_match.group(1) if title_match else "YouTube Video"
        image_match = re.search(
            r'<meta property="og:image" content="([^"]+)"', html_text
        )
        image_url = image_match.group(1) if image_match else ""
        desc_match = re.search(r'"shortDescription":"((?:\\.|[^"\\])*)"', html_text)
        description_raw = ""
        if desc_match:
            try:
                description_raw = json.loads(f'"{desc_match.group(1)}"')
            except:
                description_raw = desc_match.group(1)
        return title, image_url, description_raw

    def shorten_url_with_index(url, index):
        hostname = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        return (
            f'<a href="{escape(url)}" target="_blank">{escape(hostname)}</a> [{index}]'
        )

    def process_description(desc, video_id):
        url_pattern = re.compile(r'https?://[^\s<>"\']+')
        urls = []

        def url_replacer(m):
            url_full = m.group(0)
            if url_full not in urls:
                urls.append(url_full)
            index = urls.index(url_full) + 1
            return f'<a href="{escape(url_full)}" target="_blank">{escape(re.sub(r"^https?://(www\.)?", "", url_full).split("/")[0])}</a> [{index}]'

        desc_with_links = url_pattern.sub(url_replacer, desc)
        timecode_pattern = re.compile(r"(\d{1,2}:)?\d{1,2}:\d{2}")
        def to_seconds(tc):
            parts = list(map(int, tc.split(":")))
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            return 0

        def timecode_replacer(m):
            tc = m.group(0)
            seconds = to_seconds(tc)
            link = f"https://www.youtube.com/watch?v={escape(video_id)}&t={seconds}"
            return f'<a href="{link}" target="_blank">{escape(tc)}</a>'

        desc_with_links = timecode_pattern.sub(timecode_replacer, desc_with_links)

        def wrap_lines_preserving_html(text, width=80):
            wrapped_lines = []
            for line in text.split("\n"):
                parts = re.split(r"(<a [^>]+>.*?</a>)", line)
                wrapped_line = ""
                for part in parts:
                    if part.startswith("<a "):
                        wrapped_line += part
                    else:
                        wrapped_line += "\n".join(
                            textwrap.wrap(part, width=width, replace_whitespace=False)
                        )
                wrapped_lines.append(wrapped_line)
            return "\n".join(wrapped_lines)

        return wrap_lines_preserving_html(desc_with_links)

    def fetch_playlist_video_urls(playlist_url):
        try:
            r = requests.get(playlist_url, timeout=5)
            r.raise_for_status()
            html_text = r.text
        except Exception:
            return []
        video_ids = re.findall(r"\"videoId\":\"([^\"]+)\"", html_text)
        seen = set()
        videos = []
        for vid in video_ids:
            if vid not in seen:
                seen.add(vid)
                videos.append(f"https://www.youtube.com/watch?v={vid}")
        return videos

    videos = fetch_playlist_video_urls(playlist_url)
    if not videos:
        QtWidgets.QMessageBox.warning(
            parent, "Error", "Failed to load playlist or no videos found."
        )
        return None
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("YouTube Playlist Preview")
    dialog.resize(900, 700)
    layout = QtWidgets.QVBoxLayout(dialog)
    hbox_checks = QtWidgets.QHBoxLayout()
    show_titles_cb = QtWidgets.QCheckBox("Show Titles")
    show_titles_cb.setChecked(True)
    show_prevs_cb = QtWidgets.QCheckBox("Show Thumbnails")
    show_prevs_cb.setChecked(True)
    show_desc_cb = QtWidgets.QCheckBox("Show Descriptions")
    show_desc_cb.setChecked(True)
    hbox_checks.addWidget(show_titles_cb)
    hbox_checks.addWidget(show_prevs_cb)
    hbox_checks.addWidget(show_desc_cb)
    layout.addLayout(hbox_checks)
    scroll_area = QtWidgets.QScrollArea()
    scroll_area.setWidgetResizable(True)
    container = QtWidgets.QWidget()
    scroll_area.setWidget(container)
    videos_layout = QtWidgets.QGridLayout(container)
    video_widgets = []
    for i, video_url in enumerate(videos):
        title, image_url, raw_desc = fetch_video_data(video_url)
        video_id_match = re.search(r"v=([^&]+)", video_url)
        video_id = video_id_match.group(1) if video_id_match else ""
        desc = process_description(raw_desc or "", video_id)
        title_edit = QtWidgets.QLineEdit(title)
        title_edit.setMinimumWidth(200)
        thumb_label = QtWidgets.QLabel("[No thumbnail]")
        thumb_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        thumb_pixmap = None
        if image_url:
            try:
                img_data = requests.get(image_url).content
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(img_data)
                thumb_pixmap = pixmap.scaled(
                    120,
                    90,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                thumb_label.setPixmap(thumb_pixmap)
            except:
                pass
        desc_edit = QtWidgets.QTextEdit()
        desc_edit.setReadOnly(False)
        desc_edit.setAcceptRichText(True)
        desc_edit.setHtml(desc.replace("\n", "<br>") if desc else "[No description]")
        desc_edit.setMinimumHeight(120)
        desc_edit.setMinimumWidth(400)
        video_widgets.append(
            (title_edit, thumb_label, desc_edit, video_url, thumb_pixmap)
        )
        videos_layout.addWidget(title_edit, i, 0)
        videos_layout.addWidget(thumb_label, i, 1)
        videos_layout.addWidget(desc_edit, i, 2)
    layout.addWidget(scroll_area)
    button_box = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
        | QtWidgets.QDialogButtonBox.StandardButton.Cancel
    )
    layout.addWidget(button_box)

    def update_visibility():
        show_titles = show_titles_cb.isChecked()
        show_prevs = show_prevs_cb.isChecked()
        show_desc = show_desc_cb.isChecked()
        for (title_w, prev_w, desc_w, *_) in video_widgets:
            title_w.setVisible(show_titles)
            prev_w.setVisible(show_prevs)
            desc_w.setVisible(show_desc)

    show_titles_cb.stateChanged.connect(update_visibility)
    show_prevs_cb.stateChanged.connect(update_visibility)
    show_desc_cb.stateChanged.connect(update_visibility)
    update_visibility()
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        results = []
        for title_w, prev_w, desc_w, video_url, thumb_pixmap in video_widgets:
            title_val = title_w.text()
            desc_val = desc_w.toHtml()
            if not (
                show_titles_cb.isChecked()
                or show_prevs_cb.isChecked()
                or show_desc_cb.isChecked()
            ):
                results.append(
                    f'<a href="{escape(video_url)}" target="_blank">{escape(title_val)}</a>'
                )
                continue
            html = ""
            if show_titles_cb.isChecked():
                html += f'<a href="{escape(video_url)}" target="_blank"><b>{escape(title_val)}</b></a><br>'
            if show_prevs_cb.isChecked() and thumb_pixmap is not None:
                buffer = QtCore.QBuffer()
                buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
                thumb_pixmap.toImage().save(buffer, "PNG")
                base64_data = base64.b64encode(buffer.data()).decode("utf-8")
                html += (
                    f'<a href="{escape(video_url)}" target="_blank">'
                    f'<img src="data:image/png;base64,{base64_data}" '
                    f'width="{thumb_pixmap.width()}" height="{thumb_pixmap.height()}"></a><br>'
                )
            if show_desc_cb.isChecked():
                html += desc_val.replace("\n", "<br>")
            results.append(html)
        return results
    return None
