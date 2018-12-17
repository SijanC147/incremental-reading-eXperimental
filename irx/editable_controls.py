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
#       "show help": "? Meta+h i", // assigns three key shortcuts to the action.
#    ...
#
#   IR3X will notify you of any conflicts that it finds on load, and should bring up
#   the help menu to highlight which controls are in conflict.

REVIEWER_CONTROLS = {
    "show help": "?",
    "toggle images": "Meta+m",
    "toggle formatting": "Meta+f",
    "toggle removed text": "Meta+z",
    "toggle extracts": "Meta+x",
    "done (suspend)": "!",
    "undo": "u",
    "add image": "@",
    "add image (skip caption)": "Shift+@",
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
    "toggle help": "?",
    "edit image caption": "e",
    "mark image(s) for deletion": "d",
    "take image(s) (for reordering)": "t",
    "place image(s) above (for reordering)": "a",
    "place image(s) below (for reordering)": "b",
    "submit image changes": "Enter",
}
