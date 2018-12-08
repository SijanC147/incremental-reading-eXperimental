from functools import partial

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


class QuickKeys:
    def __init__(self, settings):
        self.settings = settings

    def loadMenuItems(self):
        self.clearMenuItems()

        for keyCombo, quickKey in self.settings['quickKeys'].items():
            menuText = 'Add Card [%s -> %s]' % (
                quickKey['modelName'], quickKey['deckName']
            )
            function = partial(mw.readingManager.quick_add, quickKey)
            mw.readingManager.quickKeyActions.append(
                addMenuItem('Read::Quick Keys', menuText, function, keyCombo)
            )

    def clearMenuItems(self):
        for action in mw.readingManager.quickKeyActions:
            mw.customMenus['Read::Quick Keys'].removeAction(action)
        mw.readingManager.quickKeyActions = []

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
            # 'bgColor': self.bgColorComboBox.currentText(),
            # 'textColor': self.textColorComboBox.currentText(),
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