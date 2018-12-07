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
        self.cardTreeWidget = QTreeView()
        self.cardTreeWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cardTreeWidget.setUniformRowHeights(True)

    def populate_organizer(self, cardInfo):
        self.cardTreeModel = QStandardItemModel()
        self.cardTreeModel.setHorizontalHeaderLabels(
            [
                'ID', 'Position', 'Type', 'Queue', 'Title', 'Due', 'Interval',
                'Reps', 'Lapses'
            ]
        )
        self.cardTreeWidget.setModel(self.cardTreeModel)

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

        for i, card in enumerate(cardInfo, start=1):
            cid = QStandardItem(str(card["id"]))
            cid.setEditable(False)
            pos = QStandardItem("❰ {} ❱".format(i))
            pos.setEditable(False)
            nid = QStandardItem(str(card["nid"]))
            nid.setEditable(False)
            ctype = QStandardItem(card_types.get(str(card["type"])))
            ctype.setEditable(False)
            queue = QStandardItem(queue_types.get(str(card["queue"])))
            queue.setEditable(False)
            due = QStandardItem(str(card["due"]))
            due.setEditable(False)
            interval = QStandardItem(str(card["interval"]))
            interval.setEditable(False)
            reps = QStandardItem(str(card["reps"]))
            reps.setEditable(False)
            lapses = QStandardItem(str(card["lapses"]))
            lapses.setEditable(False)
            title = QStandardItem(str(card["title"]))
            title.setEditable(False)
            self.cardTreeModel.appendRow(
                [cid, pos, ctype, queue, title, due, interval, reps, lapses]
            )

    def update_organizer(self, mark_card=None):
        if self.cardTreeWidget.isVisible():
            did = mw._selectedDeck()['id']
            card_info = self._getCardInfo(did, mark_card=mark_card)
            if not card_info:
                showInfo('Please select an Incremental Reading deck.')
                return

            self.populate_organizer(card_info)
            self.cardTreeWidget.update()

    def showDialog(self, currentCard=None):
        if currentCard:
            did = currentCard.did
        elif mw._selectedDeck():
            did = mw._selectedDeck()['id']
        else:
            return

        cardInfo = self._getCardInfo(did)
        if not cardInfo:
            showInfo('Please select an Incremental Reading deck.')
            return

        dialog = QDialog(mw)
        layout = QVBoxLayout()
        upButton = QPushButton('Up')
        upButton.clicked.connect(self._moveUp)
        downButton = QPushButton('Down')
        downButton.clicked.connect(self._moveDown)
        randomizeButton = QPushButton('Randomize')
        randomizeButton.clicked.connect(self._randomize)

        controlsLayout = QHBoxLayout()
        controlsLayout.addStretch()
        controlsLayout.addWidget(upButton)
        controlsLayout.addWidget(downButton)
        controlsLayout.addWidget(randomizeButton)

        layout.addLayout(controlsLayout)
        layout.addWidget(self.cardTreeWidget)

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
            self.showDialog(card)
            return
        elif ease == SCHEDULE_DONE:
            self.done_with_note()
            return

        if method == 'percent':
            totalCards = len([c['id'] for c in self._getCardInfo(card.did)])
            newPos = totalCards * (value / 100)
        elif method == 'count':
            newPos = value

        if randomize:
            newPos = gauss(newPos, newPos / 10)

        cardNote = card.note()
        setField(
            cardNote, self.settings["titleField"],
            getField(cardNote, self.settings["titleField"]) + ease_str
        )
        cardNote.flush()

        newPos = max(1, int(newPos))
        self.reposition(card, newPos, from_extract)
        tooltip(
            "Ok, we'll get back to that <b>{}</b> <br/><i>moved to position <b>{}</b></i>"
            .format(tooltip_message, newPos)
        )
        self.update_organizer(card)

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
            c['id']
            for c in self._getCardInfo(card.did, suspended=False, buried=False)
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

    def _moveUp(self):
        selected = [
            self.cardListWidget.item(i)
            for i in range(self.cardListWidget.count())
            if self.cardListWidget.item(i).isSelected()
        ]
        for item in selected:
            row = self.cardListWidget.row(item)
            newRow = max(0, row - 1)
            self.cardListWidget.insertItem(
                newRow, self.cardListWidget.takeItem(row)
            )
            item.setSelected(True)

    def _moveDown(self):
        selected = [
            self.cardListWidget.item(i)
            for i in range(self.cardListWidget.count())
            if self.cardListWidget.item(i).isSelected()
        ]
        selected.reverse()
        for item in selected:
            row = self.cardListWidget.row(item)
            newRow = min(self.cardListWidget.count(), row + 1)
            self.cardListWidget.insertItem(
                newRow, self.cardListWidget.takeItem(row)
            )
            item.setSelected(True)

    def _randomize(self):
        allItems = [
            self.cardListWidget.takeItem(0)
            for i in range(self.cardListWidget.count())
        ]
        shuffle(allItems)
        for item in allItems:
            self.cardListWidget.addItem(item)

    def _getCardInfo(self, did, mark_card=None, suspended=True, buried=True):
        cardInfo = []

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
                title = "[*]" if mark_card and cid == mark_card.id else ""
                title += "[C]" if mw.reviewer.card and cid == mw.reviewer.card.id else ""
                title += " "
                cardInfo.append(
                    {
                        'id': cid,
                        'nid': nid,
                        'type': ctype,
                        'queue': queue,
                        'due': due,
                        'interval': ivl,
                        'reps': reps,
                        'lapses': lapses,
                        'title': title + note[self.settings['titleField']]
                    }
                )
        return cardInfo
