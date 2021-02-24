# -*- coding: utf-8 -*-

import sys, urllib, os, xbmc, xbmcaddon, xbmcgui, json, codecs, zipfile, random, contextlib, threading, re, urllib.request,xbmcvfs
from datetime import datetime, timedelta

__AddonID__ = 'plugin.video.annatel.tv'
__Addon__ = xbmcaddon.Addon(id=__AddonID__)
__AddonPath__ = xbmcvfs.translatePath(__Addon__.getAddonInfo('path'))
__AddonDataPath__ = os.path.join(xbmcvfs.translatePath( "special://userdata/addon_data").encode().decode("utf-8"), __AddonID__)
__DefaultTitle__ = __Addon__.getAddonInfo('name')
__TempPath__ = os.path.join(__AddonDataPath__, "temp")

sys.path.insert(0, os.path.join(__AddonPath__, "resources", "lib", "urllib3-1.11"))



random.seed()

def GetTotalSeconds(delta):
    total_seconds = (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10**6) / 10**6
    return total_seconds

def GetPosixDateTime(dt=None):
    if (dt is None):
        dt = datetime.now()
    psx = (dt - datetime(1970, 1, 1))
    total_seconds = GetTotalSeconds(psx)
    return total_seconds

def GetDateTimeFromPosix(dt=None):
    if (dt is None):
        return datetime.now()
    else:
        return datetime.utcfromtimestamp(float(dt))

def GetTimezoneDifferenceMinutes():
    tz_min = int(round(GetTotalSeconds(datetime.now() - datetime.utcnow()))) / 60
    return tz_min

def ParseEPGTimeUTC(epg_time):
    split_epg = epg_time.split(' ')
    dt = datetime.strptime(split_epg[0], "%Y%m%d%H%M%S")
    tz = int(split_epg[1][1:3]) * 60 + int(split_epg[1][3:5])
    if (split_epg[1][0] == "+"):
        return (dt - timedelta(minutes=tz))
    else: #(split_epg[1][0] == "-"):
        return (dt + timedelta(minutes=tz))
    
def FormatEPGTime(time_utc, timezone):
    time_by_tz = time_utc + timedelta(minutes=timezone)
    time_formatted = time_by_tz.strftime("%Y%m%d%H%M%S")
    tz_h = abs(timezone / 60)
    tz_m = abs(timezone) - tz_h * 60
    tz_formatted = str(tz_h).zfill(2) + str(tz_m).zfill(2)
    if (timezone >= 0):
        return "%s +%s" % (time_formatted, tz_formatted)
    else:
        return "%s -%s" % (time_formatted, tz_formatted)
    
def StartThread(func, args=None):
    thread = threading.Thread(target=func, args=args)
    thread.daemon = False
    thread.start()
    return thread

def Cmp(a, b): 
    return (int(a) > int(b)) - (int(a) < int(b))

def IsNewVersion(new_version, old_version):
    def normalize(v):
        return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]
    return (Cmp(normalize(new_version), normalize(old_version)) > 0)

def CleanTempFolder():
    if (os.path.exists(__TempPath__)):
        for f in os.listdir(__TempPath__):
            tmpfile = os.path.join(__TempPath__, f)
            if (os.path.isfile(tmpfile)):
                os.remove(tmpfile)

def GetTempFile(suffix=""):
    if (not os.path.exists(__TempPath__)):
        os.makedirs(__TempPath__)
    
    rnd = random.randint(1,100)
    filename = "tmp%i%i%s" % (int(GetPosixDateTime()), rnd, suffix)
    tmpfile = os.path.join(__TempPath__, filename)
    return tmpfile
    
def WriteFile(text, file_path, utf8=False,xlm=False):
    
    if (text is not None):
        local_dir = os.path.dirname(file_path)
        if (not os.path.exists(local_dir)):
            os.makedirs(local_dir)
        
        if (not utf8):
            if xlm:
                import xml.etree.ElementTree as ET
                tree = ET.ElementTree(ET.fromstring(text))
                tree.write(file_path)
            else: 
                with codecs.open(file_path, "w+") as openFile:
                    openFile.write(text)

        else:
            with codecs.open(file_path, "w+", "utf-8") as openFile:
                openFile.write(text)
    else:
        DeleteFile(file_path)

def WriteBinaryFile(bin, file_path):
    if (bin is not None):
        local_dir = os.path.dirname(file_path)
        if (not os.path.exists(local_dir)):
            os.makedirs(local_dir)
        
        with open(file_path, "wb") as openFile:
            openFile.write(bin)
    else:
        DeleteFile(file_path)

def WriteTempFile(bin, suffix=""):
    tmpfile = GetTempFile(suffix)
    WriteBinaryFile(bin, tmpfile)
    return tmpfile

def ReadFile(file_path):
    text = None
    if (os.path.exists(file_path)):
        with codecs.open(file_path, "r") as openFile:
            text = openFile.read()
    return text

def DeleteFile(file_path):
    if (os.path.exists(file_path)):
        os.remove(file_path)
    
def ReadZipUrl(url, filename, onDownloadSuccess=None, onDownloadFailed=None):
    response = None
    download_success_thread = None
    
    zipData = DownloadBinary(url)	
    tmpfile = None
    if (zipData is None):
        if (onDownloadFailed is not None):
            try:
                tmpfile = onDownloadFailed()
            except:
                tmpfile = None
    else:
        tmpfile = WriteTempFile(zipData, suffix=".zip")
        if (onDownloadSuccess is not None):
            def onDownloadSuccess_Modified(ods, tf):
                ods(tf)
                DeleteFile(tf)
            download_success_thread = StartThread(onDownloadSuccess_Modified, (onDownloadSuccess, tmpfile,))
    if (tmpfile is not None):
        binFile = None
        if (zipfile.is_zipfile(tmpfile)):
            with contextlib.closing(zipfile.ZipFile(tmpfile, 'r')) as myZip:
                binFile = myZip.read(filename)
        
        if (binFile is not None):
            response = binFile
        
        if (download_success_thread is None):
            DeleteFile(tmpfile)
    return response

def DownloadBinary(url):
    response = None
    urlResponse = None
    try:
        urlResponse = urllib.request.urlopen(url)
        if (urlResponse.code == 200): # 200 = OK
            response = urlResponse.read()
        else:
            print("ERROR")
    except:
        print("ERROR")
        pass
    finally:
        if (urlResponse is not None):
            urlResponse.close()
    return response

def DownloadFile(link, file_path):
    response = False
    try:
        urlData = DownloadBinary(link)
        if (urlData is not None):
            WriteBinaryFile(urlData, file_path)
            response = True
    except:
        pass
    return response



def GetLastModifiedLocal(local_path):
    localfile = os.path.join(local_path, "modified")
    date_str = ReadFile(localfile)
    if (date_str is None):
        return None
    else:
        return GetDateTimeFromPosix(date_str)

def SetLastModifiedLocal(local_path):
    localfile = os.path.join(local_path, "modified")
    date_str = str(GetPosixDateTime(datetime.now()))
    WriteFile(date_str, localfile)


def OKmsg(line1, line2 = None, line3 = None, title=__DefaultTitle__):
    dlg = xbmcgui.Dialog()
    dlg.ok(title, line1, line2, line3)

def ShowNotification(msg, duration, title=__DefaultTitle__, addon=None, sound=False):
    icon = None
    if (addon is not None):
        icon = addon.getAddonInfo('icon')
    dlg = xbmcgui.Dialog()
    dlg.notification(title, msg, icon, duration, sound)

def YesNoDialog(heading, message, nolabel, yeslabel):
    dlg = xbmcgui.Dialog()
    response = dlg.yesno(heading, message, nolabel, yeslabel)
    return response

def OpenSettings():
    #xbmc.executebuiltin('Addon.OpenSettings(%s)' % id)
    __Addon__.openSettings(__AddonID__)


class TV(object):
    def __init__(self, url, channel_name, tvg_id, tvg_logo=None, tvg_shift=0, group_title=None, radio=False):
        self.url = url
        #self.tvg_id = tvg_id
        self.tvg_id = tvg_id.replace('é'.encode().decode("utf8"), 'e').replace(' ','_')
        self.tvg_name = self.tvg_id #tvg_id.replace('é'.encode().decode("utf8"), 'e').replace(' ','_')
        self.tvg_logo = tvg_logo
        self.tvg_shift = tvg_shift
        self.group_title = group_title
        self.radio = radio
        self.channel_name = channel_name

class EPG(object):
    def __init__(self):
        self.channels = []
    
    def GetChannelByID(self, channel_id):
        for channel in self.channels:
            if (channel.id == channel_id):
                return channel
        return None

class Channel(object):
    def __init__(self, channel_id, display_name):
        self.id = channel_id
        self.display_name = display_name
        self.programs = []

class Program(object):
    def __init__(self, start, stop, title):
        self.start = start
        self.stop = stop
        self.title = title
        self.subtitle = None
        self.description = None
        self.credits = [] # list of key-value dictionaries
        self.category = None
        self.category_lang = None
        self.length = None
        self.length_units = None
        self.aspect_ratio = None
        self.star_rating = None
        self.icon = None
