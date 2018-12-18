# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from PyQt4.QtCore import QPoint, Qt
from PyQt4.QtGui import QShortcut, QKeySequence

from anki.hooks import wrap
from aqt import mw

from irx.util import addMenuItem, addShortcut, isIrxCard, viewingIrxText, db_log


class ViewManager():
    def __init__(self, settings):
        self.previousState = None
        self.zoomFactor = 1
        self.settings = settings
        mw.moveToState = wrap(mw.moveToState, self.resetZoom, 'before')
        mw.web.wheelEvent = wrap(mw.web.wheelEvent, self.saveScroll)
        mw.web.mouseReleaseEvent = wrap(
            mw.web.mouseReleaseEvent, self.saveScroll, 'before'
        )

    def setZoom(self, factor=None):
        if factor:
            mw.web.setZoomFactor(factor)
        else:
            mw.web.setZoomFactor(
                self.settings['zoom'][str(mw.reviewer.card.id)]
            )

    def zoomIn(self):
        if viewingIrxText():
            cid = str(mw.reviewer.card.id)

            if cid not in self.settings['zoom']:
                self.settings['zoom'][cid] = 1

            self.settings['zoom'][cid] += self.settings['zoomStep']
            mw.web.setZoomFactor(self.settings['zoom'][cid])
        elif mw.state == 'review':
            self.zoomFactor += self.settings['zoomStep']
            mw.web.setZoomFactor(self.zoomFactor)
        else:
            self.settings['generalZoom'] += self.settings['zoomStep']
            mw.web.setZoomFactor(self.settings['generalZoom'])

    def zoomOut(self):
        if viewingIrxText():
            cid = str(mw.reviewer.card.id)

            if cid not in self.settings['zoom']:
                self.settings['zoom'][cid] = 1

            self.settings['zoom'][cid] -= self.settings['zoomStep']
            mw.web.setZoomFactor(self.settings['zoom'][cid])
        elif mw.state == 'review':
            self.zoomFactor -= self.settings['zoomStep']
            mw.web.setZoomFactor(self.zoomFactor)
        else:
            self.settings['generalZoom'] -= self.settings['zoomStep']
            mw.web.setZoomFactor(self.settings['generalZoom'])

    def setScroll(self, pos=None):
        if pos is None:
            savedPos = self.settings['scroll'][str(mw.reviewer.card.id)]
            mw.web.page().mainFrame().setScrollPosition(QPoint(0, savedPos))
        else:
            mw.web.page().mainFrame().setScrollPosition(QPoint(0, pos))
            self.saveScroll()

    def saveScroll(self, event=None):
        if viewingIrxText():
            pos = mw.web.page().mainFrame().scrollPosition().y()
            self.settings['scroll'][str(mw.reviewer.card.id)] = pos

    def pageUp(self):
        currentPos = mw.web.page().mainFrame().scrollPosition().y()
        pageHeight = mw.web.page().viewportSize().height()
        movementSize = pageHeight * self.settings['pageScrollFactor']
        newPos = max(0, (currentPos - movementSize))
        self.setScroll(newPos)

    def pageDown(self):
        currentPos = mw.web.page().mainFrame().scrollPosition().y()
        pageHeight = mw.web.page().viewportSize().height()
        movementSize = pageHeight * self.settings['pageScrollFactor']
        pageBottom = mw.web.page().mainFrame().scrollBarMaximum(Qt.Vertical)
        newPos = min(pageBottom, (currentPos + movementSize))
        reached_end = newPos == pageBottom or pageBottom == 0
        mw.readingManagerX.space_scroll.setEnabled(not reached_end)
        self.setScroll(newPos)

    def lineUp(self):
        currentPos = mw.web.page().mainFrame().scrollPosition().y()
        pageHeight = mw.web.page().viewportSize().height()
        movementSize = pageHeight * self.settings['lineScrollFactor']
        newPos = max(0, (currentPos - movementSize))
        self.setScroll(newPos)

    def lineDown(self):
        currentPos = mw.web.page().mainFrame().scrollPosition().y()
        pageHeight = mw.web.page().viewportSize().height()
        movementSize = pageHeight * self.settings['lineScrollFactor']
        pageBottom = mw.web.page().mainFrame().scrollBarMaximum(Qt.Vertical)
        newPos = min(pageBottom, (currentPos + movementSize))
        self.setScroll(newPos)

    def resetZoom(self, state, *args):
        if state in ['deckBrowser', 'overview']:
            mw.web.setZoomFactor(self.settings['generalZoom'])
        elif state == 'review' and not isIrxCard(mw.reviewer.card):
            self.setZoom(self.zoomFactor)

        self.previousState = state