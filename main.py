from htmlTools import *

import urllib.parse
import threading
import requests
import random
import shutil
import queue
import json
import math
import time
import sys
import os
import re

startTime = time.time()

nRequests = 0
# setup credentials
credentials = {}
file = open("credentials.json", "r")
credentials = json.load(file)
file.close()

readHex = False # read the cmd args in as hex
# parse cli arguments
for i in range(len(sys.argv)):
    cmd = sys.argv[i]
    arg1 = ""
    arg2 = ""
    if i + 1 < len(sys.argv):
        arg1 = sys.argv[i+1]
    if i + 2 < len(sys.argv):
        arg2 = sys.argv[i+2]
    if cmd == "-readHex": 
        readHex = True
    if cmd == "-set":
        if readHex:
            try:
                arg1 = bytearray.fromhex(arg1).decode("utf-8")
            except:
                print("cannot decode argument 1 for command '" + cmd + "' (" + str(arg1) + ")")
            try:
                arg2 = bytearray.fromhex(arg2).decode("utf-8")
            except:
                print("cannot decode argument 2 for command '" + cmd + "' (" + str(arg2) + ")")
        if arg2 == "true":
            arg2 = True
        if arg2 == "false":
            arg2 = False
        credentials[arg1] = arg2

# create the log folder, if it doesn't exist
try:
    os.mkdir(credentials["logFolder"])
except FileExistsError:
    pass

if credentials["logs"]:
    logF = open(credentials["logFolder"] + desinfectString(credentials["username"]) + ".log", "w")
_print = print
def print(line):
    global _print
    _print(line)
    sys.stdout.flush()
    if credentials["logs"]:
        global logF
        logF.write(line + "\n")
        logF.flush()

# testfile
counter = 0
def tfile(text, ending="html"):
    global counter
    counter += 1
    f = open("test" + str(counter) + "." + ending, "wb")
    f.write(text.encode("latin1"))
    f.close()

s = requests.session()

# login
print("login")
if credentials["useCredentials"]:
    req = s.post(credentials["moodleUrl"] + "login/index.php",
    data={
        "username": credentials["username"],
        "password": credentials["password"],
        "rememberusername": 1,
        "anchor": ""
    },
    headers={
        "content-type": "application/x-www-form-urlencoded"
    })
    nRequests += 1
else:
    s.cookies["MOODLEID1_"] = credentials["cookie_MOODLEID1_"]
    s.cookies["MoodleSession"] = credentials["cookie_MoodleSession"]

# get section tab url
print("finding the sections tab")
req = s.get(credentials["moodleUrl"])
cPos, html = getElement(req.text, '<div id="inst995')
grade = re.findall('href="([^>]*)">([A-Z]{2,3}[0-9]{1,2}[A-Z]?)</a>', html)[0]
print("Detected Grade " + grade[1])

# get sections
print("requesting sections")
req = s.get(grade[0])

if req.url.find("login/index.php") != -1:
    print("The provided credentials did not work. Please try again")

nRequests += 1

# TODO: add a check for a vaid response

# create nesecarry folders
try:
    os.mkdir("output/")
except FileExistsError:
    pass
try:
    os.mkdir("output/"+desinfectString(credentials["username"]))
except FileExistsError:
    pass

# helper functions
def mkdir(path):
    try:
        os.mkdir("output/"+desinfectString(credentials["username"])+"/"+path)
    except FileExistsError:
        pass

def idToStr(i):
    if type(i) == str:
        return i
    o = str(i)
    if len(o)<2:
        o = "0" + o
    return o

def reqCntPP():
    global nRequests
    with threading.Lock():
        nRequests += 1

def unzip(fromFile, toFolder, delete=True):
    if os.name == "nt": # windows config
        os.system('7z x "' + fromFile + '" -o"' + toFolder + '" -y > nul') # 7z
    if os.name == "posix": # rpi config
        os.system('unzip -q "' + fromFile + '" -d "' + toFolder + '"') # unzip
    if delete:
        os.remove(fromFile)

