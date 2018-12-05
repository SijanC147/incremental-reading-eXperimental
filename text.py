from __future__ import unicode_literals
from collections import defaultdict
import urllib2
import re
import time
from io import BytesIO
import base64
from datetime import datetime
from os.path import normpath, basename, join, exists
import cPickle as pickle

from PyQt4.QtGui import QApplication, QImage
from PyQt4.QtWebKit import QWebPage
from PyQt4.QtCore import QBuffer

from anki.notes import Note
from aqt import mw
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.utils import getText, showInfo, tooltip

from BeautifulSoup import BeautifulSoup


from irx.util import getField, setField, db_log, irx_siblings


class TextManager:
    def __init__(self, settings):
        self.settings = settings
        self.history_path = join(mw.pm.profileFolder(), "collection.media", "_irx_history.pkl")
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
        mw.web.eval('linkToNote("%s", "%s")'%(note_id, extract_type))
        self.save()

    def extract(self, also_edit=False, schedule_extract=None):
        if not mw.web.selectedText():
            showInfo("Please select some text to extract.")
            return

        currentCard = mw.reviewer.card
        currentNote = currentCard.note()
        model = mw.col.models.byName(self.settings["modelName"])

        newNote = Note(mw.col, model)
        newNote.tags = currentNote.tags

        mw.web.triggerPageAction(QWebPage.Copy)
        mimeData = QApplication.clipboard().mimeData()
        if self.settings["plainText"]:
            text = mimeData.text()
        else:
            text = mimeData.html()
            media_paths = re.findall(r"src=\"([^\"]+)", text)
            for path in media_paths:
                media_name = normpath(basename(path))
                text = text.replace(path, media_name)


        setField(newNote, self.settings["textField"], text)
        setField(newNote, self.settings["sourceField"], getField(currentNote, self.settings["sourceField"]))
        setField(newNote, self.settings["parentField"], getField(currentNote, self.settings["titleField"]))
        setField(newNote, self.settings["pidField"], "irxnid:{}".format(currentNote.id))
        setField(newNote, self.settings["linkField"], getField(currentNote, self.settings["linkField"]))
        setField(newNote, self.settings["dateField"], datetime.now().strftime("%A, %d %B %Y %H:%M"))

        if self.settings["editSource"]:
            EditCurrent(mw)

        if self.settings["extractDeck"]:
            did = mw.col.decks.byName(self.settings["extractDeck"])["id"]
        else:
            did = currentCard.did

        if self.settings["editExtract"] or also_edit:
            highlight = self._editExtract(
                newNote, did, self.settings["modelName"]
            )
        else:
            setField(newNote, self.settings["titleField"], self.next_version_number(currentNote))
            newNote.model()["did"] = did
            mw.col.addNote(newNote)
            highlight = True
            # current_title = getField(currentNote, self.settings["titleField"])
            # current_title_version = re.match(r"(^[0-9\.]+)", current_title)
            # if current_title_version:
            #     current_title_version = current_title_version.group()
            #     extract_title = current_title.replace(
            #         current_title_version,
            #         current_title_version + str(self.children_extracts) + ".",
            #     )
            #     self.children_extracts += 1
            #     setField(newNote, self.settings["titleField"], extract_title)
            #     newNote.model()["did"] = did
            #     mw.col.addNote(newNote)
            # else:
            #     setField(
            #         newNote,
            #         self.settings["titleField"],
            #         str(self.children_extracts)+". "+current_title
            #     )
            #     newNote.model()["did"] = did
            #     mw.col.addNote(newNote)
            # highlight = True

        if highlight:
            if schedule_extract:
                cards = newNote.cards()
                if cards:
                    mw.readingManager.scheduler.answer(cards[0], schedule_extract, from_extract=True)
            if schedule_extract == 1:
                self.linkNote(newNote.id, "soon")
                # self.highlight(custom_key="irx_schedule_soon")
            elif schedule_extract == 2:
                self.linkNote(newNote.id, "later")
                # self.highlight(custom_key="irx_schedule_later")
            # else:
                # self.highlight(custom_key="irx_extract")
            
            self.save(note_linked=newNote)
            
    def next_version_number(self, parent_note):
        parent_version = re.match(r"(^[0-9\.]+)", getField(parent_note, self.settings["titleField"]))
        if parent_version:
            parent_version = parent_version.group()
        else:
            parent_version = "1."
        siblings = irx_siblings(parent_note)
        sibling_count = len(siblings)
        next_version = sibling_count+1
        version_ok = False
        while not(version_ok):
            candidate_version = "{0}{1}.".format(parent_version, str(next_version))
            sibling_versions = [getField(sibling, self.settings["titleField"])[:len(candidate_version)] for sibling in siblings]
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
        
        mimeData = QApplication.clipboard().mimeData()

        image = mimeData.imageData()
        if not image:
            images = []
            text = mimeData.html()
            media_paths = re.findall(r"src=\"([^\"]+)", text)
            for media_path in media_paths:
                img = QImage()
                img.loadFromData(urllib2.urlopen(media_path).read())
                images.append(img)
            if not images:
                showInfo("Could not find any images to extract.")
                return
        else:
            images = [image]
        
        texts = [t for t in mimeData.text().split("\n") if t]
        images_templ = ""
        for index,image in enumerate(images):
            try:
                caption, ret = getText("Add a caption for the image", title="Extract Image", default=texts[index])
            except IndexError:
                caption, ret = getText("Add a caption for the image", title="Extract Image")
            if ret == 1:
                media = mw.col.media
                filename = media.stripIllegal(caption[:50])
                while exists(join(media.dir(), filename)):
                    filename += "_1"
                filename += ".jpg"
                buffer = QBuffer()
                buffer.open(QBuffer.ReadWrite)
                image.save(buffer, "JPG")
                media.writeData(filename, buffer.data())
                images_templ += "<div><br/><img src='{src}'><a href='{src}'>{caption}</a></div>".format(src=filename, caption=caption)
        
        if images_templ:
            current_card = mw.reviewer.card
            current_note = current_card.note()

            prev_images_field = getField(current_note, self.settings["imagesField"])
            new_images_field = prev_images_field + images_templ

            setField(current_note, self.settings["imagesField"], new_images_field)
            current_note.flush()
            mw.reset()


    def _editExtract(self, note, did, model_name):
        def onAdd():
            addCards.rejected.disconnect(self.undo)
            addCards.reject()

        addCards = AddCards(mw)
        addCards.rejected.connect(self.undo)
        addCards.addButton.clicked.connect(onAdd)
        addCards.editor.setNote(note)
        deckName = mw.col.decks.get(did)["name"]
        if note.stringTags():
            addCards.editor.tags.setText(note.stringTags().strip())
        addCards.deckChooser.deck.setText(deckName)
        addCards.modelChooser.models.setText(model_name)
        return True

    def remove(self):
        mw.web.eval("removeText()")
        self.save()

    def save(self, note_linked=None):
        note = mw.reviewer.card.note()
        if note_linked:
            self.history[note.id].append({
                "LINKED NOTE": note_linked.id,
                "TITLE:": getField(note_linked, self.settings["titleField"])
            })
        else:
            def removeOuterDiv(html):
                withoutOpenDiv = re.sub("^<div[^>]+>", "", unicode(html))
                withoutCloseDiv = re.sub("</div>$", "", withoutOpenDiv)
                return withoutCloseDiv

            page = mw.web.page().mainFrame().toHtml()
            soup = BeautifulSoup(page)
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
        if (currentNote.id not in self.history or not self.history[currentNote.id]):
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
                linked_title = last_action.get("TITLE", last_action.get("LINKED NOTE", "?"))
                tooltip_msg += "<br/> Linked note [{}] not found, maybe already deleted?".format(linked_title)
            last_action = self.history[currentNote.id].pop()
        currentNote["Text"] = last_action
        currentNote.flush()
        mw.reset()
        tooltip(tooltip_msg)
        self.write_history()

    def write_history(self):
        pickle.dump(self.history, open(self.history_path, "wb"), pickle.HIGHEST_PROTOCOL)