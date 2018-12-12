var imagesSidebar = true;
var stylesVisible = true;
var highlightsVisible = true;
var removedVisible = false;
var lastImageUrl = "";

function markRange(identifier, attributes) {
    var sel = window.getSelection();
    if (sel.type == "Range") {
        var range = sel.getRangeAt(0);
        var targetRanges = Array();
        var targetAttrs = {};
        if (attributes.hasOwnProperty("bg")) {
            targetRanges = splitRange(range, null, "remove");
            targetAttrs["bg"] = attributes["bg"];
            targetAttrs["link"] = "irxnid:" + attributes["link"];
        } else if (attributes.hasOwnProperty("remove")) {
            targetRanges = splitRange(accumRemoveRange(range), null, "bg");
            targetAttrs["remove"] = attributes["remove"];
        } else if (attributes.hasOwnProperty("styles")) {
            targetRanges = splitRange(range, null, ["remove"]);
            targetAttrs["styles"] = attributes["styles"];
        }
        insertIrxSpans(targetRanges, identifier, targetAttrs);
    }
}

function insertIrxSpans(targetRanges, identifier, attributes) {
    for (var i = 0; i < targetRanges.length; i++) {
        var targetRange = targetRanges[i];
        var startNode = document.createElement('span');
        var endNode = document.createElement('span');
        startNode.setAttribute('id', ('sx' + identifier + '-' + i));
        endNode.setAttribute('id', ('ex' + identifier + '-' + i));
        startNode.setAttribute('irx-frag', i);
        endNode.setAttribute('irx-frag', i);
        startNode.setAttribute('irx-tot', targetRanges.length - 1);
        endNode.setAttribute('irx-tot', targetRanges.length - 1);
        for (var attr in attributes) {
            startNode.setAttribute('irx-' + attr, attributes[attr]);
            endNode.setAttribute('irx-' + attr, attributes[attr]);
        }
        //alert(startNode.outerHTML);
        // showRangeDetails(targetRange);
        var initialRangeEndNode = targetRange.endContainer.childNodes[targetRange.endOffset];
        // alert(Array.prototype.indexOf.call(targetRange.endContainer.childNodes, rangeEndNode))
        // showNodeDetails(rangeEndNode)
        targetRange.insertNode(startNode);
        // alert(Array.prototype.indexOf.call(targetRange.endContainer.childNodes, rangeEndNode))
        // showRangeDetails(targetRange);
        var followingRangeEndNode = targetRange.endContainer.childNodes[targetRange.endOffset];
        if (initialRangeEndNode != followingRangeEndNode) {
            var fixedOffset = Array.prototype.indexOf.call(targetRange.endContainer.childNodes, initialRangeEndNode);
            targetRange.setEnd(targetRange.endContainer, fixedOffset);
        }
        // showNodeDetails(rangeEndNode)
        // alert(targetRange.isPointInRange(startNode, 0));
        // var offset = Array.prototype.indexOf.call(startNode.parentNode.childNodes, startNode);
        // alert(offset);
        //targetRange.setStart(startNode.parentNode, offset + 1);
        // alert(targetRange.isPointInRange(startNode, 0));
        targetRange.collapse(false);
        // showRangeDetails(targetRange);
        targetRange.insertNode(endNode);
        // showRangeDetails(targetRange);
        targetRange.setStartAfter(startNode);
        // showRangeDetails(targetRange);
        targetRange.setEndBefore(endNode);
        // showRangeDetails(targetRange);
    }
}

function showRangeContents(range) {
    var div = document.createElement('div');
    div.appendChild(range.cloneContents().cloneNode(true));
    alert(div.innerHTML);
}

function showNodeDetails(node) {
    if (node.nodeType == Node.TEXT_NODE) {
        alert(node.textContent);
    } else {
        alert(node.outerHTML);
    }
}

function showRangeDetails(range) {
    startNode = range.startContainer;
    if (startNode.nodeType == Node.TEXT_NODE) {
        var startCont = "TEXT";
    } else {
        var startCont = startNode.tagName;
    }
    endNode = range.endContainer;
    if (endNode.nodeType == Node.TEXT_NODE) {
        var endCont = "TEXT";
    } else {
        var endCont = endNode.tagName;
    }
    alert("\nSTART: " + startCont + "\tOFFSET: " + range.startOffset + "\nEND: " + endCont + "\tOFFSET: " + range.endOffset);
}

