# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from codecs import open
from functools import partial
from sys import getfilesystemencoding
import json
import os

from PyQt4.QtCore import Qt
from PyQt4.QtGui import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget
)

from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo

from irx.util import (
    addMenuItem,
    removeComboBoxItem,
    setComboBoxItem,
    updateModificationTime,
    mac_fix,
    db_log,
)

from irx.editable_controls import IRX_REVIEWER, IRX_IMAGE_MANAGER

IRX_REVIEWER_ACTIONS = {
    "show help": lambda: mw.readingManager.settingsManager.show_help(),
    "toggle images": lambda: mw.readingManager.textManager.toggle_images_sidebar(),
    "toggle formatting": lambda: mw.readingManager.textManager.toggle_show_formatting(),
    "toggle removed text": lambda: mw.readingManager.textManager.toggle_show_removed(),
    "toggle extracts": lambda: mw.readingManager.textManager.toggle_show_extracts(),
    "done (suspend)": lambda: mw.readingManager.scheduler.done_with_note(),
    "undo": lambda: mw.readingManager.textManager.undo(),
    "add image": lambda: mw.readingManager.textManager.extract_image(),
    "add image (skip caption)": lambda: mw.readingManager.textManager.extract_image(skip_captions=True),
    "extract image": lambda: mw.readingManager.textManager.extract_image(remove_src=True),
    "extract image (skip caption)": lambda: mw.readingManager.textManager.extract_image(remove_src=True, skip_captions=True),
    "extract important": lambda: mw.readingManager.textManager.extract(schedule_extract=1),
    "extract complimentary": lambda: mw.readingManager.textManager.extract(schedule_extract=2),
    "extract important (and edit)": lambda: mw.readingManager.textManager.extract(also_edit=True, schedule_extract=1),
    "extract complimentary (and edit)": lambda: mw.readingManager.textManager.extract(also_edit=True, schedule_extract=2),
    "bold": lambda: mw.readingManager.textManager.format("bold"),
    "underline": lambda: mw.readingManager.textManager.format("underline"),
    "italic": lambda: mw.readingManager.textManager.format("italic"),
    "strikethrough": lambda: mw.readingManager.textManager.format("strike"),
    "remove": lambda: mw.readingManager.textManager.remove(),
    "show reading list": lambda: mw.readingManager.scheduler.show_organizer(),
    "show image manager": lambda: mw.readingManager.textManager.manage_images(),
    "zoom in": lambda: mw.viewManager.zoomIn(),
    "zoom out": lambda: mw.viewManager.zoomOut(),
    "line up": lambda: mw.viewManager.lineUp(),
    "line down": lambda: mw.viewManager.lineDown(),
    "page up": lambda: mw.viewManager.pageUp(),
    "page down": lambda: mw.viewManager.pageDown()
}