def zip(username, deleteFolder=True):
    cd = os.curdir
    os.chdir(cd + "/output")
    if os.name == "nt": # windows config
        os.system('7z a "' + username + '.zip" "' + username + '" -y > nul') # 7z
    if os.name == "posix": # rpi config
        os.system('zip -r "' + username + '.zip" "' + username + '"') # unzip
    if deleteFolder:
        shutil.rmtree(username)
    os.chdir(cd)

# queue for requests
q = queue.Queue()

# enqueue all found sections with the section handler
cPos = 0
sectionIdCounter = 0
while cPos != -1:
    cPos, sectionHtml = getElement(req.text, '<li id="section-', cPos)
    ok, sec = parseSection(sectionHtml)
    if ok:
        sectionIdCounter += 1
        sec["path"] = idToStr(sectionIdCounter) + " " + desinfectString(sec["name"])
        mkdir(sec["path"])
        q.put({
            "handler": "section",
            "data": sec
        })
        print("-> " + sec["name"] + " " + sec["url"])

# paralell tasks

# section handler
def tHandler_section(section):
    global nRequests
    global s # session
    global q
    cPos = 0
    itemCounter = 0

    print("[section    ] " + section["name"])
    
    # get all section elements
    reqCntPP()
    req = s.get(section["url"])
    while cPos != -1:
        cPos, sectionHtml = getElement(req.text, '<a class="" onclick="" href="', cPos)
        ok, entry = parseSectionEntry(sectionHtml)
        if ok and entry["type"] != "Forum":
            itemCounter += 1
            entry["count"] = itemCounter
            entry["section"] = section["name"]
            entry["path"] = section["path"] + "/"
            mkdir(entry["path"])
            q.put({
                "handler": "sectionEntry-" + entry["type"],
                "data": entry
            })

# 'Aufgabe' (ger: task) is the term used to identify the type of element
def tHandler_sectionEntry_Aufgabe(data):
    print("[aufgabe    ] " + data["path"])

    data["path"] += idToStr(data["count"]) + " (A) " + desinfectString(data["name"])
    mkdir(data["path"])

    reqCntPP()
    req = s.get(data["url"])

    variations = [
        {"i": 0, "folder": "material", "selector": '<div id="intro" class="box generalbox boxaligncenter"'},
        {"i": 1, "folder": "upload"  , "selector": '<div class="box boxaligncenter plugincontentsummary summary_assignsubmission_file_'},
        {"i": 2, "folder": "feedback", "selector": '<div class="box boxaligncenter plugincontentsummary summary_assignfeedback_file_'}
    ]

    fileCounter = 0
    # material download
    for variation in variations:
        cPos, mainContentHtml = getElement(req.text, variation["selector"], 0)
        if cPos != -1: # we have a main area
            if variation["i"] == 0:
                cPos, task = getElement(mainContentHtml, '<div class="no-overflow">')
                if cPos != -1: # we have a task description
                    taskData = task[25:-6]
                    if len(taskData) > 0: # only bother to save a file, if its not empty
                        fileCounter += 1
                        f = open("output/" + desinfectString(credentials["username"]) + "/" + data["path"] + "/" + idToStr(fileCounter) + " task.html", "wb")
                        try:
                            f.write(taskData.encode("utf-8"))
                        except:
                            print("\nDECODE ERROR")
                            print(taskData)
                            print()
                        f.close()
            cPos, mainContentHtmlFileTree = getElement(mainContentHtml, '<div id="assign_files_tree', 0)
            if cPos != -1: # we have a file tree
                ok, files = getFileTreeFiles(mainContentHtmlFileTree)
                if ok: # we have files
                    # mkdir(data["path"] + "/" + variation["folder"])
                    for i in range(len(files)):
                        fileCounter += 1
                        q.put({
                            "handler": "sectionEntry-Datei",
                            "data": {
                                "path": data["path"] + "/" + idToStr(fileCounter) + " " + variation["folder"] + " -",
                                "url": files[i]["url"],
                                "count": ""
                            }
                        })
        if not credentials["downloadUserGeneratedContent"]:
            break


