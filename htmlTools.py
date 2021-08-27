import re

def desinfectString(string : str):
    return re.sub("[^a-zA-Z 0-9\\-_äüöÄÜÖ#*=\\(\\)\\[\\]\\{\\}\\.]+", "", string).replace("..", "")

def getElement(html, beginning, searchFrom = 0):
    cPos = html.find(beginning, searchFrom)
    beginPos = cPos

    if cPos == -1:
        return -1, ""

    balance = 1 # start at 0
    while balance > 0:
        s = html.find("<", cPos + 1)   # open
        e1 = html.find("</", cPos + 1) # close
        e2 = html.find("/>", cPos + 1) # close self closing

        if s == e1 == e2 == -1:
            cPos = len(html)
            break
        if s == -1:
            s = len(html)
        if e1 == -1:
            e1 = len(html)
        if e2 == -1:
            e2 = len(html)

        if e1 <= s and e1 < e2: # next is close tag
            balance -= 1
            cPos = e1
        elif e2 < s and e2 < e1: # next is end of self closing tag
            balance -= 1
            cPos = e2 + 1
        elif s < e1 and s < e2: # next is open tag
            balance += 1
            cPos = s

    cPos = html.find(">", cPos) + 1
    return cPos, html[beginPos:cPos]

def removeElement(html, beginning):
    s = html.find(beginning)
    cPos, _ = getElement(html, beginning)
    return html[:s] + html[cPos:] 

def htmlUnescape(html):
    return html.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

def parseSection(html):
    match = re.findall('<a href="([^>]*)" class="">([^>]*)</a>', html)
    if len(match) == 0 or len(match[0]) != 2:
        return False, {}
    return True, {
        "name": match[0][1].strip(),
        "url": htmlUnescape(match[0][0])
    }

def parseSectionEntry(html):
    match = re.findall('<a class="" onclick="" href="([^>]*)"><img[^>]*/><span class="instancename">([^>]*)<span class="accesshide " >([^>]*)</span>', html)
    if len(match) == 0 or len(match[0]) != 3:
        return False, {}
    return True, {
        "url": htmlUnescape(match[0][0]),
        "name": match[0][1].strip(),
        "type": match[0][2].strip()
    }

def getFolderDetail(html):
    match = re.findall('<input type="hidden" name="id" value="([^>]*)" /><input type="hidden" name="sesskey" value="([^>]*)" />', html)
    if len(match) == 0 or len(match[0]) != 2:
        return False, {}
    return True, {
        "id": match[0][0],
        "sesskey": match[0][1]
    }

def getFileTreeFiles(html):
    match = re.findall('<a target="_blank" href="([^>]*)">([^>]*)</a>', html)
    out = []
    for i in range(len(match)):
        out += [{
            "url": match[i][0].replace("&amp;amp;forcedownload=1", ""),
            "name": match[i][1]
        }]
    if len(match) == 0:
        return False, []
    return True, out
