# -*- coding: utf-8 -*-

from __future__ import unicode_literals, division
import sys
import os
import io
import stat
import time
import re
from math import ceil
from datetime import datetime
import struct

from PyQt4.QtCore import Qt, QBuffer
from PyQt4.QtGui import QAction, QKeySequence, QMenu, QShortcut, QLineEdit, QImage

from BeautifulSoup import BeautifulSoup as bs4

from aqt import mw
from aqt.utils import showInfo


def irx_file_path(filename):
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", filename
    )


def capitalize_phrase(phrase):
    return " ".join([w.capitalize() for w in phrase.split(" ")])


def compress_image(img_data, extension, max_size=None):
    max_size = max_size or mw.readingManager.settings.get(
        'maxImageBytes', 1048576
    )
    compressed_data = img_data
    save_size = len(img_data)
    compression_ratio = round(len(compressed_data) / len(img_data), 4)
    while int(compression_ratio) == 1 and extension.lower() != "gif":
        quality = 100
        step = max(ceil(len(img_data) / 1024 / 1024), 15)
        while save_size > max_size and quality != 50:
            quality = max(quality - step, 50)
            buf = QBuffer()
            buf.open(QBuffer.ReadWrite)
            tmp = QImage()
            tmp.loadFromData(img_data)
            tmp.save(buf, extension, quality)
            save_size = len(buf.data())
            if save_size <= max_size:
                compressed_data = buf.data()
            buf.close()
        compression_ratio = round(len(compressed_data) / len(img_data), 4)
        if int(compression_ratio) == 1:
            buf = QBuffer()
            buf.open(QBuffer.ReadWrite)
            tmp = tmp.scaled(tmp.width()/2, tmp.height()/2)
            tmp.save(buf, extension)
            img_data = buf.data()
            buf.close()
    if extension.lower() != "gif":
        thumb = QImage()
        thumb.loadFromData(compressed_data)
        thumb = thumb.scaled(250, 250, Qt.KeepAspectRatio)
        buf = QBuffer()
        buf.open(QBuffer.ReadWrite)
        thumb.save(buf, extension)
        thumb_data = buf.data()
    else:
        thumb_data = None
    return compressed_data, compression_ratio, thumb_data


def keypress_capture_field(valid=None):
    regular_key_input = QLineEdit()
    regular_key_input.setMaxLength(1)
    regular_key_input.setFixedWidth(30)

    def register_regular_key(evt):
        ok_keys = [v.lower() for v in valid]
        key_press = unicode(evt.text()).lower()
        if not ok_keys or key_press in ok_keys:
            regular_key_input.setText(key_press)
            regular_key_input.clearFocus()

    regular_key_input.keyPressEvent = register_regular_key
    return regular_key_input


def hex_to_rgb(_hex, alpha=None):
    rgb = struct.unpack('BBB', _hex.decode('hex'))
    if alpha:
        if isinstance(alpha, (str, unicode)):
            return str(rgb).replace(")", ", {})".format(alpha))
        return rgb + (alpha, )
    return rgb


def rgba_percent_to_decimal_alpha(rgba):
    rgba_vals = tuple(map(int, re.findall(r'[0-9]+', rgba.replace("%", ""))))
    alpha_percent = rgba_vals[3]
    alpha_decimal = round(float(alpha_percent) / 100, 2)
    return rgba.replace("{}%".format(alpha_percent), str(alpha_decimal))


def rgba_remove_alpha(rgba):
    rgba_vals = tuple(map(int, re.findall(r'[0-9]+', rgba.replace("%", ""))))
    return "rgb({})".format(",".join(str(v) for v in rgba_vals[:3]))


def rgb_to_hex(rgb):
    return struct.pack('BBB', *rgb).encode('hex')


def is_valid_number(_input, decimal=True):
    try:
        float(_input)
        ok = True
    except ValueError:
        ok = False

    if ok and not decimal and _input.find(".") > 0:
        return False
    return ok


def validation_style(_input, valid, ok_bg="#FFF", not_ok_bg="#FFAD9F"):
    _input.setStyleSheet(
        "QLineEdit{{ background-color:{}; }}".
        format(ok_bg if valid else not_ok_bg)
    )


def destroy_layout(layout):
    if layout:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
            else:
                destroy_layout(item.layout())


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
    return False


def mac_fix(keys, reverse=False):
    if sys.platform == "darwin":
        if not reverse:
            keys = keys.replace("Ctrl", "Cmd")
            keys = keys.replace("Alt", "Opt")
            keys = keys.replace("Meta", "Ctrl")
        else:
            keys = keys.replace("Opt", "Alt")
            keys = keys.replace("Ctrl", "Meta")
            keys = keys.replace("Cmd", "Ctrl")
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


def add_menu_sep(menu_name):
    menu = mw.customMenus.get(menu_name)
    if menu:
        menu.addSeparator()


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
