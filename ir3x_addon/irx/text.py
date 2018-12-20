# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
import os
import urllib2
from urllib import quote
import re
import time
from codecs import open
from io import BytesIO
import base64
from os.path import normpath, basename, join, exists
import cPickle as pickle
from cStringIO import StringIO

from PyQt4.QtGui import (
    QApplication, QImage, QAbstractItemView, QDialog, QDialogButtonBox, QPixmap,
    QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QLabel,
    QBrush, QColor, QMessageBox, QProgressDialog
)
from PyQt4.QtWebKit import QWebPage
from PyQt4.QtCore import Qt, QBuffer

from anki.notes import Note
from anki.utils import checksum
from aqt import mw
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.utils import getText, showInfo, tooltip

from BeautifulSoup import BeautifulSoup as bs, Tag as bs_tag

from irx.util import (
    getField, setField, db_log, irx_siblings, pretty_date, timestamp_id, 
    rgba_percent_to_decimal_alpha, compress_image, irx_info_box
)


class TextManager:
    def __init__(self, settings, user_controls_config):
        self.settings = settings
        self.user_controls_config = user_controls_config
        self.history_path = join(
            mw.pm.profileFolder(), "collection.media", "_irx_history.pkl"
        )
        if exists(self.history_path):
            self.history = pickle.load(open(self.history_path, "rb"))
        else:
            self.history = defaultdict(list)

    def clean_history(self, notify=False):
        notes_cleaned = 0
        for nid in self.history.keys():
            try:
                _ = mw.col.getNote(nid); 
            except TypeError:
                self.history.pop(nid)
                notes_cleaned += 1

        if notes_cleaned:
            self._write_history()
            tooltip("<b>IR3X</b>: History cleaned ({} entries removed)".format(notes_cleaned))
        elif notify:
            tooltip("<b>IR3X</b>: History clean")

    def format_text_range(self, attrs):
        identifier = str(int(time.time() * 10))
        js_obj = ",".join(['{0}:"{1}"'.format(k, v) for k, v in attrs.items()])
        mw.web.eval('execCommandOnRange(%s, {%s})' % (identifier, js_obj))
        self.save(linked_nid=attrs.get("link"))

    def style(self, styles):
        irx_info_box('firstTimeStyling')
        self.format_text_range({"styles": styles})

    def remove(self):
        irx_info_box('firstTimeRemovingText')
        self.format_text_range({"remove": ""})

    def link_note(self, note, schedule_name=None, bg_col=None):
        if schedule_name:
            irx_info_box('firstTimeExtractingSchedule')
            sched = [s for s in self.settings["schedules"] if self.settings["schedules"][s]["name"] == schedule_name]
            if not sched:
                raise ValueError("No schedule found with the following name: {}".format(schedule_name))
        else:
            irx_info_box('firstTimeExtractingQuickKey')
        self.format_text_range(
            {
                "bg": rgba_percent_to_decimal_alpha(bg_col or self.settings["schedules"][sched[0]]["bg"]),
                "link": note.id,
            }
        )

    def toggle_images_sidebar(self, manual=None):
        mw.web.eval('toggleImagesSidebar("%s")' % (manual or "toggle"))
        mw.reviewer.card.note().flush()

    def toggle_show_removed(self, manual=None):
        mw.web.eval('toggleRemoved("%s")' % (manual or "toggle"))
        mw.reviewer.card.note().flush()

    def toggle_show_formatting(self, manual=None):
        mw.web.eval('toggleStyles("%s")' % (manual or "toggle"))
        mw.reviewer.card.note().flush()

    def toggle_show_extracts(self, manual=None):
        mw.web.eval('toggleHighlights("%s")' % (manual or "toggle"))
        mw.reviewer.card.note().flush()

    def manage_images(self, note=None):
        irx_info_box('firstTimeOpeningImageManager')
        note = note or mw.reviewer.card.note()
        soup = bs(getField(note, self.settings["imagesField"]))

        def image_list(soup):
            images = []
            for div in soup.findAll(
                'div', attrs={'class': 'irx-img-container'}
            ):
                images.append(
                    {
                        "id":
                            div.get('id'),
                        "caption":
                            div.findChild(
                                'span', attrs={
                                    "class": "irx-caption"
                                }
                            ).text,
                        "src":
                            div.findAll('a')[0].get('href'),
                        "thumb":
                            div.findChild('img').get('irx-src'),
                        "url":
                            div.findAll('a')[1].get('href')
                            if len(div.findAll('a')) == 2 else None,
                        "html":
                            str(div.extract())
                    }
                )
            return images

        images = image_list(soup)
        if not images:
            tooltip("No images have been extracted from this note")
            return

        self.image_list_widget = QListWidget()
        self.image_list_widget.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.image_list_widget.setWordWrap(False)
        self.image_list_widget.setFixedSize(150, 250)

        std_bg = QColor('#ffffff')
        del_bg = QColor('#f0027f')
        sel_bg = QColor('#386cb0')

        def populate_qlist(images, selected=0):
            self.image_list_widget.clear()
            if not images:
                return
            for image in images:
                item = QListWidgetItem("{}".format(image["caption"]))
                item.setData(Qt.UserRole, image)
                item.setBackground(std_bg)
                self.image_list_widget.addItem(item)
            self.image_list_widget.item(max(selected, 0)).setSelected(True)
            self.image_list_widget.update()

        image_label = QLabel()
        image_label.setFixedSize(300, 250)
        image_label.setAlignment(Qt.AlignCenter)
        image_manager_help_box = mw.readingManagerX.settingsManager.make_help_group('Image Manager')
        image_manager_help_box.setFixedSize(300, 250)
        image_manager_help_box.hide()

        def update_label(clear=False):
            selected = self.image_list_widget.selectedItems()
            if len(selected) == 1:
                image_manager_help_box.hide()
                image = selected[0].data(Qt.UserRole)
                image_label.setPixmap(
                    QPixmap(image["thumb"]).scaled(
                        image_label.maximumWidth(), image_label.maximumHeight(),
                        Qt.KeepAspectRatio
                    )
                )
                image_label.show()
            else:
                image_label.hide()
                image_manager_help_box.show()
            image_label.update()

        def key_handler(evt, _orig):
            key = unicode(evt.text())
            if key == self.user_controls_config["image_manager"]["toggle controls"] or key in [k for k in self.user_controls_config["reviewer"]["show controls"].split(" ") if len(k) == 1]:
                selected = self.image_list_widget.selectedItems()
                if len(selected) == 1:
                    if image_label.isHidden():
                        image_manager_help_box.hide()
                        image_label.show()
                    else:
                        image_label.hide()
                        image_manager_help_box.show()
            elif key == self.user_controls_config["image_manager"]["mark image(s) for deletion"]:
                for selected in self.image_list_widget.selectedItems():
                    if selected.background() == std_bg:
                        selected.setBackground(del_bg)
                    elif selected.background() == del_bg:
                        selected.setBackground(std_bg)
                self.image_list_widget.update()
            elif key == self.user_controls_config["image_manager"]["edit image caption"]:
                selected = self.image_list_widget.selectedItems()
                if selected and len(selected) == 1:
                    selected_image = selected[0].data(Qt.UserRole)
                    new_caption, _ = getText(
                        "Edit image caption:",
                        default=selected_image["caption"]
                    )
                    if new_caption:
                        selected[0].setText(new_caption)
                        selected_image["caption"] = new_caption
                        selected[0].setData(Qt.UserRole, selected_image)
                        self.image_list_widget.update()
                else:
                    showInfo("Can only edit 1 image at a time")
            elif key == self.user_controls_config["image_manager"]["take image(s) (for reordering)"]:
                for selected in self.image_list_widget.selectedItems():
                    if selected.background() == std_bg:
                        selected.setBackground(sel_bg)
                    elif selected.background() == sel_bg:
                        selected.setBackground(std_bg)
            elif key in [self.user_controls_config["image_manager"]["place image(s) above (for reordering)"], self.user_controls_config["image_manager"]["place image(s) below (for reordering)"]]:
                take_items = []
                row_offset = 1 if key == self.user_controls_config["image_manager"]["place image(s) below (for reordering)"] else 0
                for i in range(self.image_list_widget.count()):
                    if self.image_list_widget.item(i).background() == sel_bg:
                        self.image_list_widget.item(i).setBackground(std_bg)
                        take_items.append(self.image_list_widget.item(i))
                if take_items:
                    for item in take_items:
                        self.image_list_widget.takeItem(
                            self.image_list_widget.row(item)
                        )
                    for item in take_items[::-1]:
                        self.image_list_widget.insertItem(
                            self.image_list_widget.currentRow() + row_offset,
                            item
                        )
                    self.image_list_widget.update()
            else:
                return _orig(evt)

        self.image_list_widget.itemSelectionChanged.connect(update_label)
        orig_handler = self.image_list_widget.keyPressEvent
        self.image_list_widget.keyPressEvent = lambda evt: key_handler(evt, orig_handler)
        populate_qlist(images)
        update_label()

        dialog = QDialog(mw)
        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(image_manager_help_box)
        layout.addWidget(image_label)
        layout.addWidget(self.image_list_widget)
        dialog.setLayout(layout)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setFixedSize(500, 300)

        def submit_changes(evt, _orig):
            if evt.key() in [Qt.Key_Return, Qt.Key_Enter]:
                dialog.accept()
            else:
                return _orig(evt)

        orig_dialog_handler = dialog.keyPressEvent
        dialog.keyPressEvent = lambda evt: submit_changes(evt, orig_dialog_handler)
        res = dialog.exec_()

        if res == 1:
            self.save()
            images = [
                self._templ_image(image["src"], image["caption"], image["id"], image.get('url'), image["thumb"]) for image in [
                    self.image_list_widget.item(index).data(Qt.UserRole)
                    for index in range(self.image_list_widget.count())
                    if self.image_list_widget.item(index).background() != del_bg
                ]
            ]
            setField(note, self.settings["imagesField"], "".join(images))
            note.flush()
            mw.reset()

    def _clean_extract_html(self, html):
        cnt = None
        content = "".join([unicode(c) for c in bs(html).find('span').contents])
        soup = bs(content)
        clean_html = ""
        clean_start = 0
        for rem_span in soup.findAll('span', {"irx-remove": ""}):
            cnt = cnt or 0
            span_str = unicode(rem_span.extract())
            if rem_span.get("id")[:2] == "ex":
                clean_start = content.find(span_str)+len(span_str)
                cnt = max(0, cnt-1)
            else:
                if cnt == 0:
                    clean_end = content.find(span_str)
                    clean_content = content[clean_start:clean_end] 
                    clean_html += clean_content + (" " if clean_content[:-1]!= " " else "")
                cnt += 1
        if cnt == 0:
            clean_html += content[clean_start:]
        return unicode(clean_html or content)

    def _remove_other_extracts(self, html):
        clean_html = html
        extract_soup = bs(html)
        for link in extract_soup.findAll("a"):
            link_str = str(link)
            href = link.get('href')
            if href.find("irxnid:")==0:
                nid = href.replace("irxnid:", "")
                try:
                    note = mw.col.getNote(nid)
                    remove_link = note.model().get("name") == self.settings["modelName"]
                except TypeError:
                    remove_link = True
                link_contents = "".join([unicode(c) for c in link.contents])
                if not remove_link:
                    link.replaceWithChildren()
                    link = bs(str(link).replace("&quot;", '"').replace(link.get('style'), "")).find('a')
                    link.insert(0, link_contents)
                    replacement = str(link)
                else:
                    replacement = link_contents
                clean_html = clean_html.replace(link_str, replacement)
        for span in extract_soup.findAll('span'):
            span_id = span.get('id')
            if not span_id:
                continue
            if span_id.find("sx") == 0 or span_id.find("ex") == 0:
                clean_html = clean_html.replace(str(span), "")
        return unicode(clean_html)
                    
    def extract(self, also_edit=False, schedule_name=None, excl_removed=True):
        if not mw.web.selectedText():
            showInfo("Please select some text to extract.")
            return
        selection = self._clean_extract_html(mw.web.selectedHtml()) if excl_removed else mw.web.selectedHtml()
        selection = self._remove_other_extracts(selection)

        model = mw.col.models.byName(self.settings["modelName"])

        current_card = mw.reviewer.card
        current_note = current_card.note()
        new_note = Note(mw.col, model)
        new_note.tags = current_note.tags

        if self.settings["plainText"]:
            text = bs(selection).text
        else:
            text = selection 
            media_paths = re.findall(r"src=\"([^\"]+)", text)
            for path in media_paths:
                media_name = normpath(basename(path))
                text = text.replace(path, media_name)

        setField(new_note, self.settings["textField"], text)
        setField(
            new_note, self.settings["imagesField"],
            getField(current_note, self.settings["imagesField"])
        )
        setField(
            new_note, self.settings["sourceField"],
            getField(current_note, self.settings["sourceField"])
        )
        setField(
            new_note, self.settings["parentField"],
            getField(current_note, self.settings["titleField"])
        )
        setField(
            new_note, self.settings["pidField"],
            "irxnid:{}".format(current_note.id)
        )
        setField(
            new_note, self.settings["linkField"],
            getField(current_note, self.settings["linkField"])
        )
        setField(new_note, self.settings["dateField"], pretty_date())

        if self.settings["editSource"]:
            EditCurrent(mw)

        if self.settings["extractDeck"]:
            did = mw.col.decks.byName(self.settings["extractDeck"])["id"]
        else:
            did = current_card.did

        if self.settings["editExtract"] or also_edit:
            highlight = self._editExtract(
                new_note, did, self.settings["modelName"]
            )
        else:
            setField(
                new_note, self.settings["titleField"],
                self._next_version_number(current_note)
            )
            highlight = True

        if highlight:
            new_note.model()["did"] = did
            mw.col.addNote(new_note)
            if schedule_name:
                cards = new_note.cards()
                if cards:
                    mw.readingManagerX.scheduler.answer(
                        cards[0], schedule_name, from_extract=True
                    )
            self.link_note(new_note, schedule_name=schedule_name)

    def extract_image(self, remove_src=False, skip_captions=False):
        irx_info_box('importingImagesOne')
        irx_info_box('importingImagesTwo')
        if mw.web.selectedText():
            mw.web.triggerPageAction(QWebPage.Copy)
        else:
            remove_src = False

        image_data, captions, image_urls = self._grab_images_from_clipboard()
        if not image_data:
            return

        images_templ = ""
        for index, image in enumerate(image_data):
            try:
                caption, ret = getText(
                    "Add a caption for the image",
                    title="Extract Image",
                    default=captions[index]
                ) if not skip_captions else (captions[index], 1)
            except IndexError:
                caption, ret = getText(
                    "Add a caption for the image",
                    title="Extract Image",
                    default=pretty_date()
                ) if not skip_captions else (pretty_date(), 1)
            if ret == 1:
                extension = os.path.splitext(image_urls[index])[-1][1:].lower()
                filepath, identifier, thumb_filepath = self._save_image_to_col(
                    image, caption[:50], extension
                )
                if filepath and identifier:
                    images_templ += self._templ_image(
                        filepath,
                        caption,
                        identifier=identifier,
                        url=image_urls[index] if image_urls else None,
                        thumb_src=thumb_filepath
                    )
        if images_templ:
            current_card = mw.reviewer.card
            current_note = current_card.note()
            prev_images_field = getField(
                current_note, self.settings["imagesField"]
            )
            images_soup = bs(prev_images_field)
            current_image_ids = [
                d.get('id') for d in images_soup.
                findAll('div', {'class': "irx-img-container"})
            ]
            if identifier not in current_image_ids:
                if remove_src:
                    self.remove()  # this automatically takes care of saving
                else:
                    self.save()
                new_images_field = prev_images_field + images_templ
                setField(
                    current_note, self.settings["imagesField"], new_images_field
                )
            else:
                tooltip("Image has already been extracted.")
            current_note.flush()
            mw.reset()

    def save(self, linked_nid=None):
        current_view = mw.web.page().mainFrame().toHtml()
        soup = bs(current_view)
        text_div = soup.find("div", {"class": "irx-text"})
        images_div = soup.find("div", {"class": "irx-images"})
        if text_div:
            current_note = mw.reviewer.card.note()
            note_linked = mw.col.getNote(linked_nid) if linked_nid else None
            action = {
                "type":
                    "irx-extract",
                "nid":
                    linked_nid,
                "title":
                    (
                        getField(note_linked, self.settings["titleField"])
                        if note_linked.model()["name"] == self.
                        settings["modelName"] else None
                    )
            } if note_linked else {}
            self.history[current_note.id].append(
                {
                    "text": current_note["Text"],
                    "images": current_note["Images"],
                    "action": action,
                }
            )
            current_note["Text"] = "".join(
                [
                    unicode(c) for c in text_div.contents if
                    not (isinstance(c, bs_tag) and c.get('class') == "irx-sep")
                ]
            )
            images_content = "".join([unicode(c) for c in images_div.contents])
            for src in re.findall(r"src=\"([^\"]+)", images_content):
                images_content = images_content.replace(
                    src, urllib2.unquote(src)
                )
            current_note["Images"] = images_content
            current_note.flush()
            self._write_history()

    def undo(self, show_tooltip=True):
        irx_info_box('firstTimeUndoing')
        current_note = mw.reviewer.card.note()
        current_note_title = getField(current_note, "Title")
        history = self.history.get(current_note.id)
        if not history:
            tooltip("No undo history for {}".format(current_note_title))
            return

        msg = "Undone"
        save_data = self.history[current_note.id].pop()
        self._write_history()
        action = save_data.get("action")
        if action and action["type"] == "irx-extract":
            extract_nid = action["nid"]
            try:
                extract = mw.col.getNote(extract_nid)
                try:
                    extract_title = getField(
                        extract, self.settings["titleField"]
                    )
                except KeyError:
                    extract_title = extract_nid
                mw.col.remNotes([extract_nid])
                mw.readingManagerX.scheduler.update_organizer()
                msg += "<br/> Deleted note: {}".format(extract_title)
            except TypeError:
                mw.col.db.execute("delete from cards where nid=?", extract_nid)
                msg += "<br/> Linked note [{}] no longer exists.".format(
                    action["title"] or action["nid"]
                )
        current_note["Text"] = save_data["text"]
        current_note["Images"] = save_data["images"]
        current_note.flush()
        mw.reset()
        if show_tooltip:
            tooltip(msg)

    def _templ_image(self, src, caption, identifier=None, url=None, thumb_src=None):
        content = {
            "id": identifier or timestamp_id(),
            "src": src,
            "caption": caption,
            "url": url,
            "thumb": thumb_src or src
        }
        template = '<div class="irx-img-container" id="{id}"><br/><a href="{src}"><img src="{thumb}" irx-src="{thumb}" onerror="irxOnImgError(this);"/>'
        template += '</a><a href="{url}">' if url else '</a>'
        template += '<span class="irx-caption">{caption}</span>'
        template += '</a></div>' if url else '</div>'
        return template.format(**content)

    def _save_image_to_col(self, image_data, filename, ext):
        media = mw.col.media
        identifier = None
        filename = filename.replace("\"","")
        filepath = media.stripIllegal(filename)
        if not isinstance(image_data, str): #it's already a QImage
            buf = QBuffer()
            buf.open(QBuffer.ReadWrite)
            image_data.save(buf, ext, quality=100)
            image_data = buf.data()
        compressed_data, compression_ratio, thumb_data = compress_image(image_data, ext)
        if not compressed_data:
            return None, None, None
        if int(compression_ratio) != 1:
            tooltip('<b>IR3X</b>: Compressed image by {0:.2f}%'.format(100 - (compression_ratio*100)))
        identifier = checksum(compressed_data)
        ext_ending = ".{}".format(ext)
        filepath += ext_ending if filepath[-len(ext_ending):] != ext_ending else ""
        media.writeData(filepath, compressed_data)
        thumb_filepath = "thumb_{}".format(filepath) if thumb_data else filepath
        if thumb_data:
            media.writeData(thumb_filepath, thumb_data)
        return filepath, identifier, thumb_filepath

    def _grab_images_from_clipboard(self):
        mime_data = QApplication.clipboard().mimeData()
        image_data = []
        image_urls = []
        image_captions = [t for t in mime_data.text().split("\n") if t]
        image = mime_data.imageData()
        if not image:
            soup = bs(mime_data.html())
            soup_imgs = soup.findAll('img')
            if soup_imgs:
                progress = QProgressDialog("Getting images from clipboard", "Cancel", 1, len(soup_imgs), mw)
                progress.setWindowModality(Qt.WindowModal)
            for i, img in enumerate(soup_imgs):
                progress.setValue(i)
                possible_better_caption = None
                parent = img.findParent(
                    'a', {
                        'href':
                            re.compile(
                                r"wiki[pm]edia\.org/wiki/File:",
                                flags=re.IGNORECASE
                            )
                    }
                )
                if parent:
                    wiki_soup = bs(urllib2.urlopen(parent.get('href')))
                    media_path = wiki_soup.findAll(
                        'div', attrs={"id": "file"}
                    )[0].findChild('a').get('href')
                    media_desc = wiki_soup.findAll(
                        'td', attrs={"class": "description"}
                    )
                    if media_desc:
                        possible_better_caption = media_desc[0].text
                else:
                    media_path = img.get('src')
                img_data = None
                try:
                    img_data = urllib2.urlopen(media_path).read()
                except ValueError:
                    try:
                        media_path = "http:" + ("//" if not media_path.startswith("//") else "") + media_path
                        img_data = urllib2.urlopen(media_path).read()
                    except Exception as url_exception:
                        tooltip(
                            "There was a problem getting {0}:\n {1}".format(
                                media_path, url_exception
                            )
                        )
                        continue
                except urllib2.URLError as url_exception:
                    try:
                        img_data = urllib2.urlopen(urllib2.unquote(media_path)).read()
                    except Exception as url_exception:
                        tooltip(
                            "There was a problem getting {0}:\n {1}".format(
                                media_path, url_exception
                            )
                        )
                        continue
                if img_data:
                    image_data.append(img_data)
                    image_urls.append(media_path)
                    if possible_better_caption:
                        tmp_image_captions = sum([[possible_better_caption,image_captions[i]] if t==i else [image_captions[t]] if t<len(image_captions) else [""] for t in range(len(image_data))], [])
                        if len(tmp_image_captions) < len(image_captions):
                            image_captions = tmp_image_captions + image_captions[len(tmp_image_captions)-1:]
                        else:
                            image_captions = tmp_image_captions
                else:
                    tooltip(
                        "There was a problem getting {}".format(
                            media_path,
                        )
                    )
                if progress.wasCanceled():
                    break;
            if soup_imgs:
                progress.setValue(len(soup_imgs))
            if not image_data:
                showInfo("Could not find any images to extract")
        else:
            image_data = [image]
            image_urls = ["_.jpg"]

        return image_data, image_captions, image_urls

    def _editExtract(self, note, did, model_name):
        undo_action = lambda: self.undo(show_tooltip=False)
        
        def _addNote(self, note, _orig):
            orig_ret = _orig(note)
            if orig_ret:
                self.rejected.disconnect(undo_action)
                self.note_added_ok = True
            return orig_ret

        def on_add(self):
            if self.note_added_ok:
                self.reject()
        
        add_cards = AddCards(mw)
        _orig = add_cards.addNote
        add_cards.note_added_ok = False
        add_cards.addNote = lambda note: _addNote(add_cards, note, _orig)
        add_cards.rejected.connect(undo_action)
        add_cards.addButton.clicked.connect(lambda: on_add(add_cards))
        add_cards.editor.setNote(note)
        deck_name = mw.col.decks.get(did)["name"]
        if note.stringTags():
            add_cards.editor.tags.setText(note.stringTags().strip())
        add_cards.deckChooser.deck.setText(deck_name)
        add_cards.modelChooser.models.setText(model_name)
        return True

    def _next_version_number(self, parent_note):
        parent_version = re.match(
            r"(^[0-9\.]+)", getField(parent_note, self.settings["titleField"])
        )
        if parent_version:
            parent_version = parent_version.group()
        else:
            parent_version = "1."
        siblings = irx_siblings(parent_note)
        sibling_count = len(siblings)
        next_version = sibling_count + 1
        version_ok = False
        while not (version_ok):
            candidate_version = "{0}{1}.".format(
                parent_version, str(next_version)
            )
            sibling_versions = [
                getField(sibling,
                         self.settings["titleField"])[:len(candidate_version)]
                for sibling in siblings
            ]
            version_ok = candidate_version not in sibling_versions
            if version_ok:
                return candidate_version
            next_version += 1

    def _write_history(self):
        pickle.dump(
            self.history, open(self.history_path, "wb"), pickle.HIGHEST_PROTOCOL
        )
