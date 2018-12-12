# -*- coding: utf-8 -*-
# pylint: disable=W0212
from __future__ import unicode_literals

import re

from PyQt4.QtCore import QObject, pyqtSlot, Qt
from PyQt4.QtGui import QApplication, QShortcut, QKeySequence
from PyQt4.QtWebKit import QWebPage

from anki import notes
from anki.hooks import addHook, wrap, remHook
from anki.sound import clearAudioQueue
from aqt import mw, dialogs
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.reviewer import Reviewer
from aqt.overview import Overview
from aqt.utils import showWarning, tooltip, showInfo

from BeautifulSoup import BeautifulSoup

from irx.about import showAbout
from irx.settings import SettingsManager
from irx.schedule import Scheduler
from irx.text import TextManager
from irx.quick_keys import QuickKeys
from irx.util import (
    addMenuItem, addShortcut, disableOutdated, getField, isIrxCard, setField,
    viewingIrxText, loadFile, db_log
)
from irx.view import ViewManager


class ReadingManager:
    def __init__(self):
        self.controlsLoaded = False
        self.quickKeyActions = []
        self.irx_specific_shortcuts = []

        addHook("profileLoaded", self.onProfileLoaded)
        addHook("reset", self.restore_view)
        addHook("showQuestion", self.restore_view)
        addHook("reviewCleanup", lambda: self.toggle_irx_controls(False))

    def onProfileLoaded(self):
        self.settingsManager = SettingsManager()
        self.settings = self.settingsManager.settings
        self.scheduler = Scheduler(self.settings)
        self.textManager = TextManager(self.settings)
        self.quickKeys = QuickKeys(self.settings)
        mw.viewManager = ViewManager(self.settings)

        if not mw.col.models.byName(self.settings["modelName"]):
            self.setup_irx_model()

        disableOutdated()

        if not self.controlsLoaded:
            addMenuItem("IR3X", "Settings", self.settingsManager.show_settings)
            addMenuItem(
                "IR3X::Quick Keys", "Manage", self.quickKeys.show_dialog
            )
            addMenuItem("IR3X::Dev", "Organizer", self.scheduler.show_organizer)
            addMenuItem("IR3X::Dev", "Update Model", self.setup_irx_model)
            addMenuItem("IR3X", "Help", self.settingsManager.show_help)
            addMenuItem("IR3X", "About", showAbout)
            self.setup_irx_controls()
            self.controlsLoaded = True

        self.quickKeys.refresh_menu_items()
        mw.viewManager.resetZoom("deckBrowser")
        self.monkey_patch_other_addons()

    def setup_irx_controls(self):
        for key_seq, action in self.settings["irx_controls"].items():
            if len(key_seq) > 1 and key_seq.find("+") > 0:
                shortcut = addShortcut(action, key_seq)
                self.irx_specific_shortcuts.append(shortcut)
        self.controls_state = False
        self.space_scroll = QShortcut(QKeySequence("space"), mw)
        self.space_scroll.activated.connect(lambda: mw.viewManager.pageDown())
        self.space_scroll.setEnabled(False)
        self.toggle_irx_controls(self.controls_state, notify=False)

    def next_irx_card(self):
        if viewingIrxText():
            if mw.reviewer.state == "question":
                mw.reviewer._showAnswerHack()
            elif mw.reviewer.state == "answer":
                mw.reviewer._answerCard(mw.reviewer._defaultEase())

    def toggle_irx_controls(self, state=None, notify=True):
        for irx_shortcut in self.irx_specific_shortcuts:
            irx_shortcut.setEnabled(state or not irx_shortcut.isEnabled())
        if notify and state != self.controls_state:
            tooltip(
                "<b>IR3X {}</b>".format(
                    "<font color='green'>ON</font>"
                    if state else "<font color='red'>OFF</font>"
                )
            )
        self.controls_state = state

    def toggle_space_scroll(self, state=None):
        self.space_scroll.setEnabled(state or not self.space_scroll.isEnabled())

    def monkey_patch_other_addons(self):
        Reviewer._answerButtonList = wrap(
            Reviewer._answerButtonList, answerButtonList, "around"
        )
        try:
            _dogs = mw.dogs
        except AttributeError:
            _dogs = None

        try:
            import Progress_Bar
            _pb = Progress_Bar._updatePB
        except ImportError:
            _pb = None

        original_undo = mw.readingManager.textManager.undo

        def patched_undo(show_tooltip):
            if _pb:
                remHook("showQuestion", _pb)
            original_undo(show_tooltip)
            if _dogs:
                mw.dogs["cnt"] -= 1
            if _pb:
                addHook("showQuestion", _pb)

        mw.readingManager.textManager.undo = lambda show_tooltip=True: patched_undo(show_tooltip)

    def setup_irx_model(self):
        model = mw.col.models.new(self.settings["modelName"])
        for key, value in self.settings.items():
            if key[-5:] == "Field":
                mw.col.models.addField(model, mw.col.models.newField(value))
        model["css"] = loadFile('web', 'model.css')
        template = self.make_irx_template(
            name="IRX Card",
            question=loadFile("web", "question.html"),
            answer=loadFile("web", "answer.html")
        )
        mw.col.models.addTemplate(model, template)
        mw.col.models.add(model)

    def make_irx_template(self, name, question, answer):
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

    def restore_view(self):
        if viewingIrxText():
            self.toggle_irx_controls(True)
            self.toggle_space_scroll(True)
            cid = str(mw.reviewer.card.id)
            if cid not in self.settings["zoom"]:
                self.settings["zoom"][cid] = 1

            if cid not in self.settings["scroll"]:
                self.settings["scroll"][cid] = 0

            mw.viewManager.setZoom()
            mw.viewManager.setScroll()
            self.init_javascript()
            note = mw.reviewer.card.note()
            note_images = getField(note, self.settings["imagesField"])
            if not note_images:
                mw.web.eval('toggleImagesSidebar(false);')
            page_bottom = mw.web.page().mainFrame().scrollBarMaximum(
                Qt.Vertical
            )
            card_pos = self.settings['scroll'][str(cid)]
            if page_bottom == card_pos or page_bottom == 0:
                self.toggle_space_scroll(False)

    def init_javascript(self):
        mw.web.page().mainFrame().addToJavaScriptWindowObject(
            "pyCallback", IREJavaScriptCallback()
        )
        mw.web.eval(loadFile('web', 'model.js'))

    def htmlUpdated(self):
        current_note = mw.reviewer.card.note()
        current_note["Text"] = mw.web.page().mainFrame().toHtml()
        current_note.flush()
        mw.web.setHtml(current_note["Text"])
        self.restore_view()

    def quick_add(self, quick_key):
        if not viewingIrxText() and mw.web.selectedText():
            return

        if mw.web.selectedText():
            mw.web.triggerPageAction(QWebPage.Copy)
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            if quick_key["plainText"]:
                selected_text = mime_data.text()
            else:
                selected_text = mime_data.html()

        current_card = mw.reviewer.card
        current_note = current_card.note()
        model = mw.col.models.byName(quick_key["modelName"])
        new_note = notes.Note(mw.col, model)
        for field in [f['name'] for f in model['flds']]:
            target_field_text = quick_key["fields"].get(field)
            if target_field_text:
                templ_vals = re.findall(r"\{\{([^\s]+?)\}\}", target_field_text)
                for target_field in templ_vals:
                    replacement = selected_text if target_field.lower(
                    ) == "text" else getField(current_note, target_field)
                    target_field_text = target_field_text.replace(
                        "{{%s}}" % target_field, replacement, 1
                    )
            setField(new_note, field, target_field_text)

        new_note.setTagsFromStr(current_note.stringTags())

        deck_name = (
            mw.col.decks.get(current_card.did
                            )["name"].replace("Incremental Reading::", "")
            if quick_key["deckName"] == "[Mirror]" else quick_key["deckName"]
        )
        target_deck = mw.col.decks.byName(deck_name)
        if not target_deck:
            try:
                mw.requireReset()
                mw.col.decks.id(deck_name)
            finally:
                if mw.col:
                    mw.maybeReset()
            target_deck = mw.col.decks.byName(deck_name)

        link_to_note = self.textManager._editExtract(
            new_note, target_deck["id"], quick_key["modelName"]
        ) if quick_key["editExtract"] else True

        if link_to_note:
            new_note.model()["did"] = mw.col.decks.byName(deck_name)["id"]
            ret = new_note.dupeOrEmpty()
            if ret == 1:
                showWarning(
                    _("The first field is empty."), help="AddItems#AddError"
                )
                return
            cards = mw.col.addNote(new_note)
            if not cards:
                showWarning(
                    _(
                        "The input you have provided would make an empty question on all cards."
                    ),
                    help="AddItems",
                )
                return
            self.textManager.linkNote(new_note, "card")
            clearAudioQueue()
            mw.col.autosave()

        if quick_key["editSource"]:
            EditCurrent(mw)


