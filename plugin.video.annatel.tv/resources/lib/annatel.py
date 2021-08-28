# -*- coding: utf-8 -*-

import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs
import sys, os, urllib
import common
from xml.dom.minidom import parseString
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

URL_XML_FEED = 'https://www.annatel.tv/api/getchannels?login=%s&password=%s'
URL_EPG_FEED = 'http://xmltv.bigsb.fr/xmltv.zip'
__AddonID__ = 'plugin.video.annatel.tv'
__Addon__ = xbmcaddon.Addon(__AddonID__)
__AddonDataPath__ = os.path.join(xbmcvfs.translatePath("special://userdata/addon_data").encode().decode("utf-8"),
                                 __AddonID__)
__XML__ = os.path.join(__AddonDataPath__, "Annatel", "XML")
__EPG__ = os.path.join(__AddonDataPath__, "Annatel", "EPG")


def GetCredentials():
    username = __Addon__.getSetting('username')
    password = __Addon__.getSetting('password')
    return username, password


def IsLoggedIn():
    username, password = GetCredentials()
    return username is not None and username != "" and password is not None and password != ""


def LoadLogin():
    resp = common.YesNoDialog("Authentification!",
                              "Il faut configurer votre login et mot de passe Annatel TV!\nCliquez sur Yes pour configurer votre login et mot de passe",
                              nolabel="Non",
                              yeslabel="Oui")
    if (resp):
        common.OpenSettings()
    else:
        common.ShowNotification("Authentification!\nMerci d\'entrer votre login et mot de passe Annatel TV", 10,
                                addon=__Addon__)


def GetTVChannels():
    if IsLoggedIn():
        username, password = GetCredentials()
        xml_link = URL_XML_FEED % (urllib.parse.quote(username), urllib.parse.quote(password))
        local_xml = os.path.join(__XML__, "annatel.xml")
        xbmc.log("XML LINK:" + xml_link)

        doc = common.DownloadBinary(xml_link)
        if doc is None:
            doc = common.ReadFile(local_xml)
        else:
            common.WriteFile(doc, local_xml, False, True)
            common.SetLastModifiedLocal(__XML__)

        if doc is not None:
            response = []
            parsed_doc = parseString(doc)
            for channel in parsed_doc.getElementsByTagName('channel'):
                name = channel.getElementsByTagName('name')[0].childNodes[0].data
                url = channel.getElementsByTagName('url')[0].childNodes[0].data
                logo = channel.getElementsByTagName('logo')[0].childNodes[0].data
                tv_channel = common.TV(url, name, name, tvg_logo=logo)
                response.append(tv_channel)

            return response
        else:
            return None
    else:
        return None


def IsOldEPG():
    modified = common.GetLastModifiedLocal(__EPG__)
    if (modified is not None):
        today = datetime.now()
        return ((today - modified).days > 3)
    else:
        return True


def GetEPG():
    xbmc.log("Getting EPG")
    epg_xml = common.ReadZipUrl(URL_EPG_FEED, "xmltv.xml")
    local_epg = os.path.join(__EPG__, "tvguide.xml")
    if epg_xml is not None:
        xbmc.log("EPG data found")
        common.WriteFile(epg_xml.decode(), local_epg)
        common.SetLastModifiedLocal(__EPG__)
    else:
        epg_xml = common.ReadFile(local_epg)

    if epg_xml is not None:
        epg = ParseEPG(epg_xml)
        xbmc.log("finished parsing epg")
        FixEPGChannelsIDs(epg)
        xbmc.log("fixed epg channel ids")
        return epg
    else:
        return None


def ParseEPG(epg_xml):
    xbmc.log("parsing epg")
    epg = None
    if epg_xml is not None:
        parsed_epg = ET.fromstring(epg_xml)
        epg = common.EPG()
        for channel in parsed_epg.findall('channel'):
            channel_id = channel.get("id")
            display_name = channel.find('display-name').text
            channel_epg = common.Channel(channel_id, display_name)
            epg.channels[channel_id] = channel_epg
            # xbmc.log("found channel {}".format(channel_epg.__dict__))

        current_channel = None
        for program in parsed_epg.findall('programme'):
            start = program.get("start")
            # if start_str is not None:
            #     start = common.ParseEPGTimeUTC(start_str)
            stop = program.get("stop")
            # if stop_str is not None :
            #     stop = common.ParseEPGTimeUTC(stop_str)
            # xbmc.log("fetched start {} stop {}".format(start_str, stop_str))
            # start = common.ParseEPGTimeUTC(program.get("start").encode("utf-8"))
            # stop = common.ParseEPGTimeUTC(program.get("stop").encode("utf-8"))
            title = program.find('title').text

            # try:		subtitle = program.find('sub-title').text.encode("utf-8")
            # except:		subtitle = None

            try:
                description = program.find('desc').text
            except:
                description = None

            # try:		aspect_ratio = program.find("aspect").text.encode("utf-8")
            # except:		aspect_ratio = None

            # try:		star_rating = program.find("star-rating")[0].text.encode("utf-8") # <star-rating><value>2/5</value></star-rating>
            # except:		star_rating = None

            # credits = []
            # try:
            #	for credit in program.find('credits'):
            #		job = credit.tag.encode("utf-8")
            #		name = credit.text.encode("utf-8")
            #		credits.append({job:name})
            # except:
            #	pass

            try:
                categoryNode = program.find('category')
                category = categoryNode.text
                category_lang = categoryNode.get("lang")
            except:
                category = None
                category_lang = None

            # try:
            #	lengthNode = program.find('length')
            #	length = lengthNode.text.encode("utf-8")
            #	length_units = lengthNode.get("units").encode("utf-8")
            # except:
            #	length = None
            #	length_units = None

            try:
                icon_node = program.find('icon')
                program_icon = icon_node.get("src")
            except:
                program_icon = None

            program_epg = common.Program(start, stop, title)
            # program_epg.subtitle = subtitle
            program_epg.description = description
            # program_epg.credits = credits
            program_epg.category = category
            program_epg.category_lang = category_lang
            # program_epg.length = length
            # program_epg.length_units = length_units
            # program_epg.aspect_ratio = aspect_ratio
            # program_epg.star_rating = star_rating
            program_epg.icon = program_icon
            # xbmc.log("found program {}".format(program_epg.__dict__))

            channel_id = program.get("channel")
            # xbmc.log("found program {}, channel {}".format(title, channel_id))
            if current_channel is None or current_channel.id != channel_id:
                current_channel = epg.channels.get(channel_id)
            if current_channel is not None:
                current_channel.programs.append(program_epg)

    return epg


def FixEPGChannelsIDs(epg):
    xbmc.log("fixing EPG channel ids")
    if epg is not None:
        # ids = {
        #     "1": "TF1",
        #     "2": "France_2",
        #     "3": "France_3",
        #     "4": "Canal_+",
        #     "5": "France_5",
        #     "6": "M6",
        #     "7": "Arte",
        #     "8": "D8",
        #     "9": "W9",
        #     "10": "TMC",
        #     "11": "NT1",
        #     "12": "NRJ_12",
        #     "13": "France_4",
        #     "15": "BFM_TV",
        #     # "16"	:	"i-télé",
        #     "16": "i-tele",
        #     "17": "D17",
        #     "18": "Gulli",
        #     # "43"	:	"Canal+_Cinéma",
        #     "43": "Canal+_Cinema",
        #     "45": "Canal+_Family",
        #     "47": "Canal+_Sport",
        #     "62": "Cine+_Premier",
        #     "68": "Comedie+",
        #     "74": "Disney_Channel",
        #     "75": "Disney_Cinema",
        #     "83": "Equidia",
        #     "87": "EuroNews",
        #     "89": "EuroSport",
        #     "90": "EuroSport2",
        #     "119": "France_O",
        #     "168": "National_Geo",
        #     "171": "NickJr_France",
        #     "186": "Paris_Première",
        #     "194": "Disney_Junior",
        #     "199": "RTL9",
        #     # "227"	:	"Téva",
        #     "227": "Teva",
        #     "288": "France_24",
        #     # "4138"	:	"Canal+_Séries",
        #     "4138": "Canal+_Series",
        #     "4139": "BeIN_Sport_1_HD",
        #     "4140": "BeIN_Sport_2_HD"
        # }

        # for channel in epg.channels:
        #     if channel.id in ids:
        #         channel.id = ids[channel.id]

        duplicates = [
            ("BeIN_Sport_1", "BeIN Sport 1", "beINSPORTS1.fr"),
            ("BeIN_Sport_2", "BeIN Sport 2", "beINSPORTS2.fr"),
            ("TF1_HD", "TF1 HD", "TF1.fr"),
            ("France_2_HD", "France 2 HD", "France2.fr"),
            ("Canal+_HD", "Canal+ HD", "CanalPlus.fr"),
            ("M6_HD", "M6 HD", "M6.fr"),
        ]

        for channel_id, channel_name, clone_id in duplicates:
            new_channel = common.Channel(channel_id, channel_name)
            original_channel = epg.channels.get(clone_id)
            if original_channel is not None:
                new_channel.programs = original_channel.programs
                epg.channels[new_channel.id] = new_channel
