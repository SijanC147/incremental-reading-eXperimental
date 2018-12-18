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
    addMenuItem, removeComboBoxItem, setComboBoxItem, updateModificationTime,
    mac_fix, db_log, keypress_capture_field, color_picker_label,
    addComboBoxItem, irx_info_box
)


class QuickKeys:
    def __init__(self, settings, user_controls_config):
        self.settings = settings
        self.user_controls_config = user_controls_config

    def refresh_menu_items(self):
        for action in mw.readingManagerX.quickKeyActions:
            mw.customMenus['IR3X::Quick Keys'].removeAction(action)
        mw.readingManagerX.quickKeyActions = []

        for keys, params in self.settings['quickKeys'].items():
            mw.readingManagerX.quickKeyActions.append(
                addMenuItem(
                    menuName='IR3X::Quick Keys',
                    text="{0} -> {1}".format(
                        params['modelName'], params['deckName']
                    ),
                    function=partial(mw.readingManagerX.quick_add, params),
                    keys=keys
                )
            )

    def show_dialog(self):
        self.dialog = QDialog(mw)
        self.target_fields = {}
        self.quickKeysComboBox = QComboBox()
        self.quickKeysComboBox.addItem('')
        self.quickKeysComboBox.addItems(
            [mac_fix(key) for key in self.settings['quickKeys'].keys()]
        )
        self.quickKeysComboBox.currentIndexChanged.connect(
            self.update_quick_keys_dialog
        )

        destDeckLayout = QHBoxLayout()
        destDeckLabel = QLabel('Destination Deck')
        self.destDeckComboBox = QComboBox()
        deckNames = ["[Mirror]"]
        deckNames += sorted([d['name'] for d in mw.col.decks.all()])
        self.destDeckComboBox.addItem('')
        self.destDeckComboBox.addItems(deckNames)
        destDeckLayout.addWidget(destDeckLabel)
        destDeckLayout.addWidget(self.destDeckComboBox)
        _orig_combo_press = self.destDeckComboBox.mousePressEvent

        def _mod_combo_press(*args, **kwargs):
            irx_info_box('introducingMirrorDeckOption', parent=self.dialog)
            _orig_combo_press(*args, **kwargs)

        self.destDeckComboBox.mousePressEvent = _mod_combo_press

        noteTypeLayout = QHBoxLayout()
        noteTypeLabel = QLabel('Note Type')
        noteTypeLayout.addWidget(noteTypeLabel)
        self.noteTypeComboBox = QComboBox()
        noteTypeLayout.addWidget(self.noteTypeComboBox)
        modelNames = sorted([m['name'] for m in mw.col.models.all()])
        self.noteTypeComboBox.addItems(modelNames)
        edit_fields_button = QPushButton('Target Fields')
        edit_fields_button.setFocusPolicy(Qt.NoFocus)
        edit_fields_button.clicked.connect(self.update_target_fields)
        noteTypeLayout.addWidget(edit_fields_button)

        keyComboLayout = QHBoxLayout()
        keyComboLabel = QLabel('Key Combination')
        keyComboLayout.addWidget(keyComboLabel)
        keyComboLayout.addStretch()

        self.ctrlKeyCheckBox = QCheckBox(mac_fix('Ctrl'))
        keyComboLayout.addWidget(self.ctrlKeyCheckBox)
        self.shiftKeyCheckBox = QCheckBox('Shift')
        keyComboLayout.addWidget(self.shiftKeyCheckBox)
        self.altKeyCheckBox = QCheckBox(mac_fix('Alt'))
        keyComboLayout.addWidget(self.altKeyCheckBox)
        self.metaKeyCheckBox = QCheckBox(mac_fix('Meta'))
        keyComboLayout.addWidget(self.metaKeyCheckBox)

        self.regular_key_input = keypress_capture_field(
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789'
        )

        keyComboLayout.addWidget(self.regular_key_input)

        last_row_layout = QHBoxLayout()
        checkbox_layout = QVBoxLayout()
        col_label_layout = QVBoxLayout()
        self.quickKeyEditExtractCheckBox = QCheckBox(
            'Edit Extracted Note (not recommended)'
        )
        _orig_edit_extract_press = self.quickKeyEditExtractCheckBox.mousePressEvent

        def _mod_edit_extract_press(*args, **kwargs):
            irx_info_box('noteAboutEditingAQuickKeyExtract', parent=self.dialog)
            _orig_edit_extract_press(*args, **kwargs)

        self.quickKeyEditExtractCheckBox.mousePressEvent = _mod_edit_extract_press
        _orig_edit_source_press = self.quickKeyEditExtractCheckBox.mousePressEvent

        self.quickKeyEditSourceCheckBox = QCheckBox(
            'Edit Source Note (not recommended)'
        )

        def _mod_edit_source_press(*args, **kwargs):
            irx_info_box('noteAboutEditingAQuickKeyExtract', parent=self.dialog)
            _orig_edit_source_press(*args, **kwargs)

        self.quickKeyEditExtractCheckBox.mousePressEvent = _mod_edit_source_press

        self.quickKeyPlainTextCheckBox = QCheckBox('Extract as Plain Text')
        checkbox_layout.addSpacing(15)
        checkbox_layout.addWidget(self.quickKeyEditExtractCheckBox)
        checkbox_layout.addWidget(self.quickKeyEditSourceCheckBox)
        checkbox_layout.addWidget(self.quickKeyPlainTextCheckBox)

        self.bg_edit_label = color_picker_label()
        _orig_press = self.bg_edit_label.mousePressEvent

        def _mod_press(*args, **kwargs):
            irx_info_box('editingQuickKeysHighlights', parent=self.dialog)
            _orig_press(*args, **kwargs)

        self.bg_edit_label.mousePressEvent = _mod_press
        _orig_wheel = self.bg_edit_label.wheelEvent

        def _mod_wheel(*args, **kwargs):
            irx_info_box('editingQuickKeysHighlights', parent=self.dialog)
            _orig_wheel(*args, **kwargs)

        self.bg_edit_label.wheelEvent = _mod_wheel

        last_row_layout.addLayout(checkbox_layout)
        last_row_layout.addStretch()
        col_label_layout.addWidget(self.bg_edit_label)
        last_row_layout.addLayout(col_label_layout)

        new_button = QPushButton('Clear')
        new_button.clicked.connect(self.clear_quick_keys_dialog)
        new_button.setFocusPolicy(Qt.NoFocus)
        delete_button = QPushButton('Delete')
        delete_button.clicked.connect(self.delete_quick_key)
        delete_button.setFocusPolicy(Qt.NoFocus)
        save_button = QPushButton('Save')
        save_button.clicked.connect(self.save_quick_key)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(new_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(save_button)

        layout = QVBoxLayout()
        layout.addWidget(self.quickKeysComboBox)
        layout.addLayout(destDeckLayout)
        layout.addLayout(noteTypeLayout)
        layout.addLayout(keyComboLayout)
        layout.addLayout(last_row_layout)
        layout.addLayout(button_layout)

        self.dialog.setLayout(layout)
        self.dialog.setWindowTitle('IR3X Quick Keys')
        irx_info_box('firstTimeViewingQuickKeys', parent=self.dialog)
        self.dialog.exec_()

    def update_quick_keys_dialog(self):
        quick_key = mac_fix(self.quickKeysComboBox.currentText(), reverse=True)
        if quick_key:
            model = self.settings['quickKeys'][quick_key]
            self.target_fields = self.settings['quickKeys'][quick_key]['fields']
            setComboBoxItem(self.destDeckComboBox, model['deckName'])
            setComboBoxItem(self.noteTypeComboBox, model['modelName'])
            self.ctrlKeyCheckBox.setChecked(model['ctrl'])
            self.shiftKeyCheckBox.setChecked(model['shift'])
            self.altKeyCheckBox.setChecked(model['alt'])
            self.metaKeyCheckBox.setChecked(model['meta'])
            self.regular_key_input.setText(model['regularKey'])
            self.quickKeyEditExtractCheckBox.setChecked(model['editExtract'])
            self.quickKeyEditSourceCheckBox.setChecked(model['editSource'])
            self.quickKeyPlainTextCheckBox.setChecked(model['plainText'])
            self.bg_edit_label.set_rgba(model.get('bg'), initial=True)
        else:
            self.clear_quick_keys_dialog()

    def update_target_fields(self):
        self.focus_input = ""
        edit_fields_dialog = QDialog(self.dialog)
        edit_fields_dialog.setWindowTitle("Edit Target Fields")
        parent_layout = QVBoxLayout()
        model_name = self.noteTypeComboBox.currentText()

        def switch_focus(field):
            self.focus_input = field

        all_fields_layout = QVBoxLayout()
        if model_name:
            model = mw.col.models.byName(model_name)
            fields_dict = {
                field: QLineEdit(self.target_fields.get(field))
                for field in [f['name'] for f in model['flds']]
            }
            for field, field_input in fields_dict.items():
                field_label = QLabel(field)
                field_input.focusInEvent = lambda evt, f=field: switch_focus(f)
                single_field_layout = QHBoxLayout()
                single_field_layout.addWidget(field_label)
                single_field_layout.addStretch()
                single_field_layout.addWidget(field_input)
                all_fields_layout.addLayout(single_field_layout)

        quick_input_button_layout = QHBoxLayout()
        for k, v in self.settings.items():
            if k[-5:] == "Field":
                quick_input_button = QPushButton(v.capitalize())
                quick_input_button.clicked.connect(
                    lambda evt, t=v: append_text(t)
                )
                quick_input_button_layout.addWidget(quick_input_button)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Close | QDialogButtonBox.Save
        )
        button_box.accepted.connect(edit_fields_dialog.accept)
        button_box.rejected.connect(edit_fields_dialog.reject)
        button_box.setOrientation(Qt.Horizontal)

        parent_layout.addLayout(quick_input_button_layout)
        parent_layout.addLayout(all_fields_layout)
        parent_layout.addWidget(button_box)

        def append_text(target_input):
            target = fields_dict.get(self.focus_input)
            if target:
                prev_text = target.text()
                target.setText(prev_text + "{{{{{0}}}}}".format(target_input))
                target.update()

        def edit_fields_key_handler(evt, _orig):
            handled = False
            if evt.key() in (Qt.Key_Escape, Qt.Key_Enter, Qt.Key_Return):
                edit_fields_dialog.accept()
                handled = True
            if not handled:
                return _orig(self)

        edit_fields_dialog.setLayout(parent_layout)
        orig_edit_fields_dialog_handler = edit_fields_dialog.keyPressEvent
        edit_fields_dialog.keyPressEvent = lambda evt: edit_fields_key_handler(evt, orig_edit_fields_dialog_handler)
        irx_info_box("firstTimeViewingTargetFields", parent=edit_fields_dialog)
        ret = edit_fields_dialog.exec_()

        if ret == 1:
            self.target_fields = {k: v.text() for (k, v) in fields_dict.items()}

    def clear_quick_keys_dialog(self):
        self.quickKeysComboBox.setCurrentIndex(0)
        self.destDeckComboBox.setCurrentIndex(0)
        self.noteTypeComboBox.setCurrentIndex(0)
        self.ctrlKeyCheckBox.setChecked(False)
        self.shiftKeyCheckBox.setChecked(False)
        self.altKeyCheckBox.setChecked(False)
        self.regular_key_input.clear()
        self.quickKeyEditExtractCheckBox.setChecked(False)
        self.quickKeyEditSourceCheckBox.setChecked(False)
        self.quickKeyPlainTextCheckBox.setChecked(False)
        self.bg_edit_label.set_rgba(initial=True)

    def delete_quick_key(self):
        quick_key = self.quickKeysComboBox.currentText()
        if quick_key:
            self.settings['quickKeys'].pop(mac_fix(quick_key, reverse=True))
            removeComboBoxItem(self.quickKeysComboBox, quick_key)
            self.clear_quick_keys_dialog()

    def save_quick_key(self):
        quick_key = {
            'deckName': self.destDeckComboBox.currentText(),
            'modelName': self.noteTypeComboBox.currentText(),
            'fields': self.target_fields,
            'ctrl': self.ctrlKeyCheckBox.isChecked(),
            'shift': self.shiftKeyCheckBox.isChecked(),
            'alt': self.altKeyCheckBox.isChecked(),
            'meta': self.metaKeyCheckBox.isChecked(),
            'regularKey': self.regular_key_input.text().lower(),
            'editExtract': self.quickKeyEditExtractCheckBox.isChecked(),
            'editSource': self.quickKeyEditSourceCheckBox.isChecked(),
            'plainText': self.quickKeyPlainTextCheckBox.isChecked(),
            'bg': self.bg_edit_label.selected_rgba(),
        }

        valid_quick_key = self.validate_new_quick_key(quick_key)
        if valid_quick_key:
            info_msg = "Updated quick key: {}" if valid_quick_key.keys(
            )[0] in self.settings['quickKeys'].keys(
            ) else "New quick key added: {}"
            self.settings['quickKeys'].update(valid_quick_key)
            self.refresh_menu_items()
            key_combo = mac_fix(valid_quick_key.keys()[0])
            showInfo(info_msg.format(key_combo))
            addComboBoxItem(self.quickKeysComboBox, key_combo)

    def validate_new_quick_key(self, quick_key):
        required = ['deckName', 'modelName', 'regularKey']
        for req in required:
            if not quick_key.get(req):
                missing_setting = {
                    'deckName': "Deck Name",
                    'modelName': "Note Type",
                    'regularKey': "Regular Key",
                }
                showInfo(
                    "The <font color='red'>{0}</font> cannot be left blank.".
                    format(missing_setting.get(req))
                )
                return False

        filled_in_fields = [
            trg_field for trg_field in quick_key['fields'].values() if trg_field
        ]
        if not filled_in_fields:
            showInfo(
                "None of the <font color='red'>target fields</font> have any content."
            )
            return False

        key_combo = ''
        if quick_key['ctrl']:
            key_combo += 'Ctrl+'
        if quick_key['shift']:
            key_combo += 'Shift+'
        if quick_key['alt']:
            key_combo += 'Alt+'
        if quick_key['meta']:
            key_combo += 'Meta+'
        key_combo += quick_key['regularKey']

        irx_controls = [
            ctrl.lower() for ctrl in self.settings['irx_controls'].keys()
        ]
        if key_combo.lower() in irx_controls:
            conflicting_action = [
                k for k, v in self.user_controls_config['reviewer'].items()
                if key_combo.lower() in v.lower()
            ][0]
            showInfo(
                "<font color='red'>Keycombo clash</font> with existing action: <br/><br/> <b>{}</b>"
                .format(conflicting_action)
            )
            return False

        return {key_combo: quick_key}
