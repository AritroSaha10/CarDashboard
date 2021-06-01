# Runs all threads

from threads.volume_control import VolumeControlThread
from threads.playback_control import PlaybackControlThread
from threads.call_handler import VoiceCallHandlerThread
from threads.bluetooth_control import BluetoothControlThread
from time import sleep
import logging

GLOBAL_LOGGING_LEVEL = logging.DEBUG

def playbackPropertyChangeCallback(pct, changed):
    for prop, value in changed.items():
        if prop == "Status":
            # Update status on screen
            continue
        elif prop == "Track":
            # Update track on screen
            print(pct.getAlbumArt())
            continue

if __name__ == "__main__":
    def runAfterConnection():
        vct = VolumeControlThread(GLOBAL_LOGGING_LEVEL)
        pct = PlaybackControlThread(GLOBAL_LOGGING_LEVEL, playbackPropertyChangeCallback)
        vcht = VoiceCallHandlerThread(GLOBAL_LOGGING_LEVEL)

    bct = BluetoothControlThread(GLOBAL_LOGGING_LEVEL, runAfterConnection)

    """
    sleep(20)
    pct.play()
    sleep(2)
    pct.pause()
    sleep(2)
    # pct.nextTrack()
    """
    
    input("Press return to exit...")