function accumRemoveRange(range) {
    var fragment = range.cloneContents();
    var fragRemSpans = fragment.querySelectorAll("span[irx-remove][id^='sx'],span[irx-remove][id^='ex']");
    var fragRemSpansIds = Array();
    for (var i = 0; i < fragRemSpans.length; i++) {
        fragRemSpansIds.push(fragRemSpans[i].id);
    }
    for (var i = 0; i < fragRemSpans.length; i++) {
        if (fragRemSpans[i].id.indexOf("sx") == 0) {
            endRemSpan = document.getElementById(fragRemSpans[i].id.replace("sx", "ex"));
            if (endRemSpan != null) {
                if (fragRemSpansIds.indexOf(endRemSpan.id) < 0) {
                    range.setEndBefore(endRemSpan);
                    endRemSpan.parentNode.removeChild(endRemSpan);
                }
            }
        } else if (fragRemSpans[i].id.indexOf("ex") == 0) {
            startRemSpan = document.getElementById(fragRemSpans[i].id.replace("ex", "sx"));
            if (startRemSpan != null) {
                if (fragRemSpansIds.indexOf(startRemSpan.id) < 0) {
                    range.setStartAfter(startRemSpan);
                    startRemSpan.parentNode.removeChild(startRemSpan);
                }
            }
        }
        docRemSpan = document.getElementById(fragRemSpansIds[i]);
        if (docRemSpan != null) {
            docRemSpan.parentNode.removeChild(docRemSpan);
        }
    }
    return range;
}

function getSplitOnQuery(splitOn) {
    var splitOnArray = Array();
    if (!Array.isArray(splitOn)) {
        splitOnArray.push(splitOn);
    } else {
        splitOnArray = splitOn;
    }
    var splitOnQuery = Array();
    for (var i = 0; i < splitOnArray.length; i++) {
        splitOnQuery.push("span[irx-" + splitOnArray[i] + "][id^='sx'],span[irx-" + splitOnArray[i] + "][id^='ex']");
    }
    return splitOnQuery.join(",");
}

function splitRange(inputRanges, identifier, splitOn) {
    var rangesToSplit = Array();
    var outputRanges = Array();
    if (identifier != null) {
        rangesToSplit = selectMarkedRanges(identifier, true);
    } else if (!Array.isArray(inputRanges)) {
        rangesToSplit.push(inputRanges);
    } else {
        rangesToSplit = inputRanges;
    }
    for (var i = 0; i < rangesToSplit.length; i++) {
        range = rangesToSplit[i];
        var newRange = range.cloneRange();
        var fragment = range.cloneContents();
        var splitOnQuery = getSplitOnQuery(splitOn);
        var fragSplitOnSpans = fragment.querySelectorAll(splitOnQuery);
        var selSplitOnSpans = Array();
        for (var i = 0; i < fragSplitOnSpans.length; i++) {
            selSplitOnSpans.push(document.getElementById(fragSplitOnSpans[i].id));
        }
        var cnt = null;
        for (var i = 0; i < selSplitOnSpans.length; i++) {
            cnt = cnt == null ? 0 : cnt;
            if (selSplitOnSpans[i].id.indexOf("ex") == 0) {
                newRange.setStartAfter(selSplitOnSpans[i]);
                cnt = Math.max(0, cnt - 1);
            } else if (selSplitOnSpans[i].id.indexOf("sx") == 0) {
                if (cnt == 0) {
                    newRange.setEndBefore(selSplitOnSpans[i]);
                    outputRanges.push(newRange);
                    newRange = range.cloneRange();
                }
                cnt = cnt + 1;
            }
        }
        if (cnt == 0) {
            outputRanges.push(newRange);
        } else if (outputRanges.length == 0) {
            outputRanges.push(range);
        }
    }
    return outputRanges;
}


function computeStyles(startNode, newStyles) {
    if (startNode.hasAttribute("irx-styles")) {
        var attrVal = startNode.getAttribute("irx-styles") + " " + newStyles;
        var attrVals = attrVal.split(" ");
        attrVal = attrVals.filter(function (v, i, self) { return (self.indexOf(v) === i & v.length > 0) });
        attrVal = attrVal.join(" ");
    } else {
        var attrVal = attributes[attr];
    }
    return attrVal;
}


