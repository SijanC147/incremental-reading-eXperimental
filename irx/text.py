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
from irx.lib import imghdr

from PyQt4.QtGui import (
    QApplication, QImage, QAbstractItemView, QDialog, QDialogButtonBox, QPixmap,
    QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QLabel
)
from PyQt4.QtWebKit import QWebPage
from PyQt4.QtCore import Qt, QBuffer

from anki.notes import Note
from aqt import mw
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.utils import getText, showInfo, tooltip

from BeautifulSoup import BeautifulSoup as bs4

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
        # Sean: Added this for autogenerating titles of children
        self.children_extracts = 1

    def highlight(self, bgColor=None, textColor=None, custom_key=None):
        if custom_key:
            bgColor = self.settings["highlight_colors"][custom_key][0]
            textColor = self.settings["highlight_colors"][custom_key][1]
        else:
            if not bgColor:
                bgColor = self.settings["highlightBgColor"]
            if not textColor:
                textColor = self.settings["highlightTextColor"]

        identifier = str(int(time.time() * 10))
        script = "markRange('%s', '%s', '%s');" % (
            identifier,
            bgColor,
            textColor,
        )
        script += "highlight('%s', '%s');" % (bgColor, textColor)
        mw.web.eval(script)
        self.save()

    def format(self, style):
        mw.web.eval('format("%s")' % style)
        self.save()

    def toggleDisplayRemoved(self, manual=None):
        manual = manual or "toggle"
        mw.web.eval('toggleDisplayRemoved("%s")' % manual)

    def toggleOverlay(self):
        mw.web.eval("toggleOverlay()")

    def linkNote(self, note_id, extract_type=""):
        mw.web.eval('linkToNote("%s", "%s")' % (note_id, extract_type))
        self.save()

    def manage_images(self, note=None):
        note = note or mw.reviewer.card.note()
        soup = bs4(getField(note, self.settings["imagesField"]))
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
        self.image_list_widget.setAlternatingRowColors(True)
        self.image_list_widget.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.image_list_widget.setWordWrap(False)
        self.image_list_widget.setFixedSize(150, 250)

        def populate_qlist(images, selected=0):
            self.image_list_widget.clear()
            if not images:
                return
            for image in images:
                text = (image["caption"][:20] + "..."
                       ) if len(image["caption"]) > 20 else image["caption"]
                item = QListWidgetItem("{}".format(text))
                item.setData(Qt.UserRole, image)
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
                selected = self.image_list_widget.selectedItems()
                if selected:
                    removed_item = selected[0].clone()
                    removed_images = [
                        h.data(Qt.UserRole)["id"] for h in history
                    ]
                    selected = [img["id"] for img in images].index(
                        removed_item.data(Qt.UserRole)["id"]
                    ) - 1
                    history.append(removed_item)
                    removed_images.append(removed_item.data(Qt.UserRole)["id"])
                    images_left = [
                        image
                        for image in images if image["id"] not in removed_images
                    ]
                    populate_qlist(images_left, selected=selected)
                    if not images_left:
                        update_label(clear=True)
            elif key == "u":
                if history:
                    last_removed = history.pop()
                    removed_images = [
                        h.data(Qt.UserRole)["id"] for h in history
                    ]
                    images_left = [
                        image
                        for image in images if image["id"] not in removed_images
                    ]
                    selected = [img["id"] for img in images_left].index(
                        last_removed.data(Qt.UserRole)["id"]
                    )
                    populate_qlist(images_left, selected=selected)
            elif key == "e":
                selected = self.image_list_widget.selectedItems()
                if selected:
                    selected_image = selected[0].data(Qt.UserRole)
                    selected_row = self.image_list_widget.row(selected[0])
                    new_caption, _ = getText(
                        "Edit image caption:",
                        default=selected_image["caption"]
                    )
                    if new_caption:
                        for image in images:
                            if image["id"] == selected_image["id"]:
                                image["caption"] = new_caption
                        populate_qlist(images, selected=selected_row)
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
            images = [
                "<div class='irx-img-container' id='{id}'><br/><a href='{src}'><img src='{src}'><span class='irx-caption'>{caption}</span></a></div>"
                .format(
                    id=image["id"], src=image["src"], caption=image["caption"]
                ) for image in [
                    self.image_list_widget.item(index).data(Qt.UserRole)
                    for index in range(self.image_list_widget.count())
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
            new_note.model()["did"] = did
            mw.col.addNote(new_note)
            highlight = True

        if highlight:
            if schedule_extract:
                cards = new_note.cards()
                if cards:
                    mw.readingManager.scheduler.answer(
                        cards[0], schedule_extract, from_extract=True
                    )
            if schedule_extract == 1:
                self.linkNote(new_note.id, "soon")
                # self.highlight(custom_key="irx_schedule_soon")
            elif schedule_extract == 2:
                self.linkNote(new_note.id, "later")
                # self.highlight(custom_key="irx_schedule_later")
            # else:
            # self.highlight(custom_key="irx_extract")

            self.save(note_linked=new_note)

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

    def extract_image(self, remove_src=False):
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
            soup = bs4(mime_data.html())
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
                            "There was a problem getting an {}:\n {}".format(
                                media_path, url_exception
                            )
                        )
                        continue
                img_type = imghdr("", h=img_data)
                if not img_type:
                    tooltip("Could not import {}".format(media_path))
                else:
                    images.append(img_data)
            if not images:
                showInfo("Could not find any images to extract")
                return
        else:
            images = [image]

        texts = [t for t in mime_data.text().split("\n") if t]
        images_templ = ""
        for index, image in enumerate(images):
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
            if ret == 1:
                media = mw.col.media
                filename = media.stripIllegal(caption[:50])
                while exists(join(media.dir(), filename)):
                    filename += "_1"
                try:
                    media.writeData(filename, image.getvalue())
                except AttributeError:
                    buf = QBuffer()
                    buf.open(QBuffer.ReadWrite)
                    filename += ".jpg"
                    image.save(buf, "JPG", quality=100)
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
        note = mw.reviewer.card.note()
        if note_linked:
            self.history[note.id].append(
                {
                    "LINKED NOTE": note_linked.id,
                    "TITLE:":
                        getField(note_linked, self.settings["titleField"])
                }
            )
        else:

            def removeOuterDiv(html):
                withoutOpenDiv = re.sub("^<div[^>]+>", "", unicode(html))
                withoutCloseDiv = re.sub("</div>$", "", withoutOpenDiv)
                return withoutCloseDiv

            page = mw.web.page().mainFrame().toHtml()
            soup = bs4(page)
            irTextDiv = soup.find("div", {"class": "irx-text"})

            if irTextDiv:
                self.history[note.id].append(note["Text"])
                withoutDiv = removeOuterDiv(irTextDiv)
                note["Text"] = unicode(withoutDiv)
                note.flush()
        self.write_history()

    def undo(self):
        currentNote = mw.reviewer.card.note()
        note_title = getField(currentNote, "Title")
        if (
            currentNote.id not in self.history or
            not self.history[currentNote.id]
        ):
            tooltip("No undo history for {}".format(note_title))
            return

        tooltip_msg = "Undone"
        last_action = self.history[currentNote.id].pop()
        if isinstance(last_action, dict):
            linked_nid = last_action["LINKED NOTE"]
            try:
                linked_note = mw.col.getNote(linked_nid)
                linked_title = getField(linked_note, "Title")
                mw.col.remNotes([linked_nid])
                mw.readingManager.scheduler.update_organizer()
                tooltip_msg += "<br/> Deleted note: {}".format(linked_title)
            except TypeError:
                linked_title = last_action.get(
                    "TITLE", last_action.get("LINKED NOTE", "?")
                )
                tooltip_msg += "<br/> Linked note [{}] not found, maybe already deleted?".format(
                    linked_title
                )
            last_action = self.history[currentNote.id].pop()
        currentNote["Text"] = last_action
        currentNote.flush()
        mw.reset()
        tooltip(tooltip_msg)
        self.write_history()

    def write_history(self):
        pickle.dump(
            self.history, open(self.history_path, "wb"), pickle.HIGHEST_PROTOCOL
        )
