%cd "/content/drive/My Drive/Twitch Downloader"
import requests
from datetime import datetime
global counter
global lengther
global lengthersr
global startercounter
global aditionalcounter
global count
global username
global adder
global linecounter
global isnumber
global content
global lister
global listerr
global listadder
global reader
global isitequal
OverallTimer = datetime.now()
counter = -1
count = -1
lengther = 0
lengthersr = 0
linecounter = 0
reader = open("CounterStrike5.txt", "r")
adder = open("EmptyFile.txt", "w")
adderr = reader.readlines()
print(len(adderr))
amnino = int(adderr[linecounter])
amnino1 = amnino + 1
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino1 = amnino + 1
print("Overidder" + str(amnino1))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino2 = amnino + 1
print("Overidder" + str(amnino2))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino3 = amnino + 1
print("Overidder" + str(amnino3))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino4 = amnino + 1
print("Overidder" + str(amnino4))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino5 = amnino + 1
print("Overidder" + str(amnino5))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino6 = amnino + 1
print("Overidder" + str(amnino6))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino7 = amnino + 1
print("Overidder" + str(amnino7))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino8 = amnino + 1
print("Overidder" + str(amnino8))
# amnino
amnino = int(adderr[linecounter])
amnino9 = amnino + 1
print("Overidder" + str(amnino9))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino10 = amnino + 1
print("Overidder" + str(amnino10))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino11 = amnino + 1
print("Overidder" + str(amnino11))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino12 = amnino + 1
print("Overidder" + str(amnino12))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino13 = amnino + 1
print("Overidder" + str(amnino13))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino14 = amnino + 1
print("Overidder" + str(amnino14))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino15 = amnino + 1
print("Overidder" + str(amnino15))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino16 = amnino + 1
print("Overidder" + str(amnino16))
linecounter = linecounter + 1
# amnino
amnino = int(adderr[linecounter])
amnino17 = amnino + 1
print("Overidder" + str(amnino17))
zanana = open("CounterStrike6.txt", "w")
zanana.write(str(amnino) + "\n" + str(amnino1) + "\n" + str(amnino2) + "\n" + str(amnino3) + "\n" + str(amnino4) + "\n" + str(amnino5) + "\n" + str(amnino6) + "\n" + str(amnino7) + "\n" + str(amnino8) + "\n" + str(amnino9) + "\n" + str(amnino10) + "\n" + str(amnino11) + "\n" + str(amnino12) + "\n" + str(amnino13) + "\n" + str(amnino14) + "\n" + str(amnino15) + "\n" + str(amnino16) + "\n" + str(amnino17))
zanana.close()
linecounter = linecounter + 1
linecounter = 0
adder.close()
reader.close()
lister = open("List9.txt", "r")
listadder = open("List9.txt", "a")
listerr = lister.read()
lenghterrrrr = len(listerr)
print("from datetime import datetime")
print("OverallTimer = datetime.now()")
count = 0
isnumber = 1
startercounter = -1
def SetLengthersr(balance):
  global lengthersr
  lengthersr = balance
def SetIsItEqual(bance):
  global isitequal
  isitequal = bance
def SetLineCounter(bounce):
  global linecounter
  linecounter = bounce
Lengthersr = 0
def urlersr(urlazn, uanaza):
  SetIsItEqual(0)
  url = urlazn
  r = requests.get(str(url))
  content = r.text
  lengther = len(content)
  SetLengthersr(lengther + 1)
  username = "uhhhhhhhhhhhhhh"
  count = -1
  while username == "uhhhhhhhhhhhhhh":
    count = count + 1
    if content[count - 16:count] == '"display_name":"':
      aditionalcounter = count
      startercounter = count
      while not content[aditionalcounter] == '"':
        aditionalcounter = aditionalcounter + 1
      username = str(content[startercounter:aditionalcounter])
  isitstreaming = 0
  count = -1
  while count < Lengthersr:
    count = count + 1
    if content[count:count + 9] == "recording":
      isitstreaming = 1
  print('%cd "/content/drive/Shared drives/Downloads/filipetaleshipolitosoares73/Twitch/' + username + '"')
  print('!mkdir "' + str(uanaza) + '"')
  print('%cd "/content/drive/Shared drives/Downloads/filipetaleshipolitosoares73/Twitch/' + username + "/" + str(uanaza) + '"')
  count = 0
  twister = 0
  if isitstreaming == 1:
    twister = content.find('/videos/', count)
    count = twister + 1
    twistera = content.find('/', count)
    count = twistera + 1
    startercounter = count
    twisterb = content.find('"', count)
    count = twisterb
  while not twister == -1:
    twister = content.find('/videos/', count)
    count = twister + 1
    twistera = content.find('/', count)
    if twistera == -1:
      twister = -1
    count = twistera + 1
    startercounter = count
    twisterb = content.find('"', count)
    if twisterb == -1:
      twister = -1
    count = twisterb
    aditionalcounter = count
    if not str(content[startercounter:aditionalcounter]) in listerr:
      if len(content[startercounter:aditionalcounter]) < 11:
        print("ReaderTimer = datetime.now()")
        print("!twitch-dl download -q source " + content[startercounter:aditionalcounter])
        print("print(str(datetime.now() - ReaderTimer) + ' ' + str(datetime.now() - OverallTimer))")
        listadder.write(" " + content[startercounter:aditionalcounter])
    count = aditionalcounter
    SetLineCounter(linecounter + 1)
urlersr('https://api.twitch.tv/kraken/channels/12826/videos?broadcast_type=archive&client_id=9kr7kfumdnzkcr9rgg4g0qtfnk2618&api_version=5&limit=100', amnino)
print("print(Finished Downloading All Videos In: + str(datetime.now() - OverallTimer))")
finishertime = datetime.now() - OverallTimer
print("Finished in:" + str(finishertime))
lister.close()
listadder.close()
