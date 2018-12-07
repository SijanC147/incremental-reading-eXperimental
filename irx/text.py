from __future__ import unicode_literals
from collections import defaultdict
import urllib2
import re
import time
from io import BytesIO
import base64
from os.path import normpath, basename, join, exists
import cPickle as pickle
from cStringIO import StringIO

from PyQt4.QtGui import (
    QApplication, QImage, QAbstractItemView, QDialog, QDialogButtonBox, QPixmap,
    QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QLabel,
    QBrush, QColor
)
from PyQt4.QtWebKit import QWebPage
from PyQt4.QtCore import Qt, QBuffer

from anki.notes import Note
from aqt import mw
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.utils import getText, showInfo, tooltip

from BeautifulSoup import BeautifulSoup as bs, Tag as bs_tag

from irx.util import getField, setField, db_log, irx_siblings, pretty_date, timestamp_id


class TextManager:
    def __init__(self, settings):
        self.settings = settings
        self.history_path = join(
            mw.pm.profileFolder(), "collection.media", "_irx_history.pkl"
        )
        if exists(self.history_path):
            self.history = pickle.load(open(self.history_path, "rb"))
        else:
            self.history = defaultdict(list)

    def format(self, style):
        mw.web.eval('format("%s")' % style)
        self.save()

    def linkNote(self, note, extract_type=""):
        mw.web.eval('linkToNote("%s", "%s")' % (note.id, extract_type))
        self.save(note_linked=note)

    def toggle_images_sidebar(self, manual=None):
        mw.web.eval('toggleImagesSidebar("%s")' % (manual or "toggle"))
        mw.reviewer.card.note().flush()

    def toggle_show_removed(self, manual=None):
        mw.web.eval('toggleShowRemoved("%s")' % (manual or "toggle"))
        mw.reviewer.card.note().flush()

    def toggle_show_formatting(self, manual=None):
        mw.web.eval('toggleShowFormatting("%s")' % (manual or "toggle"))
        mw.reviewer.card.note().flush()

    def toggle_show_extracts(self, manual=None):
        mw.web.eval('toggleShowExtracts("%s")' % (manual or "toggle"))
        mw.reviewer.card.note().flush()

    def manage_images(self, note=None):
        note = note or mw.reviewer.card.note()
        soup = bs(getField(note, self.settings["imagesField"]))
        history = []

        def image_list(soup):
            images = []
            for div in soup.findAll(
                'div', attrs={'class': 'irx-img-container'}
            ):
                images.append(
                    {
                        "id":
                            div.get('id'),
                        "caption":
                            div.findChild(
                                'span', attrs={
                                    "class": "irx-caption"
                                }
                            ).text,
                        "src":
                            div.findChild('img').get('src'),
                        "html":
                            str(div.extract())
                    }
                )
            return images

        images = image_list(soup)
        if not images:
            return

        self.image_list_widget = QListWidget()
        self.image_list_widget.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.image_list_widget.setWordWrap(False)
        self.image_list_widget.setFixedSize(150, 250)

        std_bg = QColor('#ffffff')
        del_bg = QColor('#f0027f')
        sel_bg = QColor('#386cb0')

        def populate_qlist(images, selected=0):
            self.image_list_widget.clear()
            if not images:
                return
            for image in images:
                item = QListWidgetItem("{}".format(image["caption"]))
                item.setData(Qt.UserRole, image)
                item.setBackground(std_bg)
                self.image_list_widget.addItem(item)
            self.image_list_widget.item(max(selected, 0)).setSelected(True)
            self.image_list_widget.update()

        image_label = QLabel()
        image_label.setFixedSize(300, 250)
        image_label.setAlignment(Qt.AlignCenter)

        def update_label(clear=False):
            selected = self.image_list_widget.selectedItems()
            if len(selected) == 1:
                image = selected[0].data(Qt.UserRole)
                image_label.setPixmap(
                    QPixmap(image["src"]).scaled(
                        image_label.maximumWidth(), image_label.maximumHeight(),
                        Qt.KeepAspectRatio
                    )
                )
            else:
                image_label.clear()
            image_label.update()

        def key_handler(evt, _orig):
            key = unicode(evt.text())
            if key == "d":
                for selected in self.image_list_widget.selectedItems():
                    if selected.background() == std_bg:
                        selected.setBackground(del_bg)
                    elif selected.background() == del_bg:
                        selected.setBackground(std_bg)
                self.image_list_widget.update()
            elif key == "e":
                selected = self.image_list_widget.selectedItems()
                if selected and len(selected) == 1:
                    selected_image = selected[0].data(Qt.UserRole)
                    new_caption, _ = getText(
                        "Edit image caption:",
                        default=selected_image["caption"]
                    )
                    if new_caption:
                        selected[0].setText(new_caption)
                        selected_image["caption"] = new_caption
                        selected[0].setData(Qt.UserRole, selected_image)
                        self.image_list_widget.update()
                else:
                    showInfo("Can only edit 1 image at a time")
            elif key == "t":
                for selected in self.image_list_widget.selectedItems():
                    if selected.background() == std_bg:
                        selected.setBackground(sel_bg)
                    elif selected.background() == sel_bg:
                        selected.setBackground(std_bg)
            elif key in ["a", "b"]:
                take_items = []
                row_offset = 1 if key == "b" else 0
                for i in range(self.image_list_widget.count()):
                    if self.image_list_widget.item(i).background() == sel_bg:
                        self.image_list_widget.item(i).setBackground(std_bg)
                        take_items.append(self.image_list_widget.item(i))
                if take_items:
                    for item in take_items:
                        self.image_list_widget.takeItem(
                            self.image_list_widget.row(item)
                        )
                    for item in take_items[::-1]:
                        self.image_list_widget.insertItem(
                            self.image_list_widget.currentRow() + row_offset,
                            item
                        )
                    self.image_list_widget.update()
            else:
                return _orig(evt)

        self.image_list_widget.itemSelectionChanged.connect(update_label)
        orig_handler = self.image_list_widget.keyPressEvent
        self.image_list_widget.keyPressEvent = lambda evt: key_handler(evt, orig_handler)
        populate_qlist(images)
        update_label()

        dialog = QDialog(mw)
        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(image_label)
        layout.addWidget(self.image_list_widget)
        dialog.setLayout(layout)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setFixedSize(500, 300)

        def submit_changes(evt, _orig):
            if evt.key() in [Qt.Key_Return, Qt.Key_Enter]:
                dialog.accept()
            else:
                return _orig(evt)

        orig_dialog_handler = dialog.keyPressEvent
        dialog.keyPressEvent = lambda evt: submit_changes(evt, orig_dialog_handler)
        res = dialog.exec_()

        if res == 1:
            self.save()
            images = [
                "<div class='irx-img-container' id='{id}'><br/><a href='{src}'><img src='{src}'><span class='irx-caption'>{caption}</span></a></div>"
                .format(
                    id=image["id"], src=image["src"], caption=image["caption"]
                ) for image in [
                    self.image_list_widget.item(index).data(Qt.UserRole)
                    for index in range(self.image_list_widget.count())
                    if self.image_list_widget.item(index).background() != del_bg
                ]
            ]
            setField(note, self.settings["imagesField"], "".join(images))
            note.flush()
            mw.reset()

    def extract(self, also_edit=False, schedule_extract=None):
        if not mw.web.selectedText():
            showInfo("Please select some text to extract.")
            return

        current_card = mw.reviewer.card
        current_note = current_card.note()
        model = mw.col.models.byName(self.settings["modelName"])

        new_note = Note(mw.col, model)
        new_note.tags = current_note.tags

        mw.web.triggerPageAction(QWebPage.Copy)
        mime_data = QApplication.clipboard().mimeData()
        if self.settings["plainText"]:
            text = mime_data.text()
        else:
            text = mime_data.html()
            media_paths = re.findall(r"src=\"([^\"]+)", text)
            for path in media_paths:
                media_name = normpath(basename(path))
                text = text.replace(path, media_name)

        setField(new_note, self.settings["textField"], text)
        setField(
            new_note, self.settings["imagesField"],
            getField(current_note, self.settings["imagesField"])
        )
        setField(
            new_note, self.settings["sourceField"],
            getField(current_note, self.settings["sourceField"])
        )
        setField(
            new_note, self.settings["parentField"],
            getField(current_note, self.settings["titleField"])
        )
        setField(
            new_note, self.settings["pidField"],
            "irxnid:{}".format(current_note.id)
        )
        setField(
            new_note, self.settings["linkField"],
            getField(current_note, self.settings["linkField"])
        )
        setField(new_note, self.settings["dateField"], pretty_date())

        if self.settings["editSource"]:
            EditCurrent(mw)

        if self.settings["extractDeck"]:
            did = mw.col.decks.byName(self.settings["extractDeck"])["id"]
        else:
            did = current_card.did

        if self.settings["editExtract"] or also_edit:
            highlight = self._editExtract(
                new_note, did, self.settings["modelName"]
            )
        else:
            setField(
                new_note, self.settings["titleField"],
                self.next_version_number(current_note)
            )
            highlight = True

        if highlight:
            new_note.model()["did"] = did
            mw.col.addNote(new_note)
            if schedule_extract:
                cards = new_note.cards()
                if cards:
                    mw.readingManager.scheduler.answer(
                        cards[0], schedule_extract, from_extract=True
                    )
            if schedule_extract == 1:
                self.linkNote(new_note, "soon")
            elif schedule_extract == 2:
                self.linkNote(new_note, "later")

    def next_version_number(self, parent_note):
        parent_version = re.match(
            r"(^[0-9\.]+)", getField(parent_note, self.settings["titleField"])
        )
        if parent_version:
            parent_version = parent_version.group()
        else:
            parent_version = "1."
        siblings = irx_siblings(parent_note)
        sibling_count = len(siblings)
        next_version = sibling_count + 1
        version_ok = False
        while not (version_ok):
            candidate_version = "{0}{1}.".format(
                parent_version, str(next_version)
            )
            sibling_versions = [
                getField(sibling,
                         self.settings["titleField"])[:len(candidate_version)]
                for sibling in siblings
            ]
            version_ok = candidate_version not in sibling_versions
            if version_ok:
                return candidate_version
            next_version += 1

    def extract_image(self, remove_src=False, skip_captions=False):
        if mw.web.selectedText() and remove_src:
            mw.web.triggerPageAction(QWebPage.Copy)
            self.remove()
        if mw.web.selectedText():
            mw.web.triggerPageAction(QWebPage.Copy)
        else:
            remove_src = False

        mime_data = QApplication.clipboard().mimeData()

        image = mime_data.imageData()
        if not image:
            images = []
            soup = bs(mime_data.html())
            for media_path in [img.get('src') for img in soup.findAll('img')]:
                try:
                    img_data = urllib2.urlopen(media_path).read()
                except ValueError:
                    try:
                        if media_path[:2] == "//":
                            media_path = "http:" + media_path
                        else:
                            media_path = "http://" + media_path
                        img_data = urllib2.urlopen(media_path).read()
                    except urllib2.URLError as url_exception:
                        tooltip(
                            "There was a problem getting {}:\n {}".format(
                                media_path, url_exception
                            )
                        )
                        continue
                images.append(img_data)
            if not images:
                showInfo("Could not find any images to extract")
                return
        else:
            images = [image]

        texts = [t for t in mime_data.text().split("\n") if t]
        images_templ = ""
        for index, image in enumerate(images):
            if not skip_captions:
                try:
                    caption, ret = getText(
                        "Add a caption for the image",
                        title="Extract Image",
                        default=texts[index]
                    )
                except IndexError:
                    caption, ret = getText(
                        "Add a caption for the image",
                        title="Extract Image",
                        default=pretty_date()
                    )
            else:
                caption = pretty_date()
            if ret == 1:
                media = mw.col.media
                filename = media.stripIllegal(caption[:50])
                while exists(join(media.dir(), filename)):
                    filename += "_1"
                try:
                    media.writeData(filename, image)
                except TypeError:
                    buf = QBuffer()
                    buf.open(QBuffer.ReadWrite)
                    filename += ".png"
                    image.save(buf, "PNG", quality=65)
                    media.writeData(filename, buf.data())
                images_templ += "<div class='irx-img-container' id='{id}'><br/><a href='{src}'><img src='{src}'><span class='irx-caption'>{caption}</span></a></div>".format(
                    id=timestamp_id(), src=filename, caption=caption
                )
        if images_templ:
            current_card = mw.reviewer.card
            current_note = current_card.note()

            prev_images_field = getField(
                current_note, self.settings["imagesField"]
            )
            new_images_field = prev_images_field + images_templ

            setField(
                current_note, self.settings["imagesField"], new_images_field
            )
            current_note.flush()
            mw.reset()

    def _editExtract(self, note, did, model_name):
        def on_add():
            add_cards.rejected.disconnect(self.undo)
            add_cards.reject()

        add_cards = AddCards(mw)
        add_cards.rejected.connect(self.undo)
        add_cards.addButton.clicked.connect(on_add)
        add_cards.editor.setNote(note)
        deck_name = mw.col.decks.get(did)["name"]
        if note.stringTags():
            add_cards.editor.tags.setText(note.stringTags().strip())
        add_cards.deckChooser.deck.setText(deck_name)
        add_cards.modelChooser.models.setText(model_name)
        return True

    def remove(self):
        mw.web.eval("removeText()")
        self.save()

    def save(self, note_linked=None):
        current_view = mw.web.page().mainFrame().toHtml()
        soup = bs(current_view)
        text_div = soup.find("div", {"class": "irx-text"})
        images_div = soup.find("div", {"class": "irx-images"})
        if text_div:
            current_note = mw.reviewer.card.note()
            self.history[current_note.id].append(
                {
                    "text": current_note["Text"],
                    "images": current_note["Images"],
                    "action":
                        {
                            "type":
                                "irx-extract",
                            "nid":
                                note_linked.id,
                            "title":
                                getField(
                                    note_linked, self.settings["titleField"]
                                )
                        } if note_linked else {}
                }
            )
            current_note["Text"] = "".join(
                [
                    unicode(c) for c in text_div.contents if
                    not (isinstance(c, bs_tag) and c.get('class') == "irx-sep")
                ]
            )
            images_content = "".join([unicode(c) for c in images_div.contents])
            for src in re.findall(r"src=\"([^\"]+)", images_content):
                images_content = images_content.replace(
                    src, urllib2.unquote(src)
                )
            current_note["Images"] = images_content
            current_note.flush()
            self.write_history()

    def undo(self):
        current_note = mw.reviewer.card.note()
        current_note_title = getField(current_note, "Title")
        history = self.history.get(current_note.id)
        if not history:
            tooltip("No undo history for {}".format(current_note_title))
            return

        msg = "Undone"
        save_data = self.history[current_note.id].pop()
        self.write_history()
        action = save_data.get("action")
        if action and action["type"] == "irx-extract":
            extract_nid = action["nid"]
            try:
                extract = mw.col.getNote(extract_nid)
                extract_title = getField(extract, self.settings["titleField"])
                mw.col.remNotes([extract_nid])
                mw.readingManager.scheduler.update_organizer()
                msg += "<br/> Deleted note: {}".format(extract_title)
            except TypeError:
                msg += "<br/> Linked note [{}] no longer exists.".format(
                    action["title"]
                )
        current_note["Text"] = save_data["text"]
        current_note["Images"] = save_data["images"]
        current_note.flush()
        mw.reset(guiOnly=True)
        tooltip(msg)

    def write_history(self):
        pickle.dump(
            self.history, open(self.history_path, "wb"), pickle.HIGHEST_PROTOCOL
        )
