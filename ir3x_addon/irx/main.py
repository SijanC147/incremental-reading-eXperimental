# -*- coding: utf-8 -*-
# pylint: disable=W0212
from __future__ import unicode_literals

import re
import operator
import pickle
import base64
import cgi
from os import listdir, makedirs
from os.path import join, exists, dirname, splitext

from PyQt4.QtCore import QObject, pyqtSlot, Qt
from PyQt4.QtGui import QApplication, QShortcut, QKeySequence
from PyQt4.QtWebKit import QWebPage

from BeautifulSoup import BeautifulSoup

from anki import notes
from anki.hooks import addHook, wrap, remHook
from anki.sound import clearAudioQueue
from anki.exporting import TextNoteExporter
from aqt import mw, dialogs
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.reviewer import Reviewer
from aqt.overview import Overview
from aqt.utils import showWarning, tooltip, showInfo, getSaveFile, getFile

from irx.about import showIrxAbout
from irx.settings import SettingsManager
from irx.schedule import Scheduler
from irx.text import TextManager
from irx.quick_keys import QuickKeys
from irx.util import (
    addMenuItem, addShortcut, disableOutdated, getField, isIrxCard, setField,
    viewingIrxText, loadFile, db_log, add_menu_sep, rgba_remove_alpha,
    irx_file_path, irx_info_box, timestamp_id, report_irx_issue
)
from irx.view import ViewManager