# 'Verzeichnis' (ger: folder) is the term used to identify the type of element
def tHandler_sectionEntry_Verzeichnis(data):
    path = data["path"] + idToStr(data["count"]) + " " + desinfectString(data["name"])
    print("[verzeichnis] " + path)
    mkdir(path)

    reqCntPP()
    req = s.get(data["url"])
    ok, folderDetail = getFolderDetail(req.text)
    if not ok:
        print("cannot download " + path + "(failed to extract the download details)")
        return -10
    
    reqCntPP()
    req = s.post(credentials["moodleUrl"] + credentials["moodleDownloadFolderUrl"], data=folderDetail)

    fullFileName = path + "/temp.zip"
    f = open("output/" + desinfectString(credentials["username"]) + "/" + fullFileName,"wb")
    f.write(req.content)
    f.close()

    unzip(
        "output/" + desinfectString(credentials["username"]) + "/" + fullFileName,
        "output/" + desinfectString(credentials["username"]) + "/" + path
    )
    print("[verzeichnis] " + fullFileName + " finished downloading")
    

# 'Datei' (ger: file) is the term used to identify the type of element
def tHandler_sectionEntry_Datei(data):
    print("[datei      ] " + data["path"])

    reqCntPP()
    # download the file
    req = s.get(data["url"])
    querry = urllib.parse.unquote(urllib.parse.urlparse(req.url).query)
    cPos = 0
    while True:
        nextSlash = querry.find("/", cPos)
        if nextSlash == -1:
            break
        cPos = nextSlash + 1
    fName = desinfectString(querry[cPos:])

    fullFileName = data["path"] + idToStr(data["count"]) + " " + fName
    f = open("output/" + desinfectString(credentials["username"]) + "/" + fullFileName,"wb")
    f.write(req.content)
    f.close()
    print("[datei      ] " + fullFileName + " finished downloading")

# 'Datei' (ger: file) is the term used to identify the type of element
def tHandler_sectionEntry_Test(data):
    data["path"] += str(data["count"]) + " (T) " + desinfectString(data["name"])
    mkdir(data["path"])
    print("[test       ] (Test downloads are unsupported) " + data["path"])

# map tasks to names
tHandler = {
    "section": tHandler_section,
    "sectionEntry-Aufgabe": tHandler_sectionEntry_Aufgabe,
    "sectionEntry-Verzeichnis": tHandler_sectionEntry_Verzeichnis,
    "sectionEntry-Datei": tHandler_sectionEntry_Datei,
    "sectionEntry-Test": tHandler_sectionEntry_Test
}

# thread to get one item from the queue and run its handler with its data
def thread():
    global q
    while q.qsize() > 0:
        time.sleep(random.random())
        task = q.get()
        if not task["handler"] in tHandler:
            print("Handler '" + task["handler"] + "' is not supported!")
        else:
            returnCode = 0
            try:
                returnCode = tHandler[task["handler"]](task["data"])
            except requests.exceptions.ConnectionError:
                returnCode = -10
            if returnCode == -10:
                q.put(task)
                time.sleep(0.5)
                print("[thread     ] requeuing for handler: " + task["handler"])
        q.task_done()

# activate all threads (number defined in credentials by maxConnections)
print("\nrequesting section data")
threads = {}
for i in range(credentials["maxConnections"]):
    threads[i] = threading.Thread(target=thread)
    threads[i].daemon = True
    threads[i].start()

# wait for all tasks to finish
while q.qsize() > 0 or q.unfinished_tasks > 0:
    time.sleep(1)

print("zipping results")
zip(desinfectString(credentials["username"]), deleteFolder=True)

dt = (math.floor(time.time() - startTime)*100)/100
print("\n Requested " + str(nRequests) + " pages in " + str(dt) + "s")
if credentials["logs"]:
    logF.close()