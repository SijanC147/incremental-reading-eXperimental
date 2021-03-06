INFO_MESSAGES = {
    'firstTimeOpening': {
        "flag_key":'firstTimeOpening',
        "text":"Thank you for trying out IR3X!",
        "info_texts":[
            "Seriously, I really appreciate it, you're awesome.",
            "You should have a new deck created, (<code><b>~IR3X</b></code>), this should be used to store all your IR3X notes. There should also be <b>getting started</b> IR3X note to get going.",
            "I've tried to place these information boxes at important parts of the IR3X user experience to explain how it works and how to <i>hopefully</i> get the best results.",
            "I highly recommend reading through these boxes at least once when they show up.",
            "To avoid skipping an info box by mistake, the default option is set to OK, if you still skip over an info box by mistake, you can bring it up again from the Help menu.",
            "All of the IR3X controls (editable through the <code><b>ir3x.py</b></code> file in the addon folder) are accessible through the Options menu.",
            "Most of these controls deactivate when you are not viewing IR3X notes in an effort to avoid collisions, a tooltip appears when the IR3X controls toggle on/off",
            "Bug reports help me make this add-on better, which I am intent on doing, so please report any and all of those using the Issue Reporter in the Options menu. I appreciate it!",
            "<b>Please take some time to go through the About menu, where I mention the original creators of the IR add-on, whose work was the foundation for IR3X.</b>",
            "Thanks again for giving this add-on a shot."
        ],
    },
    'firstTimeViewingIrxNote': {
        "flag_key":'firstTimeViewingIrxNote',
        "text":"Important points to keep in mind.",
        "info_texts":[
            "First off, thank you for trying out this add-on, you're awesome.",
            "Most text interaction functionality has been relatively stable as long as I stick these pointers:"+
            "<ul>{}</ul>".format("".join("<li>{}</li>".format(p) for p in [
                "Try to avoid having individual highlights that span large portions of the text, unless you will not be editing that portion further.",
                "Avoid having a lot of overlapping highlights/styles as this can cause problems when deciding which highlight/style to take precedence in the HTML.",
                "If you want to apply styles to highlighted chunks, it's usually better to style the text first, then highlight it.",
                "I highly recommend you highlight a chunk of text first then click on the link that is generated to edit that extract, instead of using the 'Edit Extract' functionality to skip a click.",
            ])),
        ],
    },
    "firstTimeViewingQuickKeys": {
        "flag_key":'firstTimeViewingQuickKeys',
        "text":"How IR3X Schedules Work",
        "info_texts":[
            "IR3X does away with the original highlight option in favor of extracts. In IR3X terms, <b>extracts = highlights = extracts</b>",
            "This means that anything that is highlighted in an IR3X represents another note, which can be either another IR3X note or another type of Anki note",
            "Quick Keys deal with the latter, while the former are configurable through Schedules.",
            "When viewing IR3X text, you can use a configured quick key combination to highlight the selected content as well as create a new note based on the settings below."
            "Most of these settings are straight forward and function exactly the same way as in original IR addon."
        ],
    },
    "introducingMirrorDeckOption":{
        "flag_key": "introducingMirrorDeckOption",
        "text": "The [Mirror] Deck Option",
        "info_texts":[
            "IR3X introduces a new options for setting your target deck and organising your notes, <b>[Mirror]</b>.",
            "Under this setting IR3X will place any new notes in a <i>mirrored</i> with respect to the root IR3X container deck (~IR3X by default).",
            "So, any notes extracted from an IR3X note in a deck such as <code>~IR3X::Tutorials::Another Subdeck</code> will go under Tutorials::Another Subdeck",
            "Any missing decks are created in the process."
        ],
    },
    "firstTimeViewingTargetFields":{
        "flag_key": "firstTimeViewingTargetFields",
        "text": "Using Templates for extract target fields",
        "info_texts":[
            "IR3X allows you to specify what goes where when extracting a new note using a very minimal templating engine.",
            "Use the buttons on the top row to insert a template value which till be replaced by the field value of the IR3X you are vieweing",
            "Except for <b>Text</b> which refers only to your highlighted selection, not the entire text field of the IR3X note",
        ],
    },
    "noteAboutEditingAQuickKeyExtract":{
        "flag_key": "noteAboutEditingAQuickKeyExtract",
        "text": "Sorry about this, but hear me out...",
        "info_texts":[
            "The option to edit the extract note is there but very much <b> not recommended </b> as it can lead to some problems (these stem directly from my lack of experience with Qt, sorry about that).",
            "A much better and more stable option is to always stick to just creating the note with the quick key, then use the link that IR3X generates, which automatically opens the note in the editor.",
            "This approach only involves an extra click, but <b>should</b> provide a more stable experience in general.",
            "Some more information about why this is if you're interested...",
            "For the typical use-case this should actually work, the problems arise when cancelling a new note from the edit window, or, even worse, switching back to the IR3X note with the editor still open.",
            "This happens because IR3X actually creates the note <b>before</b> you finish editing, then carries out an undo operation in the background to delete the created note, and remove the highlight.",
            "The undo operation is completely oblivious of the editor and will only undo whatever the last action was."
        ],
    },
    'editingQuickKeysHighlights': { 
        "flag_key":'editingQuickKeysHighlights',
        "text":"Changing Quick Keys' Colors",
        "info_texts":[
            "Any highlight changes will only apply from this point forward.",
            "Existing highlights will <b>not</b> be updated."
        ],
    },
    'firstTimeViewingSettings': { 
        "flag_key":'firstTimeViewingSettings',
        "text":"IR3X Settings",
        "info_texts":[
            "These should be quite self-explenatory, Zoom and Scroll settings work exactly the same as in the original add-on",
            "The new settings allow you to define the maximum size for imported images which IR3X when compressing images.",
            "The Auto-caption setting is used to define the atuomatic caption that is assigned to an image when IR3X cannot extract one from the clipboard.",
            "This setting supports <code>strftime</code> formatting (click on the button next to the input for more info), a live preview is displayed below the input.",
            "If the inputted template is invalid (error message displayed), any changes will be discarded.",
            "When enabled, the IR3X error handler will intercept any errors thrown by Anki and try to deduce if it is to blame for the error.", 
            "If IR3X is to blame, it will automatically open up its issue reporter with the traceback information for that error auto-populated, you can then review this information and add to it, before submitting an issue.",
            "Errors not originating from IR3X are forwarded to Anki as normal."
        ],
    },
    'firstTimeViewingSchedules' : {
        "flag_key":'firstTimeViewingSchedules',
        "text":"How IR3X Schedules Work",
        "info_texts":[
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
    },
    'editingScheduleHighlights':{ 
        "flag_key":'editingScheduleHighlights',
        "text":"Changing Schedules' Colors",
        "info_texts":[
            "Any highlight changes will only apply from this point forward.",
            "Existing highlights will <b>not</b> be updated."
        ],
    },
    'firstTimeStyling':{ 
        "flag_key":'firstTimeStyling',
        "text":"IR3X Styling Text",
        "info_texts":[
            "Remember to try as much as possible to style text before extracting (highlighting) it for best results.",
            "Text Styling visibility can be toggled using the 1st toggle on the IR3X HUD (colorful bar at the bottom of the note) or the assigned key shortcut."
        ],
    },
    'firstTimeRemovingText':{ 
        "flag_key":'firstTimeRemovingText',
        "text":"IR3X Removed Text",
        "info_texts":[
            "Removal of text in an IR3X note is not permanent, by default removed text will disappear from the note.",
            "Removed text visibility can be toggled using the 3rd toggle on the IR3X HUD (colorful bar at the bottom of the note) or the assigned key shortcut."
        ],
    },
    'firstTimeExtractingSchedule':{ 
        "flag_key":'firstTimeExtractingSchedule',
        "text":"ir3x extracts (highlights)",
        "info_texts":[
            "apart from highlighting the text, ir3x also creates a direct link to the note you just created.",
            "clicking on this link automatically opens the editor and allows you to make any changes to the note",
            "ir3x generates titles using a numbering scheme starting from 1.<i>x</i>, where <i>x</i> is calculated based on the number of child extracts the parent has."
            "for subsequent extracts originating from the one of this notes' children, the title shall be 1.<i>x</i>.<i>y</i>, where <i>y</i> is the number of children that child has, and so on.."
            "highlights (extracts) visibility can be toggled using the 2rd toggle on the ir3x hud (colorful bar at the bottom of the note) or the assigned key shortcut."
        ],
    },
    'firstTimeExtractingQuickKey':{ 
        "flag_key":'firstTimeExtractingQuickKey',
        "text":"IR3X Extracts (Highlights)",
        "info_texts":[
            "Apart from highlighting the text, IR3X also creates a direct link to the note you just created.",
            "Clicking on this link automatically opens the editor and allows you to make any changes to the note",
            "Fields for the generated note are filled according to the template settings you provide",
            "Highlights (extracts) visibility can be toggled using the 2rd toggle on the IR3X HUD (colorful bar at the bottom of the note) or the assigned key shortcut."
        ],
    },
    'firstTimeOpeningImageManager':{ 
        "flag_key":'firstTimeOpeningImageManager',
        "text":"Using the Image Manager",
        "info_texts":[
            "Some very basic functionality to interact with the imported images of a note is accessible through this Manager.",
            "The manager will not appear if no images have been imported for the current note (ie the images sidebar is empty).",
            "When open the image manager allows you to "+
                "<ul>{}</ul>".format("".join("<li>{}</li>".format(p) for p in [
                    "Change the order of the images",
                    "Change the caption of an image",
                    "Delete an image"
                ])),
            "The way this is achieved is by first <b>marking the images you intend on moving or deleting</b>",
            "Images marked for deletion will appear with a red background in the list (unless selected, in that case the blue overrides that, but they are still <i>marked for deletion</i>)",
            "Images marked for moving will appear in a different color blue (distinguishable from the selected items color)",
            "You can then move to the desired location and move the selected images <b> above or below </b> that position",
            "Your set controls for the image manager will appear any time you select multiple images, or can be manually toggled using the toggle controls key (default: ?)",
            "Hitting <b>Enter</b> will close the image manager and submit the changes, while <b>Esc</b> will discards the changes",
            "Any changes made can always be undone."
        ],
    },
    'importingImagesOne':{ 
        "flag_key":'importingImagesOne',
        "text":"Importing Images to IR3X notes",
        "info_texts":[
            "IR3X allows you to <b>import images</b> from your clipboard to an IR3X note, this image will then appear in the images sidebar, and automatically be inherited by any <b>new</b> child IR3X extracts",
            "There are two approaches to importing images, " +
                "<ul>{}</ul>".format("".join("<li>{}</li>".format(p) for p in [
                            "Importing from raw image data stored in the clipboard, this is usually faster, but can have unexpected results if the image is not a JPEG, since this is what IR3X defaults to with this approach.",
                            "Alternatively, IR3X can parse html data from your clipboard, look for any <code>img</code> elements and download these images in the background, deducing the appropriate type from the link",
                        ])), 
            "The second approach is preferred as IR3X will also search for any text content in the html to try and auto-caption the imported images, otherwise a caption is auto-generated based on your <b>auto-caption</b> setting.",
            "Moreover, this approach includes specific code for handling wikipedia images, following thumbnail links to automatically download the full resolution image and get the image description (if available).",
            "For each image, IR3X also generates creates an incredibly small thumbnail version to use as the preview in an IR3X note, this keeps Anki performant as the number of imported images increases.",
            "Clicking on the thumbnail in an IR3X note will open the actual higher resolution image that is stored in your Anki collection, while the caption serves as a hyperlink to the original source for the image online (where applicable).",
            "IR3X will carry out multiple compression runs until the image is at, or below, your specified <b>max image size</b>, while maintaining as much quality as possible",
            "For this reason, this process can take a while, while IR3X finds the best compression rate for each image, larger sized images will naturally take longer.",
            "Anki may appear unresponsive during this time, this is usually temporary, while it fetches the image data in the background.",
            "It is <b>highly</b> recommended to let the image importing process do it's thing before you proceed.",
            "Also, while it is possible to import multiple images at one go, importing images one at a time is usually more stable and allows IR3X to extract automatic captions more effectively."
        ],
    },
    'importingImagesTwo':{ 
        "flag_key":'importingImagesTwo',
        "text":"Importing GIFs",
        "info_texts":[
            "I know, I know, this was a long one, but bear with me, just one note on <b>GIF</b>s",
            "IR3X also supports importing GIF images, animation and all, with just a few caveats" +
                "<ul>{}</ul>".format("".join("<li>{}</li>".format(p) for p in [
                    "I couldn't really figure out how to handle GIF data using Qt without losing the animation information, which is the whole point, this is definitely possible but wasn't feasible at the time."
                    "So as to preserve the animation information, you should <b>always use the second approach</b> (copying a selection not the image) for importing GIFs.",
                    "This way IR3X can determine that it is a GIF, and will skip compression and thumbnail generation (since these are done through Qt, which would remove any animation), and save the GIF as is.",
                ])), 
            "Bear in mind that this means that while your GIFs will look good on your note, these undergo <b>no compression at all</b>.",
            "This can not only make your collection size larger than what is desireable, but also make the IR3X note less responsive since Anki has to render the full size image, not a thumbnail version.",
            "That being said, most GIFs are themselves usually small in size, and IR3X should warn you before importing a GIF that goes above your set size limit."
        ],
    },
    'firstTimeUndoing':{ 
        "flag_key":'firstTimeUndoing',
        "text":"IR3X Undo History",
        "info_texts":[
            "IR3X maintains a <b>persistent note history</b>, this means that you can always undo all all your IR3X actions even after you close Anki.",
            "To avoid getting this history cluttered, IR3X automatically prunes it every time anki starts, removing entries for notes that have been deleted, you can also do this manually through the Options menu.",
            "IR3X also keeps track of any extract notes that are created for each action and automatically deletes those notes when undoing that action, letting you know in the tooltip that appears.",
            "Removal of text in an IR3X note is not permanent, by default removed text will disappear from the note, however <b>removed text</b> visibility settings can be toggled.",
        ],
    },
    'firstTimeSeeingAnswers':{ 
        "flag_key":'firstTimeSeeingAnswers',
        "text": "Re-scheduling an IR3X Note",
        "info_texts":[
            "You can use any one of your <b>active</b> Schedules' answer keys [1-9], or the answer buttons below, to re-schedule an IR3X note based on your schedule settings.",
            "The <b>Done</b> button will appear when you have scrolled all the way to the bottom of an IR3X note, clicking this button suspends the note, so that it doesn't show up again.",
            "When the Done button appears, it will be focused as the automatic answer triggered by the space button.",
            "Even when the Done button does not appear, the <b>0</b> answer key is reserved for it, so you can always use that to make an IR3X note as done, regardless of the scroll position you're at."
        ],
    },
    "firstTimeInTheEditor": {
        "flag_key":'firstTimeInTheEditor',
        "text": "Editing/Adding IR3X Notes",
        "info_texts":[
            "When adding or editing IR3X notes, <b>Title</b>, <b>Text</b> and <b>Source</b> can be edited freely, IR3X will never overwrite these fields.",
            "<b>Date</b> is normally auto-generated, but you can edit this if you want, it is only used for your reference, nothing else.",
            "The <b>Parent</b> field should ideally be left alone, since IR3X uses this along with the <b>PID</b> field, to provide a link to an IR3X notes' parent. If you edit one, you must update the other.",
            "If you do edit the <b>PID</b> field, make sure to prefix the note id of the new parent with <code>irxnid:</code>, otherwise the link will not work.",
            "The <b>Images field should <i>never</i> be edited</b>. There is a specific format that IR3X uses in this field to manage the images of an IR3X note. Any modifications should be carried out using the Image Manager.",
            "The <b>Link</b> field is currently unused at the moment, however the plan is to have that field be auto-populated when the IR3X Web Importer is implemented, in due time...",
            "<b>Tags</b> aren't used by IR3X for anything (so far), so feel free to edit them as you please."
        ],
    },
    "spaceBarFunctionIntro": {
        "flag_key": 'firstTimeSpaceQuestion',
        "text": "The Space Bar in IR3X",
        "info_texts":[
            "When viewing an IR3X note, the <b>Space bar is remapped to Page Down</b> so long as there is more to scroll down to",
            "As soon as you <b>reach the end</b> of the IR3X note, the <b>Space bar switches back</b> to showing the answer card (the re-scheduling screen for IR3X)",
            "At any time, regardless of the scroll position, you can use <b>Shift+Space</b> (configurable through <code>ir3x.py</code>), which always defaults to showing the answer card.",
        ],
    },
    'firstTimeReportingIssue': {
        "flag_key": 'firstTimeSpaceQuestion',
        "text": "The IR3X Issue Reporter",
        "info_texts":[
            "To make reporting issues as easy as possible, you can input all of the information here.", 
            "When you're done, clicking the submit button will automatically <b>open up the IR3X issues page and copy your issue to your clipboard</b> formatted neatly into a template",
            "The issue template will contain the description you provide, the system information as displayed in the dialog, and the traceback if IR3X is responding to an exception it generated.",
            "You can set IR3X to intercept traceback information for exceptions it generates from the settings menu.",
            "You just have to paste this information into the issue box on Github, and provide a title for your issue, and that's should be it.",
            "Thank you for helping me make this add-on better.",
            "<b>Only the information that you see in the fields below is copied to the clipboard, and you can further review this information before submitting an issue to make sure that there is no sensitive information</b>",
        ],
    },
}