function selectMarkedRanges(identifier) {
    var startNode, endNode, range, sel;
    startNode = document.getElementById('sx' + identifier);
    endNode = document.getElementById('ex' + identifier);
    var targetRanges = Array();
    var rangeSpans = document.querySelectorAll("span[id^='sx" + identifier + "'],span[id^='ex" + identifier + "']");
    for (var i = 0; i < rangeSpans.length; i++) {
        if (rangeSpans[i].id.indexOf("sx") == 0) {
            startNode = rangeSpans[i];
            endNode = document.getElementById(startNode.id.replace("sx", "ex"));
            range = document.createRange();
            range.setStartAfter(startNode);
            range.setEndBefore(endNode);
            targetRanges.push(range);
        }
    }
    if (targetRanges.length > 0) {
        return targetRanges;
    }
    return false;
}

function clearOnRanges(targetRanges, targetClear, startNode) {
    var sel = window.getSelection();
    for (var i = 0; i < targetRanges.length; i++) {
        var range = targetRanges[i];
        document.designMode = "on";
        sel.removeAllRanges();
        sel.addRange(range);
        if (targetClear == "styles") {
            var irx_styles = startNode.getAttribute("irx-styles").split(" ");
            for (var s in irx_styles) {
                document.execCommand(irx_styles[s], true, true);
            }
        } else if (targetClear == "highlights") {
            document.execCommand("hiliteColor", false, 'transparent');
        }
        document.designMode = "off";
        sel.removeAllRanges();
    }
}

function markRangeRemoved(targetRange, visible) {
    var fragment = targetRange.extractContents();
    var remNodes = fragment.childNodes;
    var prevClass = !visible ? 'irx-removed-vis' : 'irx-removed-novis';
    var remClass = visible ? 'irx-removed-vis' : 'irx-removed-novis';
    for (var i = remNodes.length - 1; i >= 0; i--) {
        var thisNode = remNodes[i];
        if (thisNode.nodeType == Node.TEXT_NODE) {
            var textSpan = document.createElement('span');
            textSpan.setAttribute('class', remClass);
            textSpan.innerHTML = thisNode.wholeText;
            targetRange.insertNode(textSpan);
        } else {
            thisNodeClass = thisNode.getAttribute('class');
            thisNodeClass = thisNodeClass == null ? remClass : thisNodeClass.replace(prevClass, remClass);
            thisNode.setAttribute('class', thisNodeClass);
            targetRange.insertNode(thisNode);
        }
    }
}

function markRangeStyled(targetRange, visible, styles) {
    var fragment = targetRange.extractContents();
    var stylNodes = fragment.childNodes;
    var prevClass = !visible ? 'irx-styled-vis' : 'irx-styled-novis';
    var stylClass = visible ? 'irx-styled-vis' : 'irx-styled-novis';
    for (var i = stylNodes.length - 1; i >= 0; i--) {
        var thisNode = stylNodes[i];
        if (thisNode.nodeType == Node.TEXT_NODE) {
            var textSpan = document.createElement('span');
            var textSpanClass = stylClass + " " + styles.join(" ");
            textSpan.setAttribute('class', textSpanClass);
            textSpan.innerHTML = thisNode.wholeText;
            targetRange.insertNode(textSpan);
        } else if (thisNode.id.indexOf("sx") != 0 & thisNode.id.indexOf("ex") != 0) {
            thisNodeClass = thisNode.getAttribute('class');
            thisNodeClass = thisNodeClass == null ? stylClass : thisNodeClass.replace(prevClass, stylClass);
            for (var j = 0; j < styles.length; j++) {
                if (thisNodeClass.indexOf(styles[j]) < 0) {
                    thisNodeClass += " " + styles[j];
                }
            }
            thisNode.setAttribute('class', thisNodeClass);
            targetRange.insertNode(thisNode);
        } else {
            targetRange.insertNode(thisNode);
        }
    }
}


