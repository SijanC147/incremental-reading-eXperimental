# -*- coding: utf-8 -*-

from __future__ import unicode_literals, division
from random import gauss, shuffle

from PyQt4.QtCore import Qt
from PyQt4.QtGui import (
    QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout, QListWidget,
    QTreeView, QStandardItemModel, QStandardItem, QListWidgetItem, QPushButton,
    QVBoxLayout
)

from anki.utils import stripHTML
from aqt import mw
from aqt.utils import showInfo, tooltip
from irx.util import setField, getField, db_log

SCHEDULE_SOON = 1
SCHEDULE_LATER = 2
SCHEDULE_CUSTOM = 3
SCHEDULE_DONE = 5


class Scheduler:
    def __init__(self, settings):
        self.settings = settings
        self.card_tree_widget = QTreeView()
        self.card_tree_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.card_tree_widget.setUniformRowHeights(True)
        self.card_tree_model = QStandardItemModel()

    def populate_organizer(self, cards_info):
        self.card_tree_model.setHorizontalHeaderLabels(
            [
                'ID', 'Position', 'Type', 'Queue', 'Title', 'Due', 'Interval',
                'Reps', 'Lapses'
            ]
        )
        self.card_tree_widget.setModel(self.card_tree_model)

        queue_types = {
            "0": "New",
            "1": "Learn",
            "2": "Review",
            "3": "Day Learn",
            "-1": "Suspended",
            "-2": "Buried"
        }
        card_types = {
            "0": "Learning",
            "1": "Reviewing",
            "2": "Re-Learning",
            "3": "Cramming",
        }

        for i, card_info in enumerate(cards_info, start=1):
            cid = QStandardItem(str(card_info["id"]))
            cid.setEditable(False)
            pos = QStandardItem("❰ {} ❱".format(i))
            pos.setEditable(False)
            nid = QStandardItem(str(card_info["nid"]))
            nid.setEditable(False)
            ctype = QStandardItem(card_types.get(str(card_info["type"])))
            ctype.setEditable(False)
            queue = QStandardItem(queue_types.get(str(card_info["queue"])))
            queue.setEditable(False)
            due = QStandardItem(str(card_info["due"]))
            due.setEditable(False)
            interval = QStandardItem(str(card_info["interval"]))
            interval.setEditable(False)
            reps = QStandardItem(str(card_info["reps"]))
            reps.setEditable(False)
            lapses = QStandardItem(str(card_info["lapses"]))
            lapses.setEditable(False)
            title = QStandardItem(str(card_info["title"]))
            title.setEditable(False)
            self.card_tree_model.appendRow(
                [cid, pos, ctype, queue, title, due, interval, reps, lapses]
            )

    def update_organizer(self, mark_card=None):
        if self.card_tree_widget.isVisible():
            did = mw._selectedDeck()['id']
            cards_info = self.deck_cards_info(did)
            if not cards_info:
                showInfo('Please select an Incremental Reading deck.')
                return
            else:
                cards_info = self.mark_card_info(cards_info, mark="C")
                if mark_card:
                    cards_info = self.mark_card_info(
                        cards_info, mark="*", card=mark_card
                    )

            self.populate_organizer(cards_info)
            self.card_tree_widget.update()

    def show_organizer(self, current_card=None):
        if current_card:
            did = current_card.did
        elif mw._selectedDeck():
            did = mw._selectedDeck()['id']
        else:
            return

        cards_info = self.deck_cards_info(did)
        if not cards_info:
            showInfo('Please select an Incremental Reading deck.')
            return

        dialog = QDialog(mw)
        layout = QVBoxLayout()
        refresh_button = QPushButton('Update')
        refresh_button.clicked.connect(self.update_organizer)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(refresh_button)

        layout.addLayout(buttons_layout)
        layout.addWidget(self.card_tree_widget)

        dialog.setLayout(layout)
        dialog.resize(1000, 500)
        dialog.show()
        self.update_organizer()

    def answer(self, card, ease, from_extract=False):
        if ease == SCHEDULE_SOON:
            value = self.settings['schedSoonValue']
            randomize = self.settings['schedSoonRandom']
            method = self.settings['schedSoonMethod']
            tooltip_message = "<font color='red'>soon</font>"
            ease_str = " S "
        elif ease == SCHEDULE_LATER:
            value = self.settings['schedLaterValue']
            randomize = self.settings['schedLaterRandom']
            method = self.settings['schedLaterMethod']
            tooltip_message = "<font color='green'>later</font>"
            ease_str = " L "
        elif ease == SCHEDULE_CUSTOM:
            self.reposition(card, 1)
            self.show_organizer(card)
            return
        elif ease == SCHEDULE_DONE:
            self.done_with_note()
            return

        if method == 'percent':
            total_cards = len([c['id'] for c in self.deck_cards_info(card.did)])
            new_position = total_cards * (value / 100)
        elif method == 'count':
            new_position = value

        if randomize:
            new_position = gauss(new_position, new_position / 10)

        card_note = card.note()
        setField(
            card_note, self.settings["titleField"],
            getField(card_note, self.settings["titleField"]) + ease_str
        )
        card_note.flush()

        new_position = max(1, int(new_position))
        self.reposition(card, new_position, from_extract)
        tooltip(
            "Ok, we'll get back to that <b>{}</b><br/><i>moved to position <b>{}</b></i>"
            .format(tooltip_message, new_position)
        )
        self.update_organizer(mark_card=card)

    def done_with_note(self):
        current_card = mw.reviewer.card
        current_note = current_card.note()
        title = getField(current_note, "Title")
        mw.col.sched.suspendCards([c.id for c in current_note.cards()])
        tooltip(
            "<b><font color='purple'>Done</font></b> with <b>{}</b>".
            format(title)
        )
        mw.reset()
        self.update_organizer(mark_card=current_card)

    def reposition(self, card, newPos, from_extract=False):
        cids = [
            c['id'] for c in self.
            deck_cards_info(card.did, suspended=False, buried=False)
        ]
        if from_extract:
            cids = list(set(cids) - set([mw.reviewer.card.id]))
        mw.col.sched.forgetCards(cids)
        cids.remove(card.id)
        new_order = cids[:newPos - 1] + [card.id] + cids[newPos - 1:]
        if from_extract:
            new_order = [mw.reviewer.card.id] + new_order
        mw.col.sched.sortCards(new_order)

    def reorder(self, cids):
        mw.col.sched.forgetCards(cids)
        mw.col.sched.sortCards(cids)

    def mark_card_info(self, cards_info, mark=None, mark_fn=None, card=None):
        mark = "[{}] ".format(mark or "*")
        card = card or mw.reviewer.card
        cond = mark_fn if mark_fn else (lambda c_info: c_info["id"] == card.id)
        for (index, card_info) in enumerate(cards_info):
            if cond(card_info):
                cards_info[index]["title"] = mark + card_info["title"]
        return cards_info

    def deck_cards_info(self, did, suspended=True, buried=True):
        cards_info = []

        query = 'select id, nid, type, queue, due, ivl, reps, lapses from cards where did = ?'

        suspended = "-1" if not suspended else ""
        buried = "-2" if not buried else ""
        if suspended or buried:
            excl = "({})".format(",".join([suspended, buried]))
            query += " and queue not in {}".format(excl)

        for cid, nid, ctype, queue, due, ivl, reps, lapses in mw.col.db.execute(
            query, did
        ):
            note = mw.col.getNote(nid)
            if note.model()['name'] == self.settings['modelName']:
                cards_info.append(
                    {
                        'id': cid,
                        'nid': nid,
                        'type': ctype,
                        'queue': queue,
                        'due': due,
                        'interval': ivl,
                        'reps': reps,
                        'lapses': lapses,
                        'title': note[self.settings['titleField']]
                    }
                )
        return cards_info
