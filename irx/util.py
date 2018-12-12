# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import sys
import os
import io
import stat
import time
from datetime import datetime

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QAction, QKeySequence, QMenu, QShortcut

from BeautifulSoup import BeautifulSoup as bs4

from aqt import mw
from aqt.utils import showInfo


def isIrxCard(card):
    if (
        card and
        (card.model().get("name") == mw.readingManager.settings['modelName'])
    ):
        return True
    else:
        return False


def viewingIrxText():
    if (
        isIrxCard(mw.reviewer.card) and (mw.reviewer.state == 'question') and
        (mw.state == 'review')
    ):
        return True
    else:
        return False


def mac_fix(keys, reverse=False):
    if sys.platform == "darwin":
        if not reverse:
            keys = keys.replace("Ctrl", "Cmd")
            keys = keys.replace("Alt", "Opt")
            keys = keys.replace("Meta", "Ctrl")
        else:
            keys = keys.replace("Cmd", "Ctrl")
            keys = keys.replace("Opt", "Alt")
            keys = keys.replace("Ctrl", "Meta")
    return keys


def irx_siblings(parent_note):
    parent_field = "irxnid:{}".format(parent_note.id)
    irx_model = mw.col.models.byName(mw.readingManager.settings["modelName"])
    irx_notes = [mw.col.getNote(nid) for nid in mw.col.models.nids(irx_model)]
    sibling_notes = [
        note for note in irx_notes if
        getField(note, mw.readingManager.settings["pidField"]) == parent_field
    ]
    return sibling_notes


def timestamp_id():
    return int(time.time() * 100)


def pretty_date(templ_format=None, invalid=None):
    default = "%A, %d %B %Y %H:%M"
    set_format = mw.readingManager.settings.get('captionFormat', default)
    templ_format = templ_format or set_format
    try:
        return datetime.now().strftime(templ_format)
    except ValueError:
        return invalid if invalid else datetime.now().strftime(default)


def addMenu(fullName):
    if not hasattr(mw, 'customMenus'):
        mw.customMenus = {}

    if len(fullName.split('::')) == 2:
        menuName, subMenuName = fullName.split('::')
        hasSubMenu = True
    else:
        menuName = fullName
        hasSubMenu = False

    if menuName not in mw.customMenus:
        menu = QMenu('&' + menuName, mw)
        mw.customMenus[menuName] = menu
        mw.form.menubar.insertMenu(
            mw.form.menuTools.menuAction(), mw.customMenus[menuName]
        )

    if hasSubMenu and (fullName not in mw.customMenus):
        subMenu = QMenu('&' + subMenuName, mw)
        mw.customMenus[fullName] = subMenu
        mw.customMenus[menuName].addMenu(subMenu)


def db_log(data, title=None, lim=None):
    if not mw.db.editor.dialog.isVisible():
        mw.db.show()
    if isinstance(data, dict):
        mw.db.log(
            "{0}{1} \n -----------------------------".format(
                "{} \n".format(title) if title else "", "\n".join(
                    [
                        "{0}: {1}".format(k, v[:lim])
                        if lim else "{0}: {1}".format(k, v)
                        for k, v in data.items()
                    ]
                )
            )
        )
    elif isinstance(data, str):
        data = data[:lim] if lim else data
        mw.db.log(
            "{0}{1} \n -----------------------------".format(
                "{} \n".format(title) if title else "", data
            )
        )
    else:
        mw.db.log(
            "{0}{1} \n -----------------------------".format(
                "{} \n".format(title) if title else "",
                str(data)[:lim] if lim else str(data)
            )
        )


def addMenuItem(menuName, text, function, keys=None):
    action = QAction(text, mw)

    if keys:
        action.setShortcut(QKeySequence(keys))

    action.triggered.connect(function)

    if menuName == 'File':
        mw.form.menuCol.addAction(action)
    elif menuName == 'Edit':
        mw.form.menuEdit.addAction(action)
    elif menuName == 'Tools':
        mw.form.menuTools.addAction(action)
    elif menuName == 'Help':
        mw.form.menuHelp.addAction(action)
    else:
        addMenu(menuName)
        mw.customMenus[menuName].addAction(action)

    return action


def addShortcut(function, keys):
    shortcut = QShortcut(QKeySequence(keys), mw)
    shortcut.activated.connect(function)
    return shortcut


def getField(note, fieldName):
    model = note.model()
    index, _ = mw.col.models.fieldMap(model)[fieldName]
    return note.fields[index]


def setField(note, fieldName, content):
    model = note.model()
    index, _ = mw.col.models.fieldMap(model)[fieldName]
    note.fields[index] = content


def setComboBoxItem(comboBox, text):
    index = comboBox.findText(text, Qt.MatchFixedString)
    comboBox.setCurrentIndex(index)


def removeComboBoxItem(comboBox, text):
    index = comboBox.findText(text, Qt.MatchFixedString)
    comboBox.removeItem(index)


def disableOutdated():
    outdated = ['Incremental_Reading_Extension.py', 'View_Size_Adjust.py']
    disabled = False
    for filename in outdated:
        path = os.path.join(mw.pm.addonFolder(), filename)
        if os.path.isfile(path):
            os.rename(path, path + '.old')
            disabled = True
    if disabled:
        showInfo(
            'One or more outdated add-on files have been deactivated.',
            ' Please restart Anki.'
        )


def updateModificationTime(path):
    accessTime = os.stat(path)[stat.ST_ATIME]
    modificationTime = time.time()
    os.utime(path, (accessTime, modificationTime))


def loadFile(fileDir, filename):
    moduleDir, _ = os.path.split(__file__)
    path = os.path.join(moduleDir, fileDir, filename)
    with io.open(path, encoding='utf-8') as f:
        return f.read()