class IREJavaScriptCallback(QObject):
    @pyqtSlot(str)
    def htmlUpdated(self, context):
        mw.readingManager.htmlUpdated()


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
        self._irx_answer_flag = False
        if page_bottom == card_pos or page_bottom == 0:
            answers_button_list += (
                (5, "<font color='purple'>" + _("Done") + "</font>"),
            )
            self._irx_answer_flag = True
        return answers_button_list
    else:
        return _old(self)


def answerCard(self, ease, _old):
    card = self.card
    if isIrxCard(card):
        if self._irx_answer_flag:
            ease = ease if ease in (1, 2) else 5
        else:
            ease = min(ease, 2)
        _old(self, ease)
        mw.readingManager.scheduler.answer(card, ease)
    else:
        _old(self, ease)


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
    irx_action = {
        k.lower(): v
        for k, v in mw.readingManager.settings["irx_controls"].items()
        if len(k) == 1
    }.get(unicode(evt.text()).lower()) if viewingIrxText() else False
    if irx_action:
        irx_action()
    return bool(irx_action) or _old(self, evt)


def defaultEase(self, _old):
    current_card = self.card
    if isIrxCard(current_card):
        page_bottom = mw.web.page().mainFrame().scrollBarMaximum(Qt.Vertical)
        card_pos = mw.readingManager.settings['scroll'][str(current_card.id)]
        return 5 if page_bottom == card_pos or page_bottom == 0 else 2
    return _old(self)


Reviewer._answerCard = wrap(Reviewer._answerCard, answerCard, "around")
Reviewer._buttonTime = wrap(Reviewer._buttonTime, buttonTime, "around")
Reviewer._linkHandler = wrap(Reviewer._linkHandler, LinkHandler, "around")
Reviewer._keyHandler = wrap(Reviewer._keyHandler, keyHandler, 'around')
Reviewer._defaultEase = wrap(Reviewer._defaultEase, defaultEase, "around")
