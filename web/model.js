var formatting = "on";
var displayRemoved = "no";

function highlight(bgColor, textColor) {
    if (window.getSelection) {
        var range, sel = window.getSelection();

        if (sel.rangeCount && sel.getRangeAt) {
            range = sel.getRangeAt(0);
        }

        document.designMode = "on";
        if (range) {
            sel.removeAllRanges();
            sel.addRange(range);
        }

        document.execCommand("foreColor", false, textColor);
        document.execCommand("hiliteColor", false, bgColor);

        document.designMode = "off";
        sel.removeAllRanges();
    }
}

function markRange(identifier, bgColor, textColor) {
    var range, sel = window.getSelection();
    if (sel.rangeCount && sel.getRangeAt) {
        range = sel.getRangeAt(0);
        var startNode = document.createElement('span');
        startNode.setAttribute('id', ('sx' + identifier));
        startNode.setAttribute('irx-bg-color', bgColor);
        startNode.setAttribute('irx-text-color', textColor);
        range.insertNode(startNode);
        var endNode = document.createElement('span');
        endNode.setAttribute('id', ('ex' + identifier));
        range.collapse(false);
        range.insertNode(endNode);
        range.setStartAfter(startNode);
        range.setEndBefore(endNode);
        sel.removeAllRanges();
        sel.addRange(range);
    }
}

function selectMarkedRange(identifier) {
    var startNode, endNode, range, sel;
    startNode = document.getElementById('sx' + identifier);
    endNode = document.getElementById('ex' + identifier);
    if (startNode && endNode) {
        range = document.createRange();
        range.setStartAfter(startNode);
        range.setEndBefore(endNode);
        sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }
}

function restoreHighlighting() {
    var startNodesXPathResult = document.evaluate('//*[@ir-bg-color]', document, null, XPathResult.ANY_TYPE, null);
    var sNodes = new Array();
    var startNode = startNodesXPathResult.iterateNext();
    while (startNode) {
        sNodes.push(startNode);
        startNode = startNodesXPathResult.iterateNext();
    }
    var id;
    for (var i = 0; i < sNodes.length; i++) {
        startNode = sNodes[i];
        id = startNode.id.substring(1);
        selectMarkedRange(id);
        highlight(startNode.getAttribute('irx-bg-color'),
            startNode.getAttribute('irx-text-color'))
    }
}

function turnoffHighlighting() {
    var startNodesXPathResult = document.evaluate('//*[@irx-bg-color]', document, null, XPathResult.ANY_TYPE, null);
    var sNodes = new Array();
    var startNode = startNodesXPathResult.iterateNext();
    while (startNode) {
        sNodes.push(startNode);
        startNode = startNodesXPathResult.iterateNext();
    }
    var id;
    for (var i = 0; i < sNodes.length; i++) {
        startNode = sNodes[i];
        id = startNode.id.substring(1);
        selectMarkedRange(id);
        highlight('transparent', 'black')
    }
}

function removeText() {
    var selection = window.getSelection().getRangeAt(0);
    var selectedText = selection.extractContents();
    var span = document.createElement("span");

    span.className = "irx-removed";
    span.setAttribute("irx-display-removed", displayRemoved);
    span.appendChild(selectedText);

    selection.insertNode(span);
}

function linkToNote(note_id, extract_type) {
    var selection = window.getSelection().getRangeAt(0);
    var selectedText = selection.extractContents();
    var note_link = document.createElement("a");

    note_link.className = "irx-extract-link-" + extract_type;
    note_link.setAttribute("href", "irxnid:" + note_id)
    note_link.appendChild(selectedText);

    selection.insertNode(note_link);
}

function format(style) {
    var selection = window.getSelection().getRangeAt(0);
    var selectedText = selection.extractContents();
    var span = document.createElement("span");

    span.className = "irx-highlight " + style;
    span.setAttribute("irx-overlay", formatting);
    span.appendChild(selectedText);

    selection.insertNode(span);
}

function toggleDisplayRemoved(state) {
    if (state == "toggle") {
        if (displayRemoved == "no") {
            displayRemoved = "yes";
        } else {
            displayRemoved = "no";
        }
    } else {
        displayRemoved = state
    }
    var elems = document.getElementsByClassName("irx-removed");
    for (var i = 0; i < elems.length; i++) {
        elems[i].setAttribute("irx-display-removed", displayRemoved)
    }
}

function toggleOverlay() {
    if (formatting == "on") {
        formatting = "off";
        turnoffHighlighting();
    } else {
        formatting = "on";
        restoreHighlighting();
    }
    var elems = document.getElementsByClassName("irx-highlight");
    for (var i = 0; i < elems.length; i++) {
        elems[i].setAttribute("irx-overlay", formatting)
    }
}