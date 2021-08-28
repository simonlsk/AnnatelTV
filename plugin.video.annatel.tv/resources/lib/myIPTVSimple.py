# -*- coding: utf-8 -*-

import urllib, sys, re, xbmc, xbmcgui, xbmcaddon, os, json, common, xbmcvfs
import xml.etree.ElementTree as ET

__AddonID__ = 'plugin.video.annatel.tv'
__Addon__ = xbmcaddon.Addon(__AddonID__)
PVR_ADDON_ID = "pvr.iptvsimple"
__IPTVSimple__AddonDataPath____ = os.path.join(
    xbmcvfs.translatePath("special://userdata/addon_data").encode().decode("utf-8"), PVR_ADDON_ID)
__AddonDataPath__ = os.path.join(xbmcvfs.translatePath("special://userdata/addon_data").encode().decode("utf-8"),
                                 __AddonID__)

if (not os.path.exists(__AddonDataPath__)):
    os.makedirs(__AddonDataPath__)


def GetIptvAddon(show_message=False):
    iptvAddon = None

    if os.path.exists(xbmcvfs.translatePath("special://home/addons/").encode().decode(
            "utf-8") + PVR_ADDON_ID) or os.path.exists(
            xbmcvfs.translatePath("special://xbmc/addons/").encode().decode("utf-8") + PVR_ADDON_ID):
        try:
            iptvAddon = xbmcaddon.Addon(PVR_ADDON_ID)
        except:
            print("---- Annatel ----\nIPTVSimple addon is disable.")
            msg1 = "PVR IPTVSimple is Disable."
            msg2 = "Please enable IPTVSimple addon."
    else:
        msg1 = "PVR IPTVSimple is NOT installed on your machine."
        msg2 = "Please install XBMC version that include IPTVSimple in it."

    if iptvAddon is None and show_message:

        common.OKmsg(msg1 + "\n" + msg2)

    return iptvAddon


def RefreshIPTVlinks(channel_list):
    iptv_addon = GetIptvAddon()
    if iptv_addon is None:
        return False

    common.ShowNotification("Updating links...", 3000, addon=__Addon__)
    is_logo_extension = True
    final_m3_ulist = MakeM3U(channel_list, is_logo_extension)
    final_m3_ufilename = os.path.join(__AddonDataPath__, 'iptv.m3u')  # The final m3u file location.
    current_file = common.ReadFile(final_m3_ufilename)
    pvr_restart_required = False
    xbmc.log("update channel\n" + final_m3_ulist)

    if current_file is None or final_m3_ulist != current_file:
        common.WriteFile(final_m3_ulist, final_m3_ufilename)
        pvr_restart_required = True
    try:
        settings = {
            "logoPathType": "0",
            "logoPath": os.path.join(__AddonDataPath__, 'logos'),
            "m3uPathType": "0",
            "m3uPath": os.path.join(__AddonDataPath__, 'iptv.m3u'),
        }
        UpdateIPTVSimpleSettings(settings, iptv_addon, restart_pvr=pvr_restart_required)
    except Exception as e:
        print(e)
    common.ShowNotification("Updating is done.", 2000, addon=__Addon__)
    return True


def MakeM3U(channel, is_logo_extension):
    M3Ulist = []
    M3Ulist.append("#EXTM3U\n")
    for item in channel:
        tvg_logo = GetLogo(item.tvg_logo, is_logo_extension)
        M3Ulist.append(
            '#EXTINF:-1 tvg-id="{0}" tvg-name="{1}" group-title="{2}" tvg-logo="{3}",{4}\n{5}\n'.format(item.tvg_id,
                                                                                                        item.tvg_name, (
                                                                                                                    item.group_title or ""),
                                                                                                        tvg_logo,
                                                                                                        item.channel_name,
                                                                                                        item.url))
    return "\n".join(M3Ulist)


def DeleteCache():
    iptvsimple_path = __IPTVSimple__AddonDataPath____
    if (os.path.exists(iptvsimple_path)):
        for f in os.listdir(iptvsimple_path):
            if (os.path.isfile(os.path.join(iptvsimple_path, f))):
                if (f.endswith('cache')):
                    os.remove(os.path.join(iptvsimple_path, f))


def UpdateIPTVSimpleSettings(settings, iptv_addon=None, restart_pvr=False):
    xbmc.log("UpdateIPTVSettings")
    if iptv_addon is None:
        iptv_addon = GetIptvAddon()
        if iptv_addon is None:
            return

    iptv_settings_file = os.path.join(__IPTVSimple__AddonDataPath____, "settings.xml")
    if not os.path.isfile(iptv_settings_file):
        xbmc.log("Creating file {}".format(iptv_settings_file))
        iptv_addon.setSetting("epgPathType", "0")  # make 'settings.xml' in 'userdata/addon_data/pvr.iptvsimple' folder

    # get settings.xml into dictionary
    xbmc.log("Reading file {}".format(iptv_settings_file))
    settings_dictionary = ReadSettings(iptv_settings_file, True)
    xbmc.log("settings already read")

    is_settings_changed = False

    for k, v in settings.items():
        if k in settings_dictionary and settings_dictionary[k] != v:
            settings_dictionary[k] = v
            is_settings_changed = True
    if is_settings_changed:
        WriteSettings(settings_dictionary, iptv_settings_file)
    if restart_pvr:
        RefreshIPTVSimple()


def RefreshIPTVSimple():
    common.OKmsg("Please restart Kodi for changes to take place", title="Restart required")


def ReadSettings(source, fromFile=False):
    tree = ET.parse(source) if fromFile else ET.fromstring(source)
    elements = tree.findall('*')

    settingsDictionary = {}
    for elem in elements:
        settingsDictionary[elem.get('id')] = elem.get('value')

    xbmc.log("Settings read: \n{}".format(settingsDictionary))
    return settingsDictionary


def WriteSettings(settingsDictionary, iptvSettingsFile):
    xml = []
    xml.append("<settings>\n")
    for k, v in settingsDictionary.items():
        xml.append('\t<setting id="{0}" value="{1}" />\n'.format(k, v))
    xml.append("</settings>\n")
    settings_str = "".join(xml)
    xbmc.log("Writing iptv.simple settings:\n{}".format(settings_str))
    common.WriteFile(settings_str, iptvSettingsFile)


def MakeEPG(epg_list):
    current_tz_diff = common.GetTimezoneDifferenceMinutes()
    xml_list = []
    xml_list.append('<?xml version="1.0" encoding="utf-8" ?>')
    xml_list.append("<tv>")
    for epg in epg_list:
        for channel in epg.channels:
            xml_list.append('<channel id="%s">%s</channel>' % (channel.id, channel.display_name))

            for program in channel.programs:
                xml_list.append('<programme start="%s" stop="%s" channel="%s">' % (
                common.FormatEPGTime(program.start, current_tz_diff),
                common.FormatEPGTime(program.stop, current_tz_diff), channel.id))
                xml_list.append('<title>%s</title>' % program.title)

                if (program.subtitle is not None):
                    xml_list.append('<sub-title>%s</sub-title>' % program.subtitle)
                if (program.description is not None):
                    xml_list.append('<desc>%s</desc>' % program.description)
                if (program.category is not None):
                    xml_list.append('<category')
                    if (program.category_lang is not None):
                        xml_list.append(' lang="%s"' % program.category_lang)
                    xml_list.append('>%s</category>' % program.category)

                if ((program.credits is not None) and (len(program.credits) > 0)):
                    xml_list.append('<credits>')
                    for credit in program.credits:
                        job = credit.keys()[0]
                        name = credit.values()[0]
                        xml_list.append('<%s>%s</%s>' % (job, name, job))
                    xml_list.append('</credits>')

                if ((program.length is not None) and (program.length_units is not None)):
                    xml_list.append('<length units="%s">%s</length>' % (program.length_units, program.length))
                if (program.aspect_ratio is not None):
                    xml_list.append('<video><aspect>%s</aspect></video>' % program.aspect_ratio)
                if (program.star_rating is not None):
                    xml_list.append('<star-rating><value>%s</value></star-rating>' % program.star_rating)
                if (program.icon is not None):
                    xml_list.append('<icon src="%s" />' % program.icon)

                xml_list.append('</programme>')

    xml_list.append("</tv>")
    epg_xml = ''.join(xml_list)
    return epg_xml


def RefreshEPG(epg_list, is_very_new=False):
    if epg_list is not None and len(epg_list) > 0:
        epg_file = os.path.join(__AddonDataPath__, 'epg.xml')
        restart_pvr = (not os.path.exists(epg_file))
        epg_xml = MakeEPG(epg_list)
        common.WriteFile(epg_xml, epg_file)
        if restart_pvr:
            settings = {
                "epgPathType": "0",
                "epgPath": os.path.join(__AddonDataPath__, 'epg.xml'),
            }
            UpdateIPTVSimpleSettings(settings, restart_pvr=True)
        elif is_very_new:
            RefreshIPTVSimple()


def GetLogo(link, is_logo_extension):
    if ((link is not None) and (len(link) > 4)):
        filename = link.split("/")[-1]

        ext = None
        if (len(filename) > 4):
            ext = filename[-4:].lower()
        if ((ext is None) or (ext != ".png")):
            filename = filename + ".png"
            link = link + ".png"

        full_filename = os.path.join(__AddonDataPath__, 'logos', filename)
        file_exists = (os.path.exists(full_filename) or common.DownloadFile(link, full_filename))

        if (file_exists):
            if (is_logo_extension):
                return filename
            else:
                return filename[:-4]
        else:
            return ""
    else:
        return ""