class SettingsManager():
    def __init__(self):
        self.irx_controls = {
            IRX_REVIEWER[action]: IRX_REVIEWER_ACTIONS[action]
            for action in IRX_REVIEWER_ACTIONS.keys()
        }
        self.highlight_colors = {
            "irx_schedule_soon": ("#FFE11A", "#000000"),
            "irx_schedule_later": ("#FD7400", "#000000"),
            "irx_extract": ("#FF971A", "#000000"),
            "flash_extract": ("#1F8A70", "#000000"),
            "removed_text": ("#262626", "#FFFFFF")
        }

        self.settingsChanged = False
        self.loadSettings()

        keys = IRX_REVIEWER.values()
        duplicate_controls = list(
            set([key for key in keys if keys.count(key) > 1])
        )
        if duplicate_controls:
            showInfo(
                "The following IRX shortcut(s) are assigned conflicting actions:<br/><br/>{}<br/><br/>Review and change them in editable_controls.py"
                .format(" ".join(list(set(duplicate_controls))))
            )

        if self.settingsChanged:
            showInfo(
                """
                    Your Incremental Reading settings file has been modified
                    for compatibility reasons. Please take a moment to
                    reconfigure the add-on to your liking."""
            )

        addHook('unloadProfile', self.saveSettings)

    def show_help(self):
        keys = IRX_REVIEWER.values()
        duplicate_controls = list(
            set([key for key in keys if keys.count(key) > 1])
        )
        help_text = "<table>"
        actions = IRX_REVIEWER_ACTIONS.keys()
        for i in range(0, len(actions), 2):
            if IRX_REVIEWER[actions[i]] not in duplicate_controls:
                hotkey_text = mac_fix(IRX_REVIEWER[actions[i]])
            else:
                hotkey_text = "<font color='red'>" + mac_fix(
                    IRX_REVIEWER[actions[i]]
                ) + "</font>"
            help_text += "<tr>"
            help_text += "<td style='padding: 5px'><b>{hotkey}</b></td><td style='padding: 5px'>{action}</td><td style='padding: 5px'></td>".format(
                hotkey=hotkey_text, action=actions[i]
            )
            if i + 1 < len(actions):
                if IRX_REVIEWER[actions[i + 1]] not in duplicate_controls:
                    hotkey_text = mac_fix(IRX_REVIEWER[actions[i + 1]])
                else:
                    hotkey_text = "<font color='red'>" + mac_fix(
                        IRX_REVIEWER[actions[i + 1]]
                    ) + "</font>"
                help_text += "<td style='padding: 5px'><b>{hotkey}</b></td><td style='padding: 5px'>{action}</td>".format(
                    hotkey=hotkey_text, action=actions[i + 1]
                )
            else:
                help_text += "<td style='padding: 5px'></td>"
            help_text += "</tr>"
        help_text += "</table>"
        db_log(help_text)
        help_dialog = QDialog(mw)
        help_layout = QHBoxLayout()
        help_label = QLabel()
        help_label.setAlignment(Qt.AlignCenter)
        help_label.setText(help_text)
        help_layout.addWidget(help_label)
        help_dialog.setLayout(help_layout)
        help_dialog.setWindowModality(Qt.WindowModal)
        help_dialog.exec_()

    def saveSettings(self):
        with open(self.json_path, 'w', encoding='utf-8') as json_file:
            self.settings["irx_controls"] = {}
            json.dump(self.settings, json_file)
            self.settings["irx_controls"] = self.irx_controls

        updateModificationTime(self.mediaDir)

    def loadSettings(self):
        self.defaults = {
            'zoomStep': 0.1,
            'generalZoom': 1,
            'lineScrollFactor': 0.05,
            'pageScrollFactor': 0.5,
            'schedLaterMethod': 'percent',
            'schedLaterRandom': True,
            'schedLaterValue': 50,
            'schedSoonMethod': 'percent',
            'schedSoonRandom': True,
            'schedSoonValue': 10,
            'modelName': 'IR3X',
            'sourceField': 'Source',
            'textField': 'Text',
            'titleField': 'Title',
            'dateField': 'Date',
            'parentField': 'Parent',
            'pidField': 'pid',
            'linkField': 'Link',
            'imagesField': 'Images',
            'quickKeys': {},
            'scroll': {},
            'zoom': {},
        }

        self.mediaDir = os.path.join(mw.pm.profileFolder(), 'collection.media')
        self.json_path = os.path.join(self.mediaDir, '_irx.json')

        if os.path.isfile(self.json_path):
            with open(self.json_path, encoding='utf-8') as json_file:
                self.settings = json.load(json_file)
            self.addMissingSettings()
            self.removeOutdatedQuickKeys()
        else:
            self.settings = self.defaults

        self.settings["irx_controls"] = self.irx_controls
        self.settings["highlight_colors"] = self.highlight_colors

        self.loadMenuItems()

    def addMissingSettings(self):
        for k, v in self.defaults.items():
            if k not in self.settings:
                self.settings[k] = v
                self.settingsChanged = True

    def removeOutdatedQuickKeys(self):
        required = [
            'alt', 'bgColor', 'ctrl', 'deckName', 'editExtract', 'editSource',
            'fieldName', 'modelName', 'regularKey', 'shift', 'textColor'
        ]

        for keyCombo, quickKey in self.settings['quickKeys'].copy().items():
            for k in required:
                if k not in quickKey:
                    self.settings['quickKeys'].pop(keyCombo)
                    self.settingsChanged = True
                    break

    def loadMenuItems(self):
        self.clearMenuItems()

        for keyCombo, quickKey in self.settings['quickKeys'].items():
            menuText = 'Add Card [%s -> %s]' % (
                quickKey['modelName'], quickKey['deckName']
            )
            function = partial(mw.readingManager.quickAdd, quickKey)
            mw.readingManager.quickKeyActions.append(
                addMenuItem('Read::Quick Keys', menuText, function, keyCombo)
            )

    def clearMenuItems(self):
        for action in mw.readingManager.quickKeyActions:
            mw.customMenus['Read::Quick Keys'].removeAction(action)
        mw.readingManager.quickKeyActions = []

    def showDialog(self):
        dialog = QDialog(mw)

        zoom_scroll_layout = QHBoxLayout()
        zoom_scroll_layout.addWidget(self.createZoomGroupBox())
        zoom_scroll_layout.addWidget(self.createScrollGroupBox())
        zoom_scroll_widget = QWidget()
        zoom_scroll_widget.setLayout(zoom_scroll_layout)

        scheduling_layout = QVBoxLayout()
        scheduling_layout.addWidget(self.create_scheduling_group_box())
        scheduling_widget = QWidget()
        scheduling_widget.setLayout(scheduling_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)

        main_layout = QVBoxLayout()
        main_layout.addWidget(zoom_scroll_widget)
        main_layout.addWidget(scheduling_widget)
        main_layout.addWidget(button_box)

        dialog.setLayout(main_layout)
        dialog.setWindowTitle('IR3X Settings')
        dialog.exec_()

        self.settings['zoomStep'] = self.zoomStepSpinBox.value() / 100.0
        self.settings['generalZoom'] = self.generalZoomSpinBox.value() / 100.0
        self.settings['lineScrollFactor'] = self.lineStepSpinBox.value() / 100.0
        self.settings['pageScrollFactor'] = self.pageStepSpinBox.value() / 100.0
        self.settings['schedSoonRandom'] = self.soonRandomCheckBox.isChecked()
        self.settings['schedLaterRandom'] = self.laterRandomCheckBox.isChecked()

        try:
            self.settings['schedSoonValue'] = int(
                self.soonIntegerEditBox.text()
            )
            self.settings['schedLaterValue'] = int(
                self.laterIntegerEditBox.text()
            )
        except:
            pass

        if self.soonPercentButton.isChecked():
            self.settings['schedSoonMethod'] = 'percent'
        else:
            self.settings['schedSoonMethod'] = 'count'

        if self.laterPercentButton.isChecked():
            self.settings['schedLaterMethod'] = 'percent'
        else:
            self.settings['schedLaterMethod'] = 'count'

        mw.viewManager.resetZoom(mw.state)

    def create_scheduling_group_box(self):
        soon_label = QLabel('Soon Button')
        later_label = QLabel('Later Button')

        self.soonPercentButton = QRadioButton('Percent')
        soonPositionButton = QRadioButton('Position')
        self.laterPercentButton = QRadioButton('Percent')
        laterPositionButton = QRadioButton('Position')
        self.soonRandomCheckBox = QCheckBox('Randomize')
        self.laterRandomCheckBox = QCheckBox('Randomize')

        self.soonIntegerEditBox = QLineEdit()
        self.soonIntegerEditBox.setFixedWidth(100)
        self.laterIntegerEditBox = QLineEdit()
        self.laterIntegerEditBox.setFixedWidth(100)

        if self.settings['schedSoonMethod'] == 'percent':
            self.soonPercentButton.setChecked(True)
        else:
            soonPositionButton.setChecked(True)

        if self.settings['schedLaterMethod'] == 'percent':
            self.laterPercentButton.setChecked(True)
        else:
            laterPositionButton.setChecked(True)

        if self.settings['schedSoonRandom']:
            self.soonRandomCheckBox.setChecked(True)

        if self.settings['schedLaterRandom']:
            self.laterRandomCheckBox.setChecked(True)

        self.soonIntegerEditBox.setText(str(self.settings['schedSoonValue']))
        self.laterIntegerEditBox.setText(str(self.settings['schedLaterValue']))

        soon_layout = QHBoxLayout()
        soon_layout.addWidget(soon_label)
        soon_layout.addStretch()
        soon_layout.addWidget(self.soonIntegerEditBox)
        soon_layout.addWidget(self.soonPercentButton)
        soon_layout.addWidget(soonPositionButton)
        soon_layout.addWidget(self.soonRandomCheckBox)

        later_layout = QHBoxLayout()
        later_layout.addWidget(later_label)
        later_layout.addStretch()
        later_layout.addWidget(self.laterIntegerEditBox)
        later_layout.addWidget(self.laterPercentButton)
        later_layout.addWidget(laterPositionButton)
        later_layout.addWidget(self.laterRandomCheckBox)

        soon_button_group = QButtonGroup(soon_layout)
        soon_button_group.addButton(self.soonPercentButton)
        soon_button_group.addButton(soonPositionButton)

        later_button_group = QButtonGroup(later_layout)
        later_button_group.addButton(self.laterPercentButton)
        later_button_group.addButton(laterPositionButton)

        layout = QVBoxLayout()
        layout.addLayout(soon_layout)
        layout.addLayout(later_layout)
        layout.addStretch()

        group_box = QGroupBox('Scheduling')
        group_box.setLayout(layout)

        return group_box

    def createZoomGroupBox(self):
        zoomStepLabel = QLabel('Zoom Step')
        zoomStepPercentLabel = QLabel('%')
        generalZoomLabel = QLabel('General Zoom')
        generalZoomPercentLabel = QLabel('%')

        self.zoomStepSpinBox = QSpinBox()
        self.zoomStepSpinBox.setMinimum(5)
        self.zoomStepSpinBox.setMaximum(100)
        self.zoomStepSpinBox.setSingleStep(5)
        zoomStepPercent = round(self.settings['zoomStep'] * 100)
        self.zoomStepSpinBox.setValue(zoomStepPercent)

        self.generalZoomSpinBox = QSpinBox()
        self.generalZoomSpinBox.setMinimum(10)
        self.generalZoomSpinBox.setMaximum(200)
        self.generalZoomSpinBox.setSingleStep(10)
        generalZoomPercent = round(self.settings['generalZoom'] * 100)
        self.generalZoomSpinBox.setValue(generalZoomPercent)

        zoomStepLayout = QHBoxLayout()
        zoomStepLayout.addWidget(zoomStepLabel)
        zoomStepLayout.addStretch()
        zoomStepLayout.addWidget(self.zoomStepSpinBox)
        zoomStepLayout.addWidget(zoomStepPercentLabel)

        generalZoomLayout = QHBoxLayout()
        generalZoomLayout.addWidget(generalZoomLabel)
        generalZoomLayout.addStretch()
        generalZoomLayout.addWidget(self.generalZoomSpinBox)
        generalZoomLayout.addWidget(generalZoomPercentLabel)

        layout = QVBoxLayout()
        layout.addLayout(zoomStepLayout)
        layout.addLayout(generalZoomLayout)
        layout.addStretch()

        groupBox = QGroupBox('Zoom')
        groupBox.setLayout(layout)

        return groupBox

    def createScrollGroupBox(self):
        lineStepLabel = QLabel('Line Step')
        lineStepPercentLabel = QLabel('%')
        pageStepLabel = QLabel('Page Step')
        pageStepPercentLabel = QLabel('%')

        self.lineStepSpinBox = QSpinBox()
        self.lineStepSpinBox.setMinimum(5)
        self.lineStepSpinBox.setMaximum(100)
        self.lineStepSpinBox.setSingleStep(5)
        self.lineStepSpinBox.setValue(
            round(self.settings['lineScrollFactor'] * 100)
        )

        self.pageStepSpinBox = QSpinBox()
        self.pageStepSpinBox.setMinimum(5)
        self.pageStepSpinBox.setMaximum(100)
        self.pageStepSpinBox.setSingleStep(5)
        self.pageStepSpinBox.setValue(
            round(self.settings['pageScrollFactor'] * 100)
        )

        lineStepLayout = QHBoxLayout()
        lineStepLayout.addWidget(lineStepLabel)
        lineStepLayout.addStretch()
        lineStepLayout.addWidget(self.lineStepSpinBox)
        lineStepLayout.addWidget(lineStepPercentLabel)

        pageStepLayout = QHBoxLayout()
        pageStepLayout.addWidget(pageStepLabel)
        pageStepLayout.addStretch()
        pageStepLayout.addWidget(self.pageStepSpinBox)
        pageStepLayout.addWidget(pageStepPercentLabel)

        layout = QVBoxLayout()
        layout.addLayout(lineStepLayout)
        layout.addLayout(pageStepLayout)
        layout.addStretch()

        groupBox = QGroupBox('Scroll')
        groupBox.setLayout(layout)

        return groupBox

    def createQuickKeysTab(self):
        destDeckLabel = QLabel('Destination Deck')
        noteTypeLabel = QLabel('Note Type')
        textFieldLabel = QLabel('Paste Text to Field')
        keyComboLabel = QLabel('Key Combination')

        self.quickKeysComboBox = QComboBox()
        self.quickKeysComboBox.addItem('')
        self.quickKeysComboBox.addItems(self.settings['quickKeys'].keys())
        self.quickKeysComboBox.currentIndexChanged.connect(
            self.updateQuickKeysTab
        )

        self.destDeckComboBox = QComboBox()
        self.noteTypeComboBox = QComboBox()
        self.textFieldComboBox = QComboBox()
        self.quickKeyEditExtractCheckBox = QCheckBox('Edit Extracted Note')
        self.quickKeyEditSourceCheckBox = QCheckBox('Edit Source Note')
        self.quickKeyPlainTextCheckBox = QCheckBox('Extract as Plain Text')

        self.ctrlKeyCheckBox = QCheckBox('Ctrl')
        self.shiftKeyCheckBox = QCheckBox('Shift')
        self.altKeyCheckBox = QCheckBox('Alt')
        self.regularKeyComboBox = QComboBox()
        self.regularKeyComboBox.addItem('')
        self.regularKeyComboBox.addItems(
            list('ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789')
        )

        destDeckLayout = QHBoxLayout()
        destDeckLayout.addWidget(destDeckLabel)
        destDeckLayout.addWidget(self.destDeckComboBox)

        noteTypeLayout = QHBoxLayout()
        noteTypeLayout.addWidget(noteTypeLabel)
        noteTypeLayout.addWidget(self.noteTypeComboBox)

        textFieldLayout = QHBoxLayout()
        textFieldLayout.addWidget(textFieldLabel)
        textFieldLayout.addWidget(self.textFieldComboBox)

        keyComboLayout = QHBoxLayout()
        keyComboLayout.addWidget(keyComboLabel)
        keyComboLayout.addStretch()
        keyComboLayout.addWidget(self.ctrlKeyCheckBox)
        keyComboLayout.addWidget(self.shiftKeyCheckBox)
        keyComboLayout.addWidget(self.altKeyCheckBox)
        keyComboLayout.addWidget(self.regularKeyComboBox)

        deckNames = ["[Mirror]"]
        deckNames += sorted([d['name'] for d in mw.col.decks.all()])
        self.destDeckComboBox.addItem('')
        self.destDeckComboBox.addItems(deckNames)

        modelNames = sorted([m['name'] for m in mw.col.models.all()])
        self.noteTypeComboBox.addItem('')
        self.noteTypeComboBox.addItems(modelNames)
        self.noteTypeComboBox.currentIndexChanged.connect(self.updateFieldList)

        newButton = QPushButton('New')
        newButton.clicked.connect(self.clearQuickKeysTab)
        deleteButton = QPushButton('Delete')
        deleteButton.clicked.connect(self.deleteQuickKey)
        saveButton = QPushButton('Save')
        saveButton.clicked.connect(self.setQuickKey)

        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        buttonLayout.addWidget(newButton)
        buttonLayout.addWidget(deleteButton)
        buttonLayout.addWidget(saveButton)

        layout = QVBoxLayout()
        layout.addWidget(self.quickKeysComboBox)
        layout.addLayout(destDeckLayout)
        layout.addLayout(noteTypeLayout)
        layout.addLayout(textFieldLayout)
        layout.addLayout(keyComboLayout)
        layout.addWidget(self.quickKeyEditExtractCheckBox)
        layout.addWidget(self.quickKeyEditSourceCheckBox)
        layout.addWidget(self.quickKeyPlainTextCheckBox)
        layout.addLayout(buttonLayout)

        tab = QWidget()
        tab.setLayout(layout)

        return tab

    def updateQuickKeysTab(self):
        quickKey = self.quickKeysComboBox.currentText()
        if quickKey:
            model = self.settings['quickKeys'][quickKey]
            setComboBoxItem(self.destDeckComboBox, model['deckName'])
            setComboBoxItem(self.noteTypeComboBox, model['modelName'])
            setComboBoxItem(self.textFieldComboBox, model['fieldName'])
            self.ctrlKeyCheckBox.setChecked(model['ctrl'])
            self.shiftKeyCheckBox.setChecked(model['shift'])
            self.altKeyCheckBox.setChecked(model['alt'])
            setComboBoxItem(self.regularKeyComboBox, model['regularKey'])
            self.quickKeyEditExtractCheckBox.setChecked(model['editExtract'])
            self.quickKeyEditSourceCheckBox.setChecked(model['editSource'])
            self.quickKeyPlainTextCheckBox.setChecked(model['plainText'])
        else:
            self.clearQuickKeysTab()

    def updateFieldList(self):
        modelName = self.noteTypeComboBox.currentText()
        self.textFieldComboBox.clear()
        if modelName:
            model = mw.col.models.byName(modelName)
            fieldNames = [f['name'] for f in model['flds']]
            self.textFieldComboBox.addItems(fieldNames)

    def clearQuickKeysTab(self):
        self.quickKeysComboBox.setCurrentIndex(0)
        self.destDeckComboBox.setCurrentIndex(0)
        self.noteTypeComboBox.setCurrentIndex(0)
        self.textFieldComboBox.setCurrentIndex(0)
        self.ctrlKeyCheckBox.setChecked(False)
        self.shiftKeyCheckBox.setChecked(False)
        self.altKeyCheckBox.setChecked(False)
        self.regularKeyComboBox.setCurrentIndex(0)
        self.quickKeyEditExtractCheckBox.setChecked(False)
        self.quickKeyEditSourceCheckBox.setChecked(False)
        self.quickKeyPlainTextCheckBox.setChecked(False)

    def deleteQuickKey(self):
        quickKey = self.quickKeysComboBox.currentText()
        if quickKey:
            self.settings['quickKeys'].pop(quickKey)
            removeComboBoxItem(self.quickKeysComboBox, quickKey)
            self.clearQuickKeysTab()
            self.loadMenuItems()

    def setQuickKey(self):
        quickKey = {
            'deckName': self.destDeckComboBox.currentText(),
            'modelName': self.noteTypeComboBox.currentText(),
            'fieldName': self.textFieldComboBox.currentText(),
            'ctrl': self.ctrlKeyCheckBox.isChecked(),
            'shift': self.shiftKeyCheckBox.isChecked(),
            'alt': self.altKeyCheckBox.isChecked(),
            'regularKey': self.regularKeyComboBox.currentText(),
            'bgColor': self.bgColorComboBox.currentText(),
            'textColor': self.textColorComboBox.currentText(),
            'editExtract': self.quickKeyEditExtractCheckBox.isChecked(),
            'editSource': self.quickKeyEditSourceCheckBox.isChecked(),
            'plainText': self.quickKeyPlainTextCheckBox.isChecked()
        }

        for k in ['deckName', 'modelName', 'regularKey']:
            if not quickKey[k]:
                showInfo(
                    """
                        Please complete all settings. Destination deck,
                        note type, and a letter or number for the key 
                        combination are required."""
                )
                return

        keyCombo = ''
        if quickKey['ctrl']:
            keyCombo += 'Ctrl+'
        if quickKey['shift']:
            keyCombo += 'Shift+'
        if quickKey['alt']:
            keyCombo += 'Alt+'
        keyCombo += quickKey['regularKey']

        self.settings['quickKeys'][keyCombo] = quickKey
        self.loadMenuItems()

        showInfo('New shortcut added: %s' % keyCombo)
