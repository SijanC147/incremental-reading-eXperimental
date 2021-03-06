# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from aqt import mw
import irx.main

# IR3X for Anki 2.0 (Incremental Reading 3 eXperimental)
#
# ISC License
#
# Copyright 2013 Tiago Barroso
# Copyright 2013 Frank Kmiec
# Copyright 2013-2016 Aleksej
# Copyright 2017 Christian Weiß
# Copyright 2018 Timothée Chauvin
# Copyright 2017-2018 Joseph Lorimer
# Copyright 2018 Sean Bugeja <seanbugeja23@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

############################## EDITABLE CONTROLS #############################

# WIN -> MAC:
#
#   META -> CTRL
#   CTRL -> CMD
#   ALT -> OPT

#   Always use the WIN version of the keys when defining controls here,
#   the information above is provided just as a guideline.
#   Once in Anki, IR3X should display the correct key-sequences based
#   on the platform it is running on.
#
#   Multiple key sequences can be assigned to the same action by separating them
#   using a space eg.
#
#    ...
#       "show controls": "? Meta+h i", // assigns three keys for the "show controls" action.
#    ...
#
#   IR3X will notify you of any conflicts that it finds on load, and should bring up
#   the help menu to highlight which controls are in conflict.

REVIEWER_CONTROLS = {
    "show controls": "?",
    "toggle images": "Meta+m",
    "toggle formatting": "Meta+f",
    "toggle removed text": "Meta+z",
    "toggle extracts": "Meta+x",
    "done (suspend)": "!",
    "undo": "u",
    "import image": "@",
    "import image (skip caption)": "^",
    "extract image": "m",
    "extract image (skip caption)": "q",
    "bold": "Ctrl+b",
    "underline": "Meta+o",
    "italic": "Ctrl+i",
    "strikethrough": "Ctrl+s",
    "remove": "Meta+d",
    "show reading list": "Ctrl+Alt+2",
    "show image manager": "i",
    "zoom in": "Ctrl+=",
    "zoom out": "Ctrl+-",
    "line up": "Up",
    "line down": "Down",
    "page up": "PgUp",
    "page down": "PgDown",
    "next card": "Shift+Space"
}

IMAGE_MANAGER_CONTROLS = {
    "toggle controls": "?",
    "edit image caption": "e",
    "mark image(s) for deletion": "d",
    "take image(s) (for reordering)": "t",
    "place image(s) above (for reordering)": "a",
    "place image(s) below (for reordering)": "b",
    "submit image changes": "Enter",
}

############################## END OF USER CONFIG #############################

mw.readingManagerX = irx.main.ReadingManager(
    REVIEWER_CONTROLS, IMAGE_MANAGER_CONTROLS
)
