# -*- coding: utf-8 -*-

from __future__ import unicode_literals, division
from codecs import open
from functools import partial
from sys import getfilesystemencoding
from math import floor, ceil
import json
import os

from PyQt4.QtCore import Qt, QUrl
from PyQt4.QtGui import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget, QDesktopServices
)

from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo, tooltip

from irx.util import (
    addMenuItem, removeComboBoxItem, setComboBoxItem, updateModificationTime,
    mac_fix, db_log, pretty_date
)

from irx.editable_controls import REVIEWER_CONTROLS, IMAGE_MANAGER_CONTROLS


REVIEWER_FUNCTIONS = {
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
    "bold": lambda: mw.readingManager.textManager.style("bold"),
    "underline": lambda: mw.readingManager.textManager.style("underline"),
    "italic": lambda: mw.readingManager.textManager.style("italic"),
    "strikethrough": lambda: mw.readingManager.textManager.style("strikeThrough"),
    "remove": lambda: mw.readingManager.textManager.remove(),
    "show reading list": lambda: mw.readingManager.scheduler.show_organizer(),
    "show image manager": lambda: mw.readingManager.textManager.manage_images(),
    "zoom in": lambda: mw.viewManager.zoomIn(),
    "zoom out": lambda: mw.viewManager.zoomOut(),
    "line up": lambda: mw.viewManager.lineUp(),
    "line down": lambda: mw.viewManager.lineDown(),
    "page up": lambda: mw.viewManager.pageUp(),
    "page down": lambda: mw.viewManager.pageDown(),
    "next card": lambda: mw.readingManager.next_irx_card(),
}


class SettingsManager():
    def __init__(self):
        self.settings_changed = False
        self.irx_controls, self.irx_actions = self.build_control_map()

        self.load_settings()
        if self.settings_changed:
            tooltip("IR3X Settings updated.")

        self.duplicate_controls = self.check_for_duplicate_controls()
        addHook('unloadProfile', self.save_settings)

    def build_control_map(self):
        irx_controls = {}
        for key, values in REVIEWER_CONTROLS.items():
            for value in values.split(" "):
                irx_controls[value] = REVIEWER_FUNCTIONS[key]

        irx_actions = REVIEWER_CONTROLS
        irx_actions.update(IMAGE_MANAGER_CONTROLS)
        return irx_controls, irx_actions

    def check_for_duplicate_controls(self):
        all_irx_actions = self.get_all_registered_irx_actions()
        keys = sum(
            [values.split(" ") for values in all_irx_actions.values()], []
        )
        duplicate_controls = list(
            set([key for key in keys if keys.count(key) > 1])
        )
        if duplicate_controls:
            showInfo(
                "There are conflicting keys in your <code>editable_controls.py</code> settings, open IR3X help for more info."
            )
        return duplicate_controls

    def get_all_registered_irx_actions(self):
        actions_keys_index = self.irx_actions
        quick_keys_actions = self.quick_keys_action_format()
        actions_keys_index.update(quick_keys_actions)
        return actions_keys_index

    def show_help(self):
        action_categories = {
            "General Controls":
                [
                    "remove",
                    "undo",
                    "done (suspend)",
                    "next card",
                    "show help",
                    "show reading list",
                    "show image manager",
                ],
            "Text Fomatting": [
                "bold",
                "underline",
                "italic",
                "strikethrough",
            ],
            "Text Highlighting (Extracts)":
                [
                    "extract important",
                    "extract complimentary",
                    "extract important (and edit)",
                    "extract complimentary (and edit)",
                ],
            "Importing Images":
                [
                    "extract image",
                    "extract image (skip caption)",
                    "add image",  #todo rename this to import image
                    "add image (skip caption)",
                ],
            "Visual Elements":
                [
                    "toggle images",
                    "toggle formatting",
                    "toggle removed text",
                    "toggle extracts",
                ],
            "Image Manager":
                [
                    "edit image caption",
                    "mark image(s) for deletion",
                    "take image(s) (for reordering)",
                    "place image(s) above (for reordering)",
                    "place image(s) below (for reordering)",
                    "submit image changes",
                ],
            "Navigation Controls":
                [
                    "zoom in",
                    "zoom out",
                    "line up",
                    "line down",
                    "page up",
                    "page down",
                ],
            "Quick Keys":
                self.quick_keys_action_format().keys()
        }

        help_dialog = QDialog(mw)
        help_cat_boxes = [
            self.make_help_group(
                cat, acts, self.get_all_registered_irx_actions()
            ) for cat, acts in action_categories.items() if acts
        ]
        help_layout = QVBoxLayout()
        num_rows = 4
        one_row_width = int(ceil(len(help_cat_boxes) / num_rows))
        help_rows_layouts = [QHBoxLayout() for i in range(num_rows)]
        for i, help_cat_box in enumerate(help_cat_boxes):
            row = int(i / one_row_width)
            help_rows_layouts[row].addWidget(help_cat_box)

        for help_row_layout in help_rows_layouts:
            help_layout.addLayout(help_row_layout)

        help_dialog.setLayout(help_layout)
        help_dialog.setWindowModality(Qt.WindowModal)

        def hide_help(evt, _orig):
            if unicode(evt.text()) in REVIEWER_CONTROLS["show help"].split(" "):
                help_dialog.accept()
            else:
                return _orig(evt)

        orig_dialog_handler = help_dialog.keyPressEvent
        help_dialog.keyPressEvent = lambda evt: hide_help(evt, orig_dialog_handler)

        help_dialog.exec_()

    def make_help_group(self, category, actions, keys_index):
        controls_layout = QVBoxLayout()
        for action in actions:
            this_action_layout = QHBoxLayout()
            action_label = QLabel(action)
            this_action_layout.addWidget(action_label)
            this_action_layout.addStretch()
            ok_key = '<code><b>{}</b></code>'
            not_ok_key = '<font color="red">{}</font>'.format(ok_key)
            key_combo_label = QLabel(
                " or ".join(
                    [
                        ok_key.format(mac_fix(key))
                        if key not in self.duplicate_controls else
                        not_ok_key.format(mac_fix(key))
                        for key in keys_index[action].split(" ")
                    ]
                )
            )
            this_action_layout.addWidget(key_combo_label)
            controls_layout.addLayout(this_action_layout)

        category_box = QGroupBox(category)
        category_box.setLayout(controls_layout)

        return category_box

    def quick_keys_action_format(self):
        quick_keys_dict = {}
        for key, params in self.settings['quickKeys'].items():
            dkey = "{0} -> {1}".format(params['modelName'], params['deckName'])
            quick_keys_dict[dkey] = quick_keys_dict.get(dkey, []) + [key]
        return {mac_fix(k): " ".join(v) for k, v in quick_keys_dict.items()}

    def show_settings(self):
        dialog = QDialog(mw)

        zoom_scroll_layout = QHBoxLayout()
        zoom_scroll_layout.addWidget(self.create_zoom_group_box())
        zoom_scroll_layout.addWidget(self.create_scroll_group_box())
        zoom_scroll_widget = QWidget()
        zoom_scroll_widget.setLayout(zoom_scroll_layout)

        scheduling_layout = QVBoxLayout()
        scheduling_layout.addWidget(self.create_scheduling_group_box())
        scheduling_widget = QWidget()
        scheduling_widget.setLayout(scheduling_layout)

        captioning_layout = QVBoxLayout()
        captioning_layout.addWidget(self.create_image_caption_group_box())
        captioning_widget = QWidget()
        captioning_widget.setLayout(captioning_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)

        main_layout = QVBoxLayout()
        main_layout.addWidget(zoom_scroll_widget)
        main_layout.addWidget(scheduling_widget)
        main_layout.addWidget(captioning_widget)
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

        test_caption_format = pretty_date(
            self.image_caption_edit_box.text(), 'invalid'
        )
        self.settings['captionFormat'] = self.image_caption_edit_box.text(
        ) if test_caption_format != 'invalid' else self.settings['captionFormat']

        mw.viewManager.resetZoom(mw.state)

    def save_settings(self):
        with open(self.json_path, 'w', encoding='utf-8') as json_file:
            self.settings["irx_controls"] = {}
            json.dump(self.settings, json_file)
            self.settings["irx_controls"] = self.irx_controls

        updateModificationTime(self.media_dir)

    def load_settings(self):
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
            'captionFormat': "%A, %d %B %Y %H:%M",
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

        self.media_dir = os.path.join(mw.pm.profileFolder(), 'collection.media')
        self.json_path = os.path.join(self.media_dir, '_irx.json')

        if os.path.isfile(self.json_path):
            with open(self.json_path, encoding='utf-8') as json_file:
                self.settings = json.load(json_file)
            self.add_missing_settings()
        else:
            self.settings = self.defaults

        self.settings["irx_controls"] = self.irx_controls

    def create_image_caption_group_box(self):
        parent_layout = QVBoxLayout()

        caption_format_layout = QHBoxLayout()
        caption_format_label = QLabel('Format (uses strftime tokens)')
        caption_format_layout.addWidget(caption_format_label)
        caption_format_layout.addStretch()
        self.image_caption_edit_box = QLineEdit()
        self.image_caption_edit_box.setText(self.settings['captionFormat'])
        self.image_caption_edit_box.setFixedWidth(250)
        help_button = QPushButton("?")
        help_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("http://strftime.org/"))
        )

        caption_format_layout.addWidget(self.image_caption_edit_box)
        caption_format_layout.addWidget(help_button)

        caption_preview_layout = QVBoxLayout()
        caption_preview_label = QLabel()
        caption_preview_label.setAlignment(Qt.AlignCenter)
        caption_preview_layout.addWidget(caption_preview_label)

        invalid_format_msg = "<font color='red'><i>Invalid Format (won't save)</i></font>"

        def update_caption_preview(templ_format):
            caption_preview_label.setText(
                pretty_date(templ_format, invalid=invalid_format_msg)
            )
            caption_preview_label.update()

        self.image_caption_edit_box.textChanged.connect(update_caption_preview)

        parent_layout.addLayout(caption_format_layout)
        parent_layout.addStretch()
        parent_layout.addLayout(caption_preview_layout)

        group_box = QGroupBox('Auto-Image Captioning')
        group_box.setLayout(parent_layout)
        update_caption_preview(self.image_caption_edit_box.text())

        return group_box

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

    def create_zoom_group_box(self):
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

    def create_scroll_group_box(self):
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

    def add_missing_settings(self):
        for k, v in self.defaults.items():
            if k not in self.settings:
                self.settings[k] = v
                self.settings_changed = True
