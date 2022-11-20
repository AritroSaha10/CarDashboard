from threads.dbus_thread import DBusThread
import os, sys, logging

import dbus
from gi.repository import GLib

import threading

# Useful for getting album art
import requests
import json
import shutil

class PlaybackControlThread(DBusThread):
    _btObj = None # DBus bluetooth object
    _btMgr = None # DBus object manager

    playerInterface = None # DBus bluetooth media player interface
    transportPropInterface = None # DBus bluetooth media transport properties interface

    playbackStatus = None
    trackInfo = None

    propertyChangeExtraCallback = None # Extra function that'll be run in conjuction of normal callback, params should be `changed`

    def __init__(self, logLevel, propertyChangeExtraCallback = None):
        super().__init__("PlaybackControlThread", logLevel)

        # Initialize vars
        self.btObj = self.sysBus.get_object("org.bluez", "/")
        self.btMgr = dbus.Interface(self.btObj, "org.freedesktop.DBus.ObjectManager")
        self.propertyChangeExtraCallback = propertyChangeExtraCallback

        # TODO: Get playback status and track info immediately


        # Get bluetooth player and transport interfaces
        for path, interfaces in self.btMgr.GetManagedObjects().items():
            if "org.bluez.MediaPlayer1" in interfaces:
                # Get player interface
                self.playerInterface = dbus.Interface(
                    self.sysBus.get_object("org.bluez", path),
                    "org.bluez.MediaPlayer1"
                )
            elif dbus.String("org.bluez.MediaTransport1") in interfaces:
                self.transportPropInterface = dbus.Interface(
                    self.sysBus.get_object("org.bluez", path),
                    "org.freedesktop.DBus.Properties"
                )
        
        # Throw error if couldn't find
        if not self.playerInterface:
            self.logger.error(u"Unable to get the bluetooth player interface.")
            sys.exit(1)
        if not self.transportPropInterface:
            self.logger.error(u"Unable to get the bluetooth media transport properties.")
            sys.exit(1)

        # Attach reciever
        self.sysBus.add_signal_receiver(
            self.on_property_changed,
            bus_name="org.bluez",
            signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties"
        )

        super().runMainLoop()

    # Callback
    def on_property_changed(self, interface, changed, invalidated):
        if interface != "org.bluez.MediaPlayer1":
            # Not bluetooth device, doesn't matter
            return
        
        for prop, value in changed.items():
            if prop == "Status":
                self.logger.debug(f"Playback status: {value}")
                self.playbackStatus = value
            elif prop == "Track":
                self.logger.debug(f"Track info: ")
                for key in ["Title", "Artist", "Album"]:
                    self.logger.debug(f"\t{key}: {value.get(key, '')}")
                self.trackInfo = value

        if callable(self.propertyChangeExtraCallback):
            self.propertyChangeExtraCallback(self, changed) # Run extra callback with info

    # Playback functions, self-explanatory
    def play(self):
        self.playerInterface.Play()
    
    def pause(self):
        self.playerInterface.Pause()

    def nextTrack(self):
        self.playerInterface.Next()
    
    def prevTrack(self):
        self.playerInterface.Previous()
    
    def changeVol(self, newVol):
        if newVol not in range(0, 128):
            self.logger.info(f"New volume must be between 0 and 127, value of {newVol} was given. Ignoring...")
            return
        
        self.transportPropInterface.Set(
            "org.bluez.MediaTransport1",
            dbus.UInt16(newVol)
        )

    # Gets the album art to a song given track info, uses current track info
    def getAlbumArt(self) -> str:
        # Check first if user has internet connection, no point in doing all these if not
        url = "https://www.google.com"
        timeout = 5

        try:
            request = requests.get(url, timeout=timeout)
            self.logger.debug("Internet connection found, proceeding with finding album art")
        except (requests.ConnectionError, requests.Timeout) as exception:
            self.logger.warn("Can't get album art due to no internet connection, returning nothing...")
            return None

        # Check if track info is valid and has title, artist and album before getting album art
        # If this info isn't there, then we can't get the album art
        dataValid = True
        if type(self.trackInfo) == dbus.Dictionary:
            for key in ["Title", "Artist", "Album"]:
                if self.trackInfo.get(key, "") == "":
                    # Field is empty, data isn't valid
                    dataValid = False
                    break
        else:
            dataValid = False

        # Data not valid, don't bother
        if not dataValid:
            return None

        # Use Deezer API to get 1000x1000 album art, which should be high res enough
        likelyAlbumArtLink = ""
        try:
            albumArtReq = requests.get(
                f"http://api.deezer.com/search/album/?q={self.trackInfo['Album']}&index=0&limit=20&output=json",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36"
                }
            )

            if albumArtReq.status_code == 200:
                # Got the data, start extracting from JSON
                parsed = json.loads(albumArtReq.content)
                
                # Go through all of them and check if the artist is the same
                for album in parsed["data"]:
                    if album["artist"]["name"] == self.trackInfo["Artist"]:
                        likelyAlbumArtLink = album["cover_xl"]

                # likelyAlbumArtLink = parsed["data"][0]["cover_xl"]
            else:
                self.logger.warn("Couldn't fetch website for album art")
                return

        except Exception as e:
            self.logger.error("Error when fetching album art: " + str(e))
            return

        if likelyAlbumArtLink == "":
            # Couldn't find it, return nothing
            return None
        
        # Sanitize album name and put into normal fname template
        fname = ''.join(e for e in self.trackInfo['Album'] if e.isalnum() or e == " ")
        fname = fname.replace(' ', '-')
        fname = f"albumArtImgs/{fname}.jpg"

        # Check if it already exists, if it does then we don't need to download
        if not os.path.exists(fname):
            # Link has been fetched, we can download now
            albumArtImg = requests.get(likelyAlbumArtLink, stream=True)
            # Commented out because we'll be using a read-only FS
            # with open(fname, 'wb') as f:
            #     shutil.copyfileobj(albumArtImg.raw, f)
            del albumArtImg

        # Filename of img
        return fname
