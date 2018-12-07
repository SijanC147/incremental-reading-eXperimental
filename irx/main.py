# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re
from os import environ

from PyQt4.QtCore import QObject, pyqtSlot, Qt
from PyQt4.QtGui import QApplication
from PyQt4.QtWebKit import QWebPage

from anki import notes
from anki.hooks import addHook, wrap
from anki.sound import clearAudioQueue
from aqt import mw, dialogs
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.reviewer import Reviewer
from aqt.utils import showWarning, tooltip, showInfo

from BeautifulSoup import BeautifulSoup

from irx.about import showAbout
from irx.settings import SettingsManager
from irx.schedule import Scheduler
from irx.text import TextManager
from irx.util import (
    addMenuItem, addShortcut, disableOutdated, getField, isIrxCard, setField,
    viewingIrxText, loadFile, db_log
)
from irx.view import ViewManager


class ReadingManager:
    def __init__(self):
        self.controlsLoaded = False
        self.quickKeyActions = []

        addHook("profileLoaded", self.onProfileLoaded)
        addHook("reset", self.restoreView)
        addHook("showQuestion", self.restoreView)

    def onProfileLoaded(self):
        self.settingsManager = SettingsManager()
        self.settings = self.settingsManager.settings
        self.scheduler = Scheduler(self.settings)
        self.textManager = TextManager(self.settings)
        mw.viewManager = ViewManager()
        mw.viewManager.settings = self.settings

        if not mw.col.models.byName(self.settings["modelName"]):
            self.setupIrxModel()

        disableOutdated()

        if not self.controlsLoaded:
            addMenuItem("IRX", "Settings", self.settingsManager.showDialog)
            addMenuItem("IRX", "Help", self.settingsManager.show_help)
            addMenuItem("IRX", "About", showAbout)
            for keys, action in self.settings["irx_controls"].items():
                if len(keys) > 1 and keys.find("+") >= 0:
                    addShortcut(action, keys)
            self.controlsLoaded = True

        mw.viewManager.resetZoom("deckBrowser")

    def load_developer_tools(self):
        if environ.get("IRX_DEV"):
            addMenuItem("IRX", "Update Model", self.setupIrxModel)

    def setupIrxModel(self):
        model = mw.col.models.new(self.settings["modelName"])
        for key, value in self.settings.items():
            if key[-5:] == "Field":
                mw.col.models.addField(model, mw.col.models.newField(value))
        model["css"] = loadFile('web', 'model.css')
        template = self.makeTemplate(
            name="IRX Card",
            question=loadFile("web", "question.html"),
            answer=loadFile("web", "answer.html")
        )
        mw.col.models.addTemplate(model, template)
        mw.col.models.add(model)

    def makeTemplate(self, name, question, answer):
        template = mw.col.models.newTemplate(name)
        try:
            for field in re.findall(r"\{\{([^\s]+?)\}\}", question):
                question = question.replace(
                    "{{%s}}" % field, "{{%s}}" % self.settings[field + "Field"],
                    1
                )
        except KeyError as e:
            raise KeyError(
                "The question template contains an invalid key: {}".format(e)
            )
        try:
            for field in re.findall(r"\{\{([^\s]+?)\}\}", answer):
                answer = answer.replace(
                    "{{%s}}" % field, "{{%s}}" % self.settings[field + "Field"],
                    1
                )
        except KeyError as e:
            raise KeyError(
                "The answer template contains an invalid key: {}".format(e)
            )
        template["qfmt"] = question
        template["afmt"] = answer
        return template

    def restoreView(self):
        if viewingIrxText():
            cid = str(mw.reviewer.card.id)
            if cid not in self.settings["zoom"]:
                self.settings["zoom"][cid] = 1

            if cid not in self.settings["scroll"]:
                self.settings["scroll"][cid] = 0

            mw.viewManager.setZoom()
            mw.viewManager.setScroll()
            self.restoreHighlighting()

    def restoreHighlighting(self):
        mw.web.page().mainFrame().addToJavaScriptWindowObject(
            "pyCallback", IREJavaScriptCallback()
        )
        initJavaScript()
        mw.web.eval("restoreHighlighting()")

    def htmlUpdated(self):
        curNote = mw.reviewer.card.note()
        curNote["Text"] = mw.web.page().mainFrame().toHtml()
        curNote.flush()
        mw.web.setHtml(curNote["Text"])
        self.restoreView()

    def quickAdd(self, quickKey):
        if not viewingIrxText():
            return

        hasSelection = False
        selectedText = ""
        self.textManager.toggle_show_removed("no")

        if len(mw.web.selectedText()) > 0:
            hasSelection = True
            mw.web.triggerPageAction(QWebPage.Copy)
            clipboard = QApplication.clipboard()
            mimeData = clipboard.mimeData()
            if quickKey["plainText"]:
                selectedText = mimeData.text()
            else:
                selectedText = mimeData.html()

        # Create new note with selected model and deck
        newModel = mw.col.models.byName(quickKey["modelName"])
        newNote = notes.Note(mw.col, newModel)
        setField(newNote, quickKey["fieldName"], selectedText)

        card = mw.reviewer.card
        currentNote = card.note()
        tags = currentNote.stringTags()
        # Sets tags for the note, but still have to set them in the editor
        #   if show dialog (see below)
        newNote.setTagsFromStr(tags)

        for f in newModel["flds"]:
            if self.settings["sourceField"] == f["name"]:
                setField(
                    newNote,
                    self.settings["sourceField"],
                    getField(currentNote, self.settings["sourceField"]),
                )

        # Sean: Added intelligen way to mirror the deck from IR to non IR
        intelli_deck_name = (
            mw.col.decks.get(card.did
                            )["name"].replace("Incremental Reading::", "")
            if quickKey["deckName"] == "[Mirror]" else quickKey["deckName"]
        )
        deckId = mw.col.decks.byName(intelli_deck_name)
        if not deckId:
            try:
                mw.requireReset()
                mw.col.decks.id(intelli_deck_name)
            finally:
                if mw.col:
                    mw.maybeReset()

        # Sean: Replace all instances of the quickKey["deckName"] with intelli_deck_name
        if quickKey["editExtract"]:
            link_to_note = self.textManager._editExtract(
                newNote, deckId, quickKey["modelName"]
            )
        elif hasSelection:
            deckId = mw.col.decks.byName(intelli_deck_name)["id"]
            newNote.model()["did"] = deckId
            ret = newNote.dupeOrEmpty()
            if ret == 1:
                showWarning(
                    _("The first field is empty."), help="AddItems#AddError"
                )
                return
            cards = mw.col.addNote(newNote)
            if not cards:
                showWarning(
                    _(
                        """\
                    The input you have provided would make an empty \
                    question on all cards."""
                    ),
                    help="AddItems",
                )
                return
            link_to_note = True

            clearAudioQueue()
            mw.col.autosave()
            tooltip(_("Added"))

        if link_to_note:
            self.textManager.linkNote(newNote.id)

        if quickKey["editSource"]:
            EditCurrent(mw)


