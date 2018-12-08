var imagesSidebar = "yes";
var showFormatting = "yes";
var showRemoved = "no";
var showExtracts = "yes";

// function highlight(bgColor, textColor) {
//     if (window.getSelection) {
//         var range, sel = window.getSelection();

//         if (sel.rangeCount && sel.getRangeAt) {
//             range = sel.getRangeAt(0);
//         }

//         document.designMode = "on";
//         if (range) {
//             sel.removeAllRanges();
//             sel.addRange(range);
//         }

//         document.execCommand("foreColor", false, textColor);
//         document.execCommand("hiliteColor", false, bgColor);

//         document.designMode = "off";
//         sel.removeAllRanges();
//     }
// }

// function markRange(identifier, bgColor, textColor) {
//     var range, sel = window.getSelection();
//     if (sel.rangeCount && sel.getRangeAt) {
//         range = sel.getRangeAt(0);
//         var startNode = document.createElement('span');
//         startNode.setAttribute('id', ('sx' + identifier));
//         startNode.setAttribute('irx-bg-color', bgColor);
//         startNode.setAttribute('irx-text-color', textColor);
//         range.insertNode(startNode);
//         var endNode = document.createElement('span');
//         endNode.setAttribute('id', ('ex' + identifier));
//         range.collapse(false);
//         range.insertNode(endNode);
//         range.setStartAfter(startNode);
//         range.setEndBefore(endNode);
//         sel.removeAllRanges();
//         sel.addRange(range);
//     }
// }

// function selectMarkedRange(identifier) {
//     var startNode, endNode, range, sel;
//     startNode = document.getElementById('sx' + identifier);
//     endNode = document.getElementById('ex' + identifier);
//     if (startNode && endNode) {
//         range = document.createRange();
//         range.setStartAfter(startNode);
//         range.setEndBefore(endNode);
//         sel = window.getSelection();
//         sel.removeAllRanges();
//         sel.addRange(range);
//     }
// }

// function restoreHighlighting() {
//     var startNodesXPathResult = document.evaluate('//*[@ir-bg-color]', document, null, XPathResult.ANY_TYPE, null);
//     var sNodes = new Array();
//     var startNode = startNodesXPathResult.iterateNext();
//     while (startNode) {
//         sNodes.push(startNode);
//         startNode = startNodesXPathResult.iterateNext();
//     }
//     var id;
//     for (var i = 0; i < sNodes.length; i++) {
//         startNode = sNodes[i];
//         id = startNode.id.substring(1);
//         selectMarkedRange(id);
//         highlight(startNode.getAttribute('irx-bg-color'),
//             startNode.getAttribute('irx-text-color'))
//     }
// }

// function turnoffHighlighting() {
//     var startNodesXPathResult = document.evaluate('//*[@irx-bg-color]', document, null, XPathResult.ANY_TYPE, null);
//     var sNodes = new Array();
//     var startNode = startNodesXPathResult.iterateNext();
//     while (startNode) {
//         sNodes.push(startNode);
//         startNode = startNodesXPathResult.iterateNext();
//     }
//     var id;
//     for (var i = 0; i < sNodes.length; i++) {
//         startNode = sNodes[i];
//         id = startNode.id.substring(1);
//         selectMarkedRange(id);
//         highlight('transparent', 'black')
//     }
// }

function removeText() {
    var selection = window.getSelection().getRangeAt(0);
    var selectedText = selection.extractContents();
    var span = document.createElement("span");

    span.className = "irx-removed";
    span.setAttribute("irx-show-removed", displayRemoved);
    span.appendChild(selectedText);

    selection.insertNode(span);
}

function linkToNote(note_id, extract_type) {
    var selection = window.getSelection().getRangeAt(0);
    var selectedText = selection.extractContents();

    var note_link = document.createElement("a");
    note_link.className = "irx-link"
    note_link.setAttribute("href", "irxnid:" + note_id)
    note_link.appendChild(selectedText);

    var note_span = document.createElement("span");
    var extract_span_class = "irx-extract-link-" + extract_type
    note_span.className = "irx-extract " + extract_span_class;
    note_span.setAttribute("irx-show-extracts", showExtracts);
    note_span.appendChild(note_link)

    selection.insertNode(note_span);
}

function format(style) {
    var selection = window.getSelection().getRangeAt(0);
    var selectedText = selection.extractContents();
    var span = document.createElement("span");

    span.className = "irx-format " + style;
    span.setAttribute("irx-show-formatting", showFormatting);
    span.appendChild(selectedText);

    selection.insertNode(span);
}

function toggleImagesSidebar(manual) {
    var text = document.getElementsByClassName("irx-text")[0];
    var images = document.getElementsByClassName("irx-images")[0];
    if (manual == "toggle") {
        if (imagesSidebar == "no") {
            imagesSidebar = "yes";
        } else {
            imagesSidebar = "no";
        }
    } else {
        imagesSidebar = manual
    }
    text.setAttribute("irx-images-sidebar", imagesSidebar)
    images.setAttribute("irx-images-sidebar", imagesSidebar)
}


function toggleShowExtracts(manual) {
    if (manual == "toggle") {
        if (showExtracts == "no") {
            showExtracts = "yes";
        } else {
            showExtracts = "no";
        }
    } else {
        showExtracts = manual
    }
    var elems = document.getElementsByClassName("irx-extract");
    for (var i = 0; i < elems.length; i++) {
        elems[i].setAttribute("irx-show-extracts", showExtracts)
    }
}


function toggleShowRemoved(manual) {
    if (manual == "toggle") {
        if (showRemoved == "no") {
            showRemoved = "yes";
        } else {
            showRemoved = "no";
        }
    } else {
        showRemoved = manual
    }
    var elems = document.getElementsByClassName("irx-removed");
    for (var i = 0; i < elems.length; i++) {
        elems[i].setAttribute("irx-show-removed", showRemoved)
    }
}

function toggleShowFormatting(manual) {
    if (manual == "toggle") {
        if (showFormatting == "yes") {
            showFormatting = "no";
        } else {
            showFormatting = "yes";
        }
    } else {
        showFormatting = manual
    }
    var elems = document.getElementsByClassName("irx-format");
    for (var i = 0; i < elems.length; i++) {
        elems[i].setAttribute("irx-show-formatting", showFormatting)
    }
}