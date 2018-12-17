# pylint: disable=W0212
from __future__ import unicode_literals

import re
import operator
from os import listdir
from os.path import join, exists

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
    viewingIrxText, loadFile, db_log, add_menu_sep, rgba_remove_alpha,
    irx_file_path, irx_info_box
)
from irx.view import ViewManager


class ReadingManager:
    def __init__(self):
        self.controlsLoaded = False
        self.quickKeyActions = []
        self.schedule_key_actions = []
        self.irx_specific_shortcuts = []

        addHook("profileLoaded", self.onProfileLoaded)
        addHook("reset", self.restore_view)
        addHook("showQuestion", self.restore_view)
        addHook("reviewCleanup", lambda: self.toggle_irx_controls(False))

    def onProfileLoaded(self):
        self.settingsManager = SettingsManager()
        self.settings = self.settingsManager.settings
        irx_info_box(
            flag_key='firstTimeOpening',
            text="Thank you for trying out IR3X!",
            info_texts=[
                "Seriously, I really appreciate it, you're awesome.",
                "First off, you should find a new deck created (<code><b>{}</b></code>) this should be used to store all your IR3X notes.".format(self.settings['containerDeck']),
                "I've tried to place these information boxes at important parts of the IR3X user experience to explain how it works and how to <i>hopefully</i> get the best results."
                "I highly recommend reading through these boxes at least once when they show up, you can subsequently prevent them from showing up agian.",
                "To avoid skipping an info box by mistake, the default option is set to OK, if you still skip over an info box by mistake, the flags for all info boxes can be reset from the IR3X Options menu.",
                "Check the Help menu for a list of your current control setup (editable through the <code><b>editable_controls.py</b></code> file in the addon folder)",
                "Most of these controls deactivate when you are not viewing IR3X notes in an effort to avoid collisions, a tooltip appears when the IR3X controls toggle on/off",
                "If you're gunning for the most stable experience, I would recommend not being too over-adventurous.",
                "That being said, bug reports help me make this add-on better, which I am intent on doing, so please report any and all of those at the github repo (link in the About menu). I appreciate it!",
                "<b>Also take some time to have a look at the About menu, where I mention the original creators of the IR add-on whose work was the foundation for this add-on.</b>",
                "Thanks again for giving this add-on a shot."
            ],
            parent=mw
        )
        self.scheduler = Scheduler(self.settings)
        self.textManager = TextManager(self.settings)
        self.quickKeys = QuickKeys(self.settings)
        mw.viewManager = ViewManager(self.settings)

        self.copy_missing_files()
        self.load_irx_container_deck()

        if not mw.col.models.byName(self.settings["modelName"]):
            self.setup_irx_model()

        disableOutdated()

        if not self.controlsLoaded:
            addMenuItem("IR3X", "About IR3X", showAbout)
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
                "IR3X::Options", "Clean History",
                lambda: self.textManager.clean_history(notify=True)
            )
            addMenuItem(
                "IR3X::Options", "Reset Info Message Flags",
                lambda: self.settingsManager.reset_info_flags()
            )

            # addMenuItem("IR3X::Dev", "Organizer", self.scheduler.show_organizer)
            # addMenuItem("IR3X::Dev", "Update Model", self.setup_irx_model)
            add_menu_sep("IR3X")
            addMenuItem("IR3X", "Help", self.settingsManager.show_help)
            self.setup_irx_controls()
            self.controlsLoaded = True

        self.quickKeys.refresh_menu_items()
        self.settingsManager.refresh_schedule_menu_items()
        self.textManager.clean_history()
        mw.viewManager.resetZoom("deckBrowser")
        self.monkey_patch_other_addons()

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
            if container_deck:
                tooltip("<b>IR3X</b>: Created container deck, {}".format(self.settings['containerDeck']))
            else:
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

    def copy_missing_files(self):
        for req_file in [f for f in listdir(irx_file_path()) if f[0] == "_"]:
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
            irx_info_box(
                flag_key='firstTimeViewingIrxNote',
                text="Important points to keep in mind.",
                info_texts=[
                    "First off, thank you for trying out this add-on, you're awesome.",
                    "Most text interaction functionality has been relatively stable as long as I stick these pointers:"+
                    "<ul>{}</ul>".format("".join("<li>{}</li>".format(p) for p in [
                        "Try to avoid having individual highlights that span large portions of the text, unless you will not be editing that portion further.",
                        "Avoid having a lot of overlapping highlights/styles as this can cause problems when deciding which highlight/style to take precedence in the HTML.",
                        "If you want to apply styles to highlighted chunks, it's usually better to style the text first, then highlight it.",
                        "I highly recommend you highlight a chunk of text first then click on the link that is generated to edit that extract, instead of using the 'Edit Extract' functionality to skip a click.",
                    ])),
                ],
                parent=mw
            )

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
