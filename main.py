# Runs all threads

from threads.volume_control import VolumeControlThread
from threads.playback_control import PlaybackControlThread
from threads.call_handler import VoiceCallHandlerThread
from threads.bluetooth_control import BluetoothControlThread
from threads.web_server import WebServerThread

from time import sleep
import logging, atexit

GLOBAL_LOGGING_LEVEL = logging.DEBUG

# Threads
threads = {}

def exitHandler():
    # Disconnect all connected devices
    for device in threads["bct"].get_all_connected():
        print(device["obj"])
        device["obj"].Disconnect()
    
    print("Exiting application...")

def playbackPropertyChangeCallback(pct, changed):
    albumArtImgLink = ""

    for prop, value in changed.items():
        if prop == "Status":
            # Update status on screen
            continue
        elif prop == "Track":
            # Update track on screen
            albumArtImgLink = pct.getAlbumArt()
            continue

    # Update web server thread with information
    threads["wst"].update_data(pct.trackInfo, pct.playbackStatus, albumArtImgLink)

if __name__ == "__main__":
    # Register exit handler
    atexit.register(exitHandler)

    threads["wst"] = WebServerThread(GLOBAL_LOGGING_LEVEL)
    
    # Start bluetooth thread and wait for connection
    threads["bct"] = BluetoothControlThread(GLOBAL_LOGGING_LEVEL)
    threads["bct"].wait_for_connection()

    # Wait before starting other threads
    sleep(1.5)

    # Start other threads
    threads["vct"] = VolumeControlThread(GLOBAL_LOGGING_LEVEL)
    threads["pct"] = PlaybackControlThread(GLOBAL_LOGGING_LEVEL, playbackPropertyChangeCallback)
    # threads["vcht"] = VoiceCallHandlerThread(GLOBAL_LOGGING_LEVEL)

    threads["wst"].run()
    
    """
    sleep(20)
    pct.play()
    sleep(2)
    pct.pause()
    sleep(2)
    # pct.nextTrack()
    """
    
    input("Press return to exit...")