function execCommandOnRange(identifiers, attrs) {
    if (!Array.isArray(identifiers) & !selectMarkedRanges(identifiers, false)) {
        identifier = identifiers;
        markRange(identifier, attrs);
        identifiers = Array();
        identifiers.push(identifier);
    }
    for (var i in identifiers) {
        identifier = identifiers[i]
        var startNode = document.querySelector("span[id^='sx" + identifier + "']");
        if (startNode) {
            var targetRanges = selectMarkedRanges(identifier);
            var sel = window.getSelection();
            for (var i = 0; i < targetRanges.length; i++) {
                var range = targetRanges[i];

                document.designMode = "on";
                sel.removeAllRanges();
                sel.addRange(range);

                if (startNode.hasAttribute("irx-remove")) {
                    markRangeRemoved(range, removedVisible);
                }
                if (startNode.hasAttribute("irx-bg")) {
                    var irx_bg = highlightsVisible ? startNode.getAttribute("irx-bg") : 'transparent';
                    document.execCommand("hiliteColor", false, irx_bg);
                }
                if (startNode.hasAttribute("irx-link")) {
                    var irx_link = startNode.getAttribute("irx-link");
                    document.execCommand("createLink", false, irx_link);
                }
                if (startNode.hasAttribute("irx-styles")) {
                    var irx_styles = startNode.getAttribute("irx-styles").split(" ");
                    markRangeStyled(range, stylesVisible, irx_styles);
                }

                document.designMode = "off";
            }
            sel.removeAllRanges();
        }
    }
    attachEventsToIrxLinks();
}


function rangeIdsWithAttr(irxAttr) {
    var irxSpans = document.querySelectorAll("span[id^='sx'][irx-" + irxAttr + "]");
    var irxSpansIds = Array();
    for (var i = 0; i < irxSpans.length; i++) {
        irxSpansIds.push(irxSpans[i].id.substring(2));
    }
    return irxSpansIds;
}

function toggleStyles(manual) {
    var prevClass = stylesVisible ? 'irx-styled-vis' : 'irx-styled-novis';
    if (!manual | manual == "toggle") {
        stylesVisible = !stylesVisible;
    } else {
        stylesVisible = manual;
    }
    var currClass = stylesVisible ? 'irx-styled-vis' : 'irx-styled-novis';
    if (prevClass != currClass) {
        var remNodes = document.querySelectorAll("." + prevClass);
        for (var i = 0; i < remNodes.length; i++) {
            remNodes[i].setAttribute('class', remNodes[i].getAttribute('class').replace(prevClass, currClass));
        }
    }
}

function toggleHighlights(manual) {
    prev_state = highlightsVisible;
    if (!manual | manual == "toggle") {
        highlightsVisible = !highlightsVisible;
    } else {
        highlightsVisible = manual;
    }
    if (prev_state != highlightsVisible) {
        execCommandOnRange(rangeIdsWithAttr('bg'), null);
    }
}

function toggleRemoved(manual) {
    var prevClass = removedVisible ? 'irx-removed-vis' : 'irx-removed-novis';
    if (manual == undefined | manual == "toggle") {
        removedVisible = !removedVisible;
    } else {
        removedVisible = manual;
    }
    var currClass = removedVisible ? 'irx-removed-vis' : 'irx-removed-novis';
    if (prevClass != currClass) {
        var remNodes = document.querySelectorAll("." + prevClass);
        for (var i = 0; i < remNodes.length; i++) {
            remNodes[i].setAttribute('class', remNodes[i].getAttribute('class').replace(prevClass, currClass));
        }
    }
}

function attachEventsToIrxLinks() {
    var links = document.querySelectorAll("a[href^='irxnid:']:not([onmouseover])");
    for (var k = 0; k < links.length; k++) {
        links[k].setAttribute('onmouseover', 'hoverState("' + links[k].getAttribute('href') + '", "on")');
        links[k].setAttribute('onmouseout', 'hoverState("' + links[k].getAttribute('href') + '", "off")');
    }
}

function hoverState(irxnid, state) {
    var links = document.querySelectorAll("a[href*='" + irxnid + "']");
    var linkStyle = state == "on" ? 'color: magenta' : '';
    for (var k = 0; k < links.length; k++) {
        links[k].setAttribute('style', linkStyle);
    }
}

function toggleImagesSidebar(manual) {
    var prev_state = imagesSidebar;
    if (!manual | manual == "toggle") {
        imagesSidebar = !imagesSidebar;
    } else {
        imagesSidebar = manual;
    }
    if (prev_state != imagesSidebar) {
        var attrVal = imagesSidebar ? "yes" : "no";
        var text = document.getElementsByClassName("irx-text")[0];
        var images = document.getElementsByClassName("irx-images")[0];
        text.setAttribute("irx-images-sidebar", attrVal);
        images.setAttribute("irx-images-sidebar", attrVal);
    }
}