class ReadingManager:
    def __init__(self, reviewer_controls, image_manager_controls):
        self.user_controls_config = {
            "reviewer": reviewer_controls,
            "image_manager": image_manager_controls,
        }
        self.controlsLoaded = False
        self.quickKeyActions = []
        self.schedule_key_actions = []
        self.help_menu_items = []
        self.irx_specific_shortcuts = []
        self.error_pool = ""

        addHook("profileLoaded", self.onProfileLoaded)
        addHook("reset", self.restore_view)
        addHook("showQuestion", self.restore_view)
        addHook("showAnswer", self.first_time_answer_info)
        addHook("reviewCleanup", lambda: self.toggle_irx_controls(False))
        addHook("setupEditorButtons", self.first_time_irx_editor)

    def onProfileLoaded(self):
        self.settingsManager = SettingsManager(self.user_controls_config)
        self.settings = self.settingsManager.settings
        self.scheduler = Scheduler(self.settings)
        self.textManager = TextManager(self.settings, self.user_controls_config)
        self.quickKeys = QuickKeys(self.settings, self.user_controls_config)
        mw.viewManager = ViewManager(self.settings)

        self.copy_missing_files()
        self.load_irx_container_deck()
        self.attach_irx_error_handler()

        if not mw.col.models.byName(self.settings["modelName"]):
            self.setup_irx_model()

        disableOutdated()

        if not self.controlsLoaded:
            addMenuItem("IR3X", "About IR3X", showIrxAbout)
            add_menu_sep("IR3X")
            addMenuItem(
                "IR3X::Quick Keys", "Manage", self.quickKeys.show_dialog
            )
            add_menu_sep("IR3X::Quick Keys")
            addMenuItem(
                "IR3X::Schedules", "Manage",
                self.settingsManager.show_scheduling
            )
            add_menu_sep("IR3X::Schedules")
            addMenuItem(
                "IR3X::Options", "Settings", self.settingsManager.show_settings
            )
            add_menu_sep("IR3X::Options")
            addMenuItem(
                "IR3X::Options", "Show Controls", self.settingsManager.show_controls
            )
            addMenuItem(
                "IR3X::Options", "Clean History",
                lambda: self.textManager.clean_history(notify=True)
            )
            addMenuItem(
                "IR3X::Options", "Report Issue", report_irx_issue)

            if self.settings.get('isDev', False):
                add_menu_sep("IR3X")
                addMenuItem("IR3X::Developer", "Organizer", self.scheduler.show_organizer)
                addMenuItem("IR3X::Developer", "Update Model", self.setup_irx_model)
                addMenuItem("IR3X::Developer", "Export IR3X Note", self.export_irx_note)
                addMenuItem("IR3X::Developer", "Import IR3X Note", self.import_irx_note)
            add_menu_sep("IR3X")
            addMenuItem("IR3X::Help", "Reset All Info Messages",self.settingsManager.reset_info_flags)
            add_menu_sep("IR3X::Help")
            self.setup_irx_controls()
            self.controlsLoaded = True

        self.quickKeys.refresh_menu_items()
        self.settingsManager.refresh_schedule_menu_items()
        self.settingsManager.refresh_help_menu_items()
        self.textManager.clean_history()
        mw.viewManager.resetZoom("deckBrowser")
        self.monkey_patch_other_addons()
        self.create_getting_started_deck()
        irx_info_box('firstTimeOpening')


    def attach_irx_error_handler(self):
        _eh_write = mw.errorHandler.write
        def intercept_err(data, _orig):
            if mw.readingManagerX.settings.get('useIrxErrorHandler', False):
                if not isinstance(data, unicode):
                    data = unicode(data, "utf8", "replace")
                mw.readingManagerX.error_pool += data
            _orig(data)
        mw.errorHandler.write = lambda data, orig=_eh_write: intercept_err(data, orig)

        _eh_oTo = mw.errorHandler.onTimeout
        def catch_err(_orig):
            trace_back = mw.readingManagerX.error_pool
            mw.readingManagerX.error_pool = ""
            if mw.readingManagerX.settings.get('useIrxErrorHandler', False) and trace_back.find("irx") >=0 and trace_back.find("report_irx_issue") < 0:
                mw.errorHandler.pool = ""
                mw.progress.clear()
                report_irx_issue(trace_back)
            else:
                _orig()
        mw.errorHandler.onTimeout = lambda orig=_eh_oTo: catch_err(orig)

    def first_time_answer_info(self):
        if viewingIrxText():
            irx_info_box('firstTimeSeeingAnswers')
    
    def first_time_irx_editor(self, editor):
        if mw.col.models.current()['name'] == self.settings['modelName']:
            irx_info_box("firstTimeInTheEditor", parent=editor.parentWindow)

    def load_irx_container_deck(self):
        prev_container_deck = mw.col.decks.byName(self.settings['prevContainerDeck'])
        container_deck = mw.col.decks.byName(self.settings['containerDeck'])
        problem = False
        if not container_deck and not prev_container_deck:
            try:
                mw.col.decks.id(self.settings['containerDeck'])
                mw.requireReset()
            finally:
                if mw.col:
                    mw.maybeReset()
            container_deck = mw.col.decks.byName(self.settings['containerDeck'])
            if not container_deck:
                problem = True
        elif not container_deck and prev_container_deck:
            try:
                mw.col.decks.rename(prev_container_deck, self.settings['containerDeck'])
                mw.requireReset()
            finally:
                if mw.col:
                    mw.maybeReset()
            container_deck = mw.col.decks.byName(self.settings['containerDeck'])
            if container_deck:
                tooltip("<b>IR3X</b>: Renamed container deck, {} -> {}".format(self.settings['prevContainerDeck'], self.settings['containerDeck']))
            else:
                problem = True
        if problem:
            showWarning("There was a problem setting up the IR3X container Deck, you could create the deck yourself, using the name {}".format(self.settings['containerDeck']))
        else:
            self.settings['prevContainerDeck'] = self.settings['containerDeck']
        return not problem

    def create_getting_started_deck(self):
        if not self.settings['gettingStarted']:
            return
        container_deck = mw.col.decks.byName(self.settings['containerDeck'])
        if not container_deck:
            if not self.load_irx_container_deck():
                return
        container_deck = mw.col.decks.byName(self.settings['containerDeck'])
        getting_started_deck_name = "{0}::Getting Started".format(self.settings['containerDeck'])
        getting_started_deck = mw.col.decks.byName(getting_started_deck_name)
        if not getting_started_deck:
            try:
                mw.col.decks.id(getting_started_deck_name)
                mw.requireReset()
            finally:
                if mw.col:
                    mw.maybeReset()
        getting_started_deck = mw.col.decks.byName(getting_started_deck_name)
        if not getting_started_deck:
            return
        getting_stated_file_path = irx_file_path("_getting_started.irx")
        self.import_irx_note(getting_stated_file_path, getting_started_deck["id"])
        self.settings['gettingStarted'] = False

    def import_irx_note(self, filepath=None, did=None):
        model = mw.col.models.byName(self.settings["modelName"])
        did = did or mw.col.decks.byName(self.settings['containerDeck'])["id"]
        irx_note_file = filepath or getFile(
            parent=mw,
            title="Import IR3X Note",
            cb=None,
            filter="*.irx",
            key="",
        )
        content = pickle.load(open(irx_note_file, "rb"))
        new_note = notes.Note(mw.col, model)
        for key,value in content.items():
            if key != "media":
                setField(new_note, self.settings[key], value or "")
            else:
                for filename, data in value.items():
                    mw.col.media.writeData(unicode(filename), data)
        new_note.model()["did"] = did
        mw.col.addNote(new_note)
        mw.reset()
    
    def export_irx_note(self):
        current_note = mw.reviewer.card.note()
        export = {f:v for f,v in current_note.items()}
        agnostic_export = {}
        irx_fields = {k:v for k,v in self.settings.items() if k[-5:]=="Field"}
        for key in export:
            agnostic_key = [k for k,v in irx_fields.items() if v==key][0]
            agnostic_export[agnostic_key] = export[key]
        
        filenames = mw.col.media.filesInStr(
            mid=current_note.model()["id"],
            string=(agnostic_export["textField"] + agnostic_export["imagesField"]),
        )
        agnostic_export["media"] = {
            str(filename): open(filename, "rb").read() for filename in filenames
        }
        export_filename = "{0}_{1}.irx".format(agnostic_export["titleField"].replace(" ", "_"), timestamp_id())
        export_path = irx_file_path(join("exports", export_filename))
        if not exists(dirname(export_path)):
            makedirs(dirname(export_path))
        target = getSaveFile(
            parent=mw,
            title="Export IR3X Note",
            dir_description=dirname(export_path),
            key="IR3X Note File",
            ext="irx",
            fname=export_filename
        )
        if target:
            pickle.dump(agnostic_export, open(target, "wb"), pickle.HIGHEST_PROTOCOL)
            tooltip("<b>IR3X</b>: Note Exported")

    def copy_missing_files(self):
        for req_file in [f for f in listdir(irx_file_path()) if f.startswith("_irx")]:
            if not exists(join(mw.col.media.dir(), req_file)):
                mw.col.media.writeData(
                    req_file,
                    open(irx_file_path(req_file), "rb").read()
                )

    def setup_irx_controls(self):
        for key_seq, action in self.settings["irx_controls"].items():
            if len(key_seq) > 1 and key_seq.find("+") > 0:
                shortcut = addShortcut(action, key_seq)
                self.irx_specific_shortcuts.append(shortcut)
        self.controls_state = False
        self.space_scroll = QShortcut(QKeySequence("space"), mw)

        def space_scroll_info():
            irx_info_box("spaceBarFunctionIntro")
            mw.viewManager.pageDown()

        self.space_scroll.activated.connect(space_scroll_info)
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
                "<b>IR3X</b>: {}".format(
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

        original_undo = mw.readingManagerX.textManager.undo

        def patched_undo(show_tooltip):
            if _pb:
                remHook("showQuestion", _pb)
            original_undo(show_tooltip)
            if _dogs:
                mw.dogs["cnt"] -= 1
            if _pb:
                addHook("showQuestion", _pb)

        mw.readingManagerX.textManager.undo = lambda show_tooltip=True: patched_undo(show_tooltip)

    def setup_irx_model(self):
        model = mw.col.models.new(self.settings["modelName"])
        irx_fields = [
            "title","text","date","source", "link","parent","pid","images"
        ]
        for irx_field in irx_fields:
            mw.col.models.addField(model, mw.col.models.newField(self.settings[irx_field+"Field"]))
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
                    "{{%s}}" % field, "{{%s}}" % self.settings.get(field.lower() + "Field", self.settings.get(field + "Field")),
                    1
                )
        except KeyError as e:
            raise KeyError(
                "The question template contains an invalid key: {}".format(e)
            )
        try:
            for field in re.findall(r"\{\{([^\s]+?)\}\}", answer):
                answer = answer.replace(
                    "{{%s}}" % field, "{{%s}}" % self.settings.get(field.lower() + "Field", self.settings.get(field + "Field")),
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
            irx_info_box('firstTimeViewingIrxNote')

    def init_javascript(self):
        mw.web.page().mainFrame().addToJavaScriptWindowObject(
            "pyCallback", IREJavaScriptCallback()
        )
        mw.web.eval(loadFile('web', 'model.js'))
        mw.web.eval('setupIrx();')

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
            mw.col.decks.get(current_card.did)["name"].replace("{}::".format(self.settings['containerDeck']), "")
            if quick_key["deckName"] == "[Mirror]" else quick_key["deckName"]
        )
        target_deck = mw.col.decks.byName(deck_name)
        if not target_deck:
            try:
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
            self.textManager.link_note(new_note, bg_col=quick_key['bg'])

        if quick_key["editSource"]:
            EditCurrent(mw)


class IREJavaScriptCallback(QObject):
    @pyqtSlot(str)
    def htmlUpdated(self, context):
        mw.readingManagerX.htmlUpdated()


def answerButtonList(self, _old):
    current_card = self.card
    if isIrxCard(current_card):
        page_bottom = mw.web.page().mainFrame().scrollBarMaximum(Qt.Vertical)
        card_pos = mw.readingManagerX.settings['scroll'][str(current_card.id)]
        answers_button_list = sorted(
            (
                (
                    int(schedule["anskey"]),
                    "<span style='background-color: {bg}; padding: 2px; border-radius: 3px;'>{name}</span>"
                    .format(
                        bg=rgba_remove_alpha(schedule["bg"]),
                        name=_(schedule["name"])
                    )
                )
                for schedule in mw.readingManagerX.settings['schedules'].values()
                if schedule["anskey"]
            ),
            key=operator.itemgetter(0)
        )
        self._irx_answer_flag = False
        if page_bottom == card_pos or page_bottom == 0:
            answers_button_list += (
                (
                    0,
                    "<span style='background-color: #C02F1D; color: #F2F3F4; padding: 2px; border-radius: 3px;'>"
                    + _("Done") + "</span>"
                ),
            )
            self._irx_answer_flag = True
        return answers_button_list
    else:
        return _old(self)


def answerCard(self, ease, _old):
    card = self.card
    if isIrxCard(card):
        active_schedules = list(
            map(
                int,
                mw.readingManagerX.settingsManager.schedule_keys_action_format(
                    action_major=False
                ).keys()
            )
        )
        if self._irx_answer_flag:  # default to done if the done button is available
            ease = ease if ease in active_schedules else 0
        else:  # otherwise default to "easiest" equivalent
            ease = min(active_schedules)
        if ease != 0:
            num_buttons = self.mw.col.sched.answerButtons(self.card)
            irx_norm_ease = [
                round((float(a) / sum(active_schedules)) * num_buttons)
                for a in active_schedules
            ]
            _old(self, irx_norm_ease[active_schedules.index(ease)])
        else:  # 10 will pass Anki's assertion, and is not in IRX answer keys limits (1-9)
            _old(self, 10)
        irx_schedule = mw.readingManagerX.settingsManager.schedule_keys_action_format(
            action_major=False
        ).get(str(ease)) if ease != 0 else "done"
        mw.readingManagerX.scheduler.answer(card, irx_schedule)
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
            mw.onEditCurrent()
            self.card = previous_card
        except:
            tooltip("Could not find note, possibly deleted.")
        finally:
            handled = True

    return handled or _old(self, evt)


def keyHandler(self, evt, _old):
    irx_action = {
        k.lower(): v
        for k, v in mw.readingManagerX.settings["irx_controls"].items()
        if len(k) == 1
    }.get(unicode(evt.text()).lower()) if viewingIrxText() else False
    if irx_action:
        irx_action()
    return bool(irx_action) or _old(self, evt)


def defaultEase(self, _old):
    current_card = self.card
    if isIrxCard(current_card):
        page_bottom = mw.web.page().mainFrame().scrollBarMaximum(Qt.Vertical)
        card_pos = mw.readingManagerX.settings['scroll'][str(current_card.id)]
        return 0 if page_bottom == card_pos or page_bottom == 0 else 2
    return _old(self)


Reviewer._answerCard = wrap(Reviewer._answerCard, answerCard, "around")
Reviewer._buttonTime = wrap(Reviewer._buttonTime, buttonTime, "around")
Reviewer._linkHandler = wrap(Reviewer._linkHandler, LinkHandler, "around")
Reviewer._keyHandler = wrap(Reviewer._keyHandler, keyHandler, 'around')
Reviewer._defaultEase = wrap(Reviewer._defaultEase, defaultEase, "around")
