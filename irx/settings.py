# -*- coding: utf-8 -*-

from __future__ import unicode_literals, division
from codecs import open
from functools import partial
from sys import getfilesystemencoding
from math import floor, ceil
import json
import os
import re
import operator
import copy

from PyQt4.QtCore import Qt, QUrl, QVariant
from PyQt4.QtGui import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget, QDesktopServices, QColorDialog, QColor,
    QIcon, QLayout, QSlider
)

from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo, tooltip

from irx.util import (
    addMenuItem, removeComboBoxItem, setComboBoxItem, updateModificationTime,
    mac_fix, db_log, pretty_date, destroy_layout, timestamp_id, is_valid_number,
    validation_style, hex_to_rgb, irx_file_path, keypress_capture_field, capitalize_phrase, 
    pretty_byte_value, color_picker_label, irx_info_box
)

from irx.editable_controls import REVIEWER_CONTROLS, IMAGE_MANAGER_CONTROLS


REVIEWER_FUNCTIONS = {
    "show help": lambda: mw.readingManagerX.settingsManager.show_help(),
    "toggle images": lambda: mw.readingManagerX.textManager.toggle_images_sidebar(),
    "toggle formatting": lambda: mw.readingManagerX.textManager.toggle_show_formatting(),
    "toggle removed text": lambda: mw.readingManagerX.textManager.toggle_show_removed(),
    "toggle extracts": lambda: mw.readingManagerX.textManager.toggle_show_extracts(),
    "done (suspend)": lambda: mw.readingManagerX.scheduler.done_with_note(),
    "undo": lambda: mw.readingManagerX.textManager.undo(),
    "add image": lambda: mw.readingManagerX.textManager.extract_image(),
    "add image (skip caption)": lambda: mw.readingManagerX.textManager.extract_image(skip_captions=True),
    "extract image": lambda: mw.readingManagerX.textManager.extract_image(remove_src=True),
    "extract image (skip caption)": lambda: mw.readingManagerX.textManager.extract_image(remove_src=True, skip_captions=True),
    "extract important": lambda: mw.readingManagerX.textManager.extract(schedule_name="soon"),
    "extract complimentary": lambda: mw.readingManagerX.textManager.extract(schedule_name="later"),
    "extract important (and edit)": lambda: mw.readingManagerX.textManager.extract(also_edit=True, schedule_name="soon"),
    "extract complimentary (and edit)": lambda: mw.readingManagerX.textManager.extract(also_edit=True, schedule_name="later"),
    "bold": lambda: mw.readingManagerX.textManager.style("bold"),
    "underline": lambda: mw.readingManagerX.textManager.style("underline"),
    "italic": lambda: mw.readingManagerX.textManager.style("italic"),
    "strikethrough": lambda: mw.readingManagerX.textManager.style("strikeThrough"),
    "remove": lambda: mw.readingManagerX.textManager.remove(),
    "show reading list": lambda: mw.readingManagerX.scheduler.show_organizer(),
    "show image manager": lambda: mw.readingManagerX.textManager.manage_images(),
    "zoom in": lambda: mw.viewManager.zoomIn(),
    "zoom out": lambda: mw.viewManager.zoomOut(),
    "line up": lambda: mw.viewManager.lineUp(),
    "line down": lambda: mw.viewManager.lineDown(),
    "page up": lambda: mw.viewManager.pageUp(),
    "page down": lambda: mw.viewManager.pageDown(),
    "next card": lambda: mw.readingManagerX.next_irx_card(),
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
        self.actions_by_category = {
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
                    "toggle help",
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
                self.quick_keys_action_format().keys(),
            "Scheduling (Highlighting)":
                self.schedule_keys_action_format().keys()
        }
        if self.duplicate_controls:
            self.show_help()
        addHook('unloadProfile', self.save_settings)

    def reset_info_flags(self):
        for flag in self.settings['infoMsgFlags']:
            self.settings['infoMsgFlags'][flag] = True
        self.save_settings()
        tooltip("<b>IR3X</b>: Info message flags reset.")

    def refresh_schedule_menu_items(self):
        for action in mw.readingManagerX.schedule_key_actions:
            mw.customMenus['IR3X::Schedules'].removeAction(action)
        mw.readingManagerX.schedule_key_actions = []

        schedules = ((int(schedule["anskey"] or 10), schedule["name"]) for schedule in self.settings['schedules'].values())
        schedules_sorted = sorted(schedules, key=operator.itemgetter(0))
        for anskey, name in schedules_sorted:
            mw.readingManagerX.schedule_key_actions.append(
                addMenuItem(
                    menuName='IR3X::Schedules',
                    text=name,
                    function=partial(
                        mw.readingManagerX.textManager.extract,
                        schedule_name=name
                    ),
                    keys=str(anskey if anskey!= 10 else "") or None
                )
            )

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
            [values.split(" ") for key, values in all_irx_actions.items() if key not in IMAGE_MANAGER_CONTROLS.keys()], []
        )
        duplicate_controls = list(
            set([key for key in keys if keys.count(key) > 1])
        )
        if duplicate_controls:
            showInfo(
                """IR3X made an oopsie! Found some conflicting hotkey settings. <br/><br/>\
                I'll bring up the help menu which'll highlight the conflicting keys in red <br/><br/>\
                Review your <code>editable_controls.py</code> file, quick keys settings or schedule answer keys. <br/><br/>""",
                type="warning",
                title="IR3X Controls"
            )
        return duplicate_controls

    def get_all_registered_irx_actions(self):
        actions_keys_index = copy.deepcopy(self.irx_actions)
        quick_keys_actions = self.quick_keys_action_format()
        actions_keys_index.update(quick_keys_actions)
        schedule_keys_actions = self.schedule_keys_action_format()
        actions_keys_index.update(schedule_keys_actions)
        return actions_keys_index

    def show_help(self):
        help_dialog = QDialog(mw)
        help_cat_boxes = [
            self.make_help_group(
                cat, acts, self.get_all_registered_irx_actions()
            ) for cat, acts in self.actions_by_category.items() if acts
        ]
        help_cat_boxes = [h for h in help_cat_boxes if h]
        help_layout = QVBoxLayout()
        num_rows = 4
        one_row_width = int(ceil(len(help_cat_boxes) / num_rows))
        help_rows_layouts = [QHBoxLayout() for i in range(num_rows)]
        for i, help_cat_box in enumerate(help_cat_boxes):
            row = int(i / one_row_width)
            help_rows_layouts[row].addWidget(help_cat_box)

        for help_row_layout in help_rows_layouts:
            help_layout.addLayout(help_row_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        help_layout.addWidget(button_box)
        help_dialog.setLayout(help_layout)
        help_dialog.setWindowModality(Qt.WindowModal)
        button_box.accepted.connect(help_dialog.accept)

        def hide_help(evt, _orig):
            if unicode(evt.text()) in REVIEWER_CONTROLS["show help"].split(" "):
                help_dialog.accept()
            else:
                return _orig(evt)

        orig_dialog_handler = help_dialog.keyPressEvent
        help_dialog.keyPressEvent = lambda evt: hide_help(evt, orig_dialog_handler)

        help_dialog.exec_()

    def make_help_group(self, category, actions=None, keys_index=None):
        keys_index = keys_index or self.get_all_registered_irx_actions()
        actions = actions or self.actions_by_category.get(category)
        if not actions:
            return False
        controls_layout = QVBoxLayout()
        active_actions = [a for a in actions if a in keys_index.keys()] 
        for action in active_actions:
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

        return category_box if active_actions else False 

    def quick_keys_action_format(self):
        quick_keys_dict = {}
        for key, params in self.settings['quickKeys'].items():
            dict_key = "{0} -> {1}".format(
                params['modelName'], params['deckName']
            )
            quick_keys_dict[dict_key] = quick_keys_dict.get(dict_key,
                                                            []) + [key]
        return {mac_fix(k): " ".join(v) for k, v in quick_keys_dict.items()}

    def schedule_keys_action_format(self, action_major=True):
        return {
            (schedule["name"] if action_major else schedule["anskey"]):
            (schedule["anskey"] if action_major else schedule["name"])
            for schedule in self.settings['schedules'].values()
        }

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
        irx_info_box(
            flag_key='firstTimeViewingSettings',
            text="IR3X Settings",
            info_texts=[
                "These should be quite self-explenatory, Zoom and Scroll settings work exactly the same as in the original add-on",
                "The new settings allow you to define the maximum size for imported images which IR3X when compressing images.",
                "The Auto-caption setting is used to define the atuomatic caption that is assigned to an image when IR3X cannot extract one from the clipboard.",
                "This setting supports <code>strftime</code> formatting (click on the button next to the input for more info), a live preview is displayed below the input.",
                "If the inputted template is invalid (error message displayed), any changes will be discarded."
            ],
            parent=dialog
        )
        if not dialog.exec_():
            return
        
        self.settings['zoomStep'] = self.zoomStepSpinBox.value() / 100.0
        self.settings['generalZoom'] = self.generalZoomSpinBox.value() / 100.0
        self.settings['lineScrollFactor'] = self.lineStepSpinBox.value() / 100.0
        self.settings['pageScrollFactor'] = self.pageStepSpinBox.value() / 100.0
        self.settings['maxImageBytes'] = self.compression_slider_pref.value()
        test_caption_format = pretty_date(
            self.image_caption_edit_box.text(), 'invalid'
        )
        self.settings['captionFormat'] = self.image_caption_edit_box.text(
        ) if test_caption_format != 'invalid' else self.settings['captionFormat']

        mw.viewManager.resetZoom(mw.state)

    def create_image_caption_group_box(self):
        parent_layout = QVBoxLayout()

        compression_layout = QHBoxLayout()
        compression_label = QLabel("Max Size")
        self.compression_slider_pref = QSlider(Qt.Horizontal)
        self.compression_slider_pref.setMinimum(102400) # 100K
        self.compression_slider_pref.setMaximum(5242880) # 5M
        self.compression_slider_pref.setSingleStep(51200) # 50K
        self.compression_slider_pref.setPageStep(102400) # 100K
        self.compression_slider_pref.setFixedWidth(250)
        self.compression_slider_pref.setTickPosition(QSlider.TicksBelow)
        self.compression_slider_pref.setTickInterval(1048576)
        self.compression_slider_pref.setValue(self.settings["maxImageBytes"])

        slider_value_label = QLabel(pretty_byte_value(self.compression_slider_pref.value()))
        slider_value_label.setFixedWidth(40)
        compression_layout.addWidget(compression_label)
        compression_layout.addStretch()
        compression_layout.addWidget(self.compression_slider_pref)
        compression_layout.addWidget(slider_value_label)
        slider_value_label.setAlignment(Qt.AlignCenter)
        self.compression_slider_pref.valueChanged.connect(lambda evt, lab=slider_value_label: lab.setText(pretty_byte_value(evt)))

        caption_format_layout = QHBoxLayout()
        caption_format_label = QLabel('Auto-Caption')
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

        parent_layout.addLayout(compression_layout)
        parent_layout.addLayout(caption_format_layout)
        parent_layout.addStretch()
        parent_layout.addLayout(caption_preview_layout)

        group_box = QGroupBox('Image')
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
            'prevContainerDeck': '~IR3X',
            'containerDeck': '~IR3X',
            'modelName': 'IR3X',
            'captionFormat': "%A, %d %B %Y %H:%M",
            'maxImageBytes': 1048576,
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
                            "anskey": "1",
                            "bg": "rgba(255, 0, 0, 60%)"
                        },
                    "2":
                        {
                            "id": 2,
                            "name": "later",
                            "value": 50,
                            "method": "percent",
                            "random": True,
                            "anskey": "2",
                            "bg": "rgba(0, 255, 0, 60%)"
                        }
                },
            'scroll': {},
            'zoom': {},
            'infoMsgFlags': {}
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

    def add_missing_settings(self):
        for k, v in self.defaults.items():
            no_sched = (k == "schedules" and not self.settings[k])
            if (k not in self.settings) or no_sched:
                self.settings[k] = v
                self.settings_changed = True

    def show_scheduling(self):
        self.schedules = []
        self.schedules_layout = QVBoxLayout()
        self.schedules_layout.setSizeConstraint(QLayout.SetFixedSize)
        main_layout = QVBoxLayout()
        main_layout.setSizeConstraint(QLayout.SetFixedSize)
        schedules_container_layout = QVBoxLayout()
        schedules_container_layout.setSizeConstraint(QLayout.SetFixedSize)

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
        irx_info_box(
            flag_key='firstTimeViewingSchedules',
            text="How IR3X Schedules Work",
            info_texts=[
                "IR3X does away with the original highlight option in favor of extracts. In IR3X terms, <b>extracts = highlights = extracts</b>",
                "This means that anything that is highlighted in an IR3X represents another note, which can be either another IR3X note or another type of Anki note",
                "Schedules deal with the former, while the latter are configurable through Quick Keys.",
                "When viewing IR3X text, extracts can be created by highlighting text and using the assigned <b>Answer Key</b>",
                "Answer keys can be any value between 1 and 9. A schedule can also have no answer key assigned to it, in that case the schedule is considered <b>inactive</b>",
                "You can still use an inactive schedule but only through the Schedules Menu, not through a keyboard shortcut.",
                "Moreover, the primary difference is that <b>active schedules will also appear as answer buttons on the answer card</b>.",
                "You can re-schedule an IR3X note before moving on to the next from the answer screen using the schedule answer key.",
                "This means at any time you can have <b>up to 9 active schedules</b> as a way of assigning priorities to IR3X notes.",
                "Finally, IR3X also tried to intelligently assign a title to an extract based on the title of its parent for efficiency.",
                "Should you want to change this, all extracts also serve as hyperlinks to the created notes, clicking on them will open the editor to make any changes."
            ],
            modality=Qt.WindowModal,
            parent=self.schedules_dialog
        )
        self.schedules_dialog.exec_()

    def validate_and_save_schedules(self):
        errors = self.check_for_invalid_sched_names()
        errors += self.check_for_invalid_sched_values()
        errors += self.check_for_invalid_sched_anskeys()
        if errors:
            showInfo(
                "There are problems with your schedules: <br/><br/>{}".format(
                    "<br/>".join(list(set(errors)))
                )
            )
            return

        self.settings["schedules"] = {}
        for schedule in self.schedules:
            self.settings["schedules"][schedule["id"]] = {
                k: v()
                for k, v in schedule.items() if k not in ["remove", "id"]
            }
            self.settings["schedules"][schedule["id"]]["id"] = schedule["id"]
        self.refresh_schedule_menu_items()

        self.schedules = []
        self.schedules_dialog.accept()

    def check_for_invalid_sched_values(self):
        invalid_scheds = []
        errors = []
        for i, v in enumerate(self.schedules):
            widget = self.schedules_layout.itemAt(i).itemAt(1).widget()
            valid, errs = self.validate_sched_value(
                value=v["value"](), method=v["method"](), src=widget
            )
            if not valid:
                invalid_scheds.append(i)
                errors += errs
        return errors

    def check_for_invalid_sched_names(self):
        invalid_scheds = []
        errors = []
        for i, v in enumerate(self.schedules):
            widget = self.schedules_layout.itemAt(i).itemAt(0).widget()
            valid, errs = self.validate_sched_name(v["name"](), src=widget)
            if not valid:
                invalid_scheds.append(i)
                errors += errs
        return errors

    def check_for_invalid_sched_anskeys(self):
        invalid_scheds = []
        errors = []
        for i, v in enumerate(self.schedules):
            widget = self.schedules_layout.itemAt(i).itemAt(5).widget()
            valid, errs = self.validate_sched_anskey(v["anskey"](), src=widget)
            if not valid:
                invalid_scheds.append(i)
                errors += errs
        return errors

    def validate_sched_value(self, value=None, method=None, src=None, method_widget=None):
        value = src.text() if src else value
        method = method or (
            "percent" if method_widget.isChecked() else "position"
        )
        valid = True
        error_msgs = []
        if not value:
            error_msgs.append("Schedule value cannot be empty.")
            valid = False
        elif not is_valid_number(value, decimal=False):
            error_msgs.append("{} is an invalid value.".format(value))
            valid = False
        else:
            if int(value) <= 0:
                error_msgs.append("Value has to be greater or equal to 1")
                valid = False
            elif method == "percent" and not (1 <= int(value) <= 100):
                error_msgs.append(
                    "{} is an invalid percent value.".format(value)
                )
                valid = False

        if src:
            validation_style(src, valid)
        return valid, error_msgs

    def validate_sched_name(self, value=None, src=None):
        sched_names = [s["name"]() for s in self.schedules]
        duplicate_names = list(
            set([name for name in sched_names if sched_names.count(name) > 1])
        )
        value = src.text() if src else value
        valid = True
        error_msgs = []
        if not value:
            error_msgs.append("Schedule name cannot be empty.")
            valid = False
        elif value in duplicate_names:
            error_msgs.append("All schedule names must be unique.")
            valid = False
        if src:
            validation_style(src, valid)
        return valid, error_msgs

    def validate_sched_anskey(self, value=None, src=None, name=None):
        sched_anskeys = [s["anskey"]() for s in self.schedules]
        duplicate_anskeys = list(
            set(
                [
                    anskey for anskey in sched_anskeys
                    if sched_anskeys.count(anskey) > 1
                ]
            )
        )
        value = src.text() if src else value
        control_conflicts = [
            k for k, v in self.irx_actions.items() if value in v.split(" ")
        ]
        quick_key_conflicts = [
            k for k, v in self.quick_keys_action_format().items()
            if value in v.split(" ")
        ]
        valid = True
        error_msgs = []
        if value in duplicate_anskeys:
            error_msgs.append("Answer keys must be unique (or left blank).")
            valid = False
        elif control_conflicts:
            error_msgs.append(
                "<font color='red'>{0}</font> conflicts with key for <b>{1}</b>."
                .format(value, control_conflicts[0])
            )
            valid = False
        elif quick_key_conflicts:
            error_msgs.append(
                "<font color='red'>{0}</font> conflicts with quick key for <b>{1}</b>."
                .format(value, quick_key_conflicts[0])
            )
            valid = False
        if src:
            validation_style(src, valid)
        return valid, error_msgs

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
            self.schedules_dialog.adjustSize()

        def validate_all(evt, val_fn, pos, **kwargs):
            for i in range(self.schedules_layout.count()):
                widget = self.schedules_layout.itemAt(i).itemAt(pos).widget()
                val_fn(src=widget, **kwargs)

        schedule = schedule or {}
        if not rem:
            name_widget = QLabel(capitalize_phrase(schedule.get('name')))
        else:
            name_widget = QLineEdit()
            name_widget.setText(capitalize_phrase(schedule.get('name', "Schedule Name")))
            name_widget.textChanged.connect(lambda evt, val_fn=self.validate_sched_name, pos=0: validate_all(evt, val_fn, pos))
        name_widget.setFixedWidth(150)
        name_widget.setAlignment(Qt.AlignCenter)
        value_edit_box = QLineEdit()
        value_edit_box.setFixedWidth(50)
        percent_button = QRadioButton('Percent')
        position_button = QRadioButton('Position')
        value_validator = lambda evt, src=value_edit_box, _method=percent_button: self.validate_sched_value(value=evt, src=src, method_widget=_method)
        value_edit_box.textChanged.connect(value_validator)
        percent_button.clicked.connect(value_validator)
        position_button.clicked.connect(value_validator)
        random_check_box = QCheckBox('Randomize')
        sched_id = str(schedule.get("id", timestamp_id()))
        bg_edit_label = color_picker_label(schedule.get("bg"))
        _orig_press = bg_edit_label.mousePressEvent 
        def _mod_press(*args, **kwargs):
            irx_info_box(
                flag_key='editingScheduleHighlights',
                text="Changing Schedules' Colors",
                info_texts=[
                    "Any highlight changes will only apply from this point forward.",
                    "Existing highlights will <b>not</b> be updated."
                ],
                modality=Qt.WindowModal,
                parent=self.schedules_dialog
            )
            _orig_press(*args, **kwargs)
        bg_edit_label.mousePressEvent = _mod_press
        _orig_wheel = bg_edit_label.wheelEvent 
        def _mod_wheel(*args, **kwargs):
            irx_info_box(
                flag_key='editingScheduleHighlights',
                text="Changing Schedules' Colors",
                info_texts=[
                    "Any highlight changes will only apply from this point forward.",
                    "Existing highlights will <b>not</b> be updated."
                ],
                modality=Qt.WindowModal,
                parent=self.schedules_dialog
            )
            _orig_wheel(*args, **kwargs)
        bg_edit_label.wheelEvent = _mod_wheel

        answer_key_label = QLabel("Key [1-9]")
        answer_key_input = keypress_capture_field('123456789')
        answer_key_input.textChanged.connect(lambda evt, val_fn=self.validate_sched_anskey, pos=5: validate_all(evt, val_fn, pos))
        remove_button = QPushButton()
        remove_button.setEnabled(rem)
        remove_button.clicked.connect(lambda evt: remove_schedule(sched_id))
        remove_button.setIcon(QIcon(irx_file_path("cancel.png")))
        layout = QHBoxLayout()
        layout.addWidget(name_widget)
        layout.addWidget(value_edit_box)
        layout.addWidget(percent_button)
        layout.addWidget(position_button)
        layout.addWidget(random_check_box)
        layout.addWidget(answer_key_input)
        layout.addWidget(answer_key_label)
        layout.addWidget(bg_edit_label)
        layout.addStretch()
        layout.addWidget(remove_button)
        button_group = QButtonGroup(layout)
        button_group.addButton(percent_button)
        button_group.addButton(position_button)
        value_edit_box.setText(str(schedule.get("value", "")))
        percent_button.setChecked(
            schedule.get('method', "percent") == "percent"
        )
        position_button.setChecked(schedule.get('method') == "position")
        random_check_box.setChecked(schedule.get('random', False))
        answer_key_input.setText(str(schedule.get("anskey", "")))
        sched_dict = {
            "id":
                sched_id,
            "name":
                lambda: capitalize_phrase(name_widget.text()),
            "value":
                lambda: value_edit_box.text(),
            "method":
                lambda: "percent" if percent_button.isChecked() else "position",
            "random":
                lambda: random_check_box.isChecked(),
            "bg":
                lambda: bg_edit_label.selected_rgba(),
            "anskey":
                lambda: answer_key_input.text(),
            "remove":
                remove_button
        }
        return layout, sched_dict
