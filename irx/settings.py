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
    mac_fix, db_log, pretty_date, destroy_layout, timestamp_id
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
        self.schedules = []
        self.settings_changed = False
        self.irx_controls, self.irx_actions = self.build_control_map()

        self.load_settings()
        if self.settings_changed:
            tooltip("<b>IR3X</b>: Settings updated.")

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

        captioning_layout = QVBoxLayout()
        captioning_layout.addWidget(self.create_image_caption_group_box())
        captioning_widget = QWidget()
        captioning_widget.setLayout(captioning_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)

        main_layout = QVBoxLayout()
        main_layout.addWidget(zoom_scroll_widget)
        main_layout.addWidget(captioning_widget)
        main_layout.addWidget(button_box)

        dialog.setLayout(main_layout)
        dialog.setWindowTitle('IR3X Settings')
        dialog.exec_()

        self.settings['zoomStep'] = self.zoomStepSpinBox.value() / 100.0
        self.settings['generalZoom'] = self.generalZoomSpinBox.value() / 100.0
        self.settings['lineScrollFactor'] = self.lineStepSpinBox.value() / 100.0
        self.settings['pageScrollFactor'] = self.pageStepSpinBox.value() / 100.0
        test_caption_format = pretty_date(
            self.image_caption_edit_box.text(), 'invalid'
        )
        self.settings['captionFormat'] = self.image_caption_edit_box.text(
        ) if test_caption_format != 'invalid' else self.settings['captionFormat']

        mw.viewManager.resetZoom(mw.state)

    def show_scheduling(self):

        main_layout = QVBoxLayout()

        schedules_container_layout = QVBoxLayout()
        self.schedules_layout = QVBoxLayout()

        for sid in [
            str(s)
            for s in sorted([int(i) for i in self.settings["schedules"]])
        ]:
            sched_layout, sched_dict = self._create_schedule_row(
                self.settings["schedules"][sid], rem=(sid not in ["1", "2"])
            )
            self.schedules_layout.addLayout(sched_layout)
            self.schedules.append(sched_dict)

        add_button_layout = QHBoxLayout()
        add_button = QPushButton("+")

        def add_new_schedule(evt):
            sched_layout, sched_dict = self._create_schedule_row()
            self.schedules_layout.addLayout(sched_layout)
            self.schedules.append(sched_dict)

        add_button.clicked.connect(add_new_schedule)
        add_button_layout.setAlignment(Qt.AlignHCenter)
        add_button_layout.addWidget(add_button)

        schedules_container_layout.addLayout(self.schedules_layout)
        schedules_container_layout.addLayout(add_button_layout)
        schedules_container_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.validate_and_save_schedules)

        main_layout.addLayout(schedules_container_layout)
        main_layout.addWidget(button_box)

        self.schedules_dialog = QDialog(mw)
        self.schedules_dialog.setLayout(main_layout)
        self.schedules_dialog.setWindowTitle('IR3X Scheduling')
        self.schedules_dialog.exec_()

    def validate_and_save_schedules(self):
        sched_names = [s["name"]() for s in self.schedules]
        duplicate_names = list(
            set([name for name in sched_names if sched_names.count(name) > 1])
        )
        if duplicate_names:

            def validate(evt, src, excl):
                if evt in excl:
                    src.setStyleSheet('QLineEdit{ background-color:#FFAD9F; }')
                else:
                    src.setStyleSheet('QLineEdit{ background-color:#FFFFFF; }')

            showInfo("All schedules must have a unique name.")
            for i in range(2, self.schedules_layout.count()):
                layout = self.schedules_layout.itemAt(i)
                name_input = layout.itemAt(0).widget()
                if name_input.text() in duplicate_names:
                    name_input.setStyleSheet(
                        'QLineEdit{ background-color:#FFAD9F; }'
                    )
                    name_input.textChanged.connect(lambda evt, src=name_input: validate(evt, src, sched_names))
            return

        self.settings["schedules"] = {}
        for schedule in self.schedules:
            self.settings["schedules"][schedule["id"]] = {
                k: v()
                for k, v in schedule.items() if k not in ["remove", "id"]
            }
            self.settings["schedules"][schedule["id"]]["id"] = schedule["id"]

        self.schedules = []
        self.schedules_dialog.accept()

    def _create_schedule_row(self, schedule=None, rem=True):
        def remove_schedule(sid):
            index = self.schedules.index(
                [s for s in self.schedules if s["id"] == sid][0]
            )
            layout = self.schedules_layout.itemAt(index)
            destroy_layout(layout)
            self.schedules_layout.removeItem(layout)
            self.schedules_layout.update()
            del layout
            del self.schedules[index]

        schedule = schedule or {}
        if not rem:
            name_widget = QLabel(schedule.get('name'))
        else:
            name_widget = QLineEdit()
            name_widget.setText(schedule.get('name', ""))
        name_widget.setFixedWidth(150)
        value_edit_box = QLineEdit()
        value_edit_box.setFixedWidth(50)
        percent_button = QRadioButton('Percent')
        position_button = QRadioButton('Position')
        random_check_box = QCheckBox('Randomize')
        sched_id = str(schedule.get("id", timestamp_id()))
        remove_button = QPushButton("-")
        remove_button.setEnabled(rem)
        remove_button.clicked.connect(lambda evt: remove_schedule(sched_id))
        layout = QHBoxLayout()
        layout.addWidget(name_widget)
        layout.addStretch()
        layout.addWidget(value_edit_box)
        layout.addWidget(percent_button)
        layout.addWidget(position_button)
        layout.addWidget(random_check_box)
        layout.addWidget(remove_button)
        button_group = QButtonGroup(layout)
        button_group.addButton(percent_button)
        button_group.addButton(position_button)
        value_edit_box.setText(str(schedule.get("value", "")))
        percent_button.setChecked(schedule.get('method') == "percent")
        position_button.setChecked(schedule.get('method') == "position")
        random_check_box.setChecked(schedule.get('random', False))
        sched_dict = {
            "id":
                sched_id,
            "name":
                lambda: name_widget.text(),
            "value":
                lambda: value_edit_box.text(),
            "method":
                lambda: "percent" if percent_button.isChecked() else "position",
            "random":
                lambda: random_check_box.isChecked(),
            "remove":
                remove_button
        }
        return layout, sched_dict

    def save_settings(self):
        with open(self.json_path, 'w', encoding='utf-8') as json_file:
            self.settings["irx_controls"] = {}
            json.dump(self.settings, json_file, indent=4)
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
            'plainText': False,
            "editExtract": False,
            "editSource": False,
            "extractDeck": None,
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
            'schedules':
                {
                    "1":
                        {
                            "id": 1,
                            "name": "soon",
                            "value": 10,
                            "method": "percent",
                            "random": True,
                        },
                    "2":
                        {
                            "id": 2,
                            "name": "later",
                            "value": 50,
                            "method": "percent",
                            "random": True,
                        }
                },
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
            if (k not in self.settings
               ) or (k == "schedules" and not self.settings[k]):
                self.settings[k] = v
                self.settings_changed = True