class IREJavaScriptCallback(QObject):
    @pyqtSlot(str)
    def htmlUpdated(self, context):
        mw.readingManager.htmlUpdated()


def initJavaScript():
    js = loadFile('web', 'model.js')
    mw.web.eval(js)


def answerButtonList(self, _old):
    current_card = self.card
    if isIrxCard(current_card):
        page_bottom = mw.web.page().mainFrame().scrollBarMaximum(Qt.Vertical)
        card_pos = mw.readingManager.settings['scroll'][str(current_card.id)]
        answers_button_list = (
            (1, "<font color='red'>" + _("Soon") + "</font>"),
            (2, "<font color='green'>" + _("Later") + "</font>"),
            # (3, "<font color='blue'>" + _("Custom") + "</font>"),
        )
        if page_bottom == card_pos or page_bottom == 0:
            answers_button_list += (
                (5, "<font color='purple'>" + _("Done") + "</font>"),
            )
        return answers_button_list
    else:
        return _old(self)


def answerCard(self, ease, _old):
    card = self.card
    _old(self, ease)
    if isIrxCard(card):
        mw.readingManager.scheduler.answer(card, ease)


def buttonTime(self, i, _old):
    return "<div class=spacer></div>" if isIrxCard(self.card) else _old(self, i)


def LinkHandler(self, evt, _old):
    handled = False
    if viewingIrxText() and evt[:7] == "irxnid:":
        note_id = evt[7:]
        try:
            previous_card = self.card
            note = mw.col.getNote(note_id)
            mw.reviewer.card = note.cards()[0]
            editing = mw.onEditCurrent()
            self.card = previous_card
        except:
            tooltip("Could not find note, possibly deleted.")
        finally:
            handled = True

    return handled or _old(self, evt)


def keyHandler(self, evt, _old):
    handled = False
    if viewingIrxText():
        special_keys = {
            "up": Qt.Key_Up,
            "down": Qt.Key_Down,
            "left": Qt.Key_Left,
            "right": Qt.Key_Right,
            "enter": Qt.Key_Enter,
            "return": Qt.Key_Return,
            "esc": Qt.Key_Escape,
            "pgup": Qt.Key_PageUp,
            "pgdown": Qt.Key_PageDown,
            "home": Qt.Key_Home,
            "end": Qt.Key_End,
            "tab": Qt.Key_Tab
        }
        custom_hotkeys = {}
        for key, val in mw.readingManager.settings["irx_controls"].items():
            if len(key) == 1:
                custom_hotkeys[key] = val
            elif key in special_keys.keys():
                custom_hotkeys[special_keys[key.lower()]] = val

        key = unicode(evt.text())
        if key in custom_hotkeys.keys():
            custom_hotkeys[key]()
            handled = True
        elif evt.key() in custom_hotkeys.keys():
            custom_hotkeys[evt.key()]()
            handled = True

    return handled or _old(self, evt)


def defaultEase(self, _old):
    current_card = self.card
    if isIrxCard(current_card):
        page_bottom = mw.web.page().mainFrame().scrollBarMaximum(Qt.Vertical)
        card_pos = mw.readingManager.settings['scroll'][str(current_card.id)]
        return 5 if page_bottom == card_pos or page_bottom == 0 else 2
    return _old(self)


Reviewer._answerButtonList = wrap(
    Reviewer._answerButtonList, answerButtonList, "around"
)
Reviewer._answerCard = wrap(Reviewer._answerCard, answerCard, "around")
Reviewer._buttonTime = wrap(Reviewer._buttonTime, buttonTime, "around")
Reviewer._linkHandler = wrap(Reviewer._linkHandler, LinkHandler, "around")
Reviewer._keyHandler = wrap(Reviewer._keyHandler, keyHandler, 'around')
Reviewer._defaultEase = wrap(Reviewer._defaultEase, defaultEase, "around")