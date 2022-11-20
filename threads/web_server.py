# This technically does not use DBus, but is still very useful
from threads.dbus_thread import DBusThread
import os, sys, logging
from flask import Flask
from json import dumps

playbackData = {}

class WebServerThread(DBusThread):
    flaskApp = Flask(__name__)

    def __init__(self, logLevel):
        super().__init__("WebServerThread", logLevel) # Initializes DBus and logging

        # Start main loop
        super().runMainLoop()
        
    def run(self):
        self.flaskApp.run(debug=False, use_reloader=False, host="0.0.0.0")

    def update_data(self, trackInfo, playbackStatus, albumArtImgLink):
        playbackData["status"] = playbackStatus
        playbackData["track"] = trackInfo
        
        if albumArtImgLink != "":
            playbackData["albumArtImg"] = albumArtImgLink
        else:
            playbackData["albumArtImg"] = "/home/pi/carDashboard/albumArtImgs/placeholder.png"

    @flaskApp.route("/")
    def indexPage():
        return dumps(playbackData)


