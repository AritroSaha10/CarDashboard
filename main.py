# Runs all threads

from threads.volume_control import VolumeControlThread
from threads.playback_control import PlaybackControlThread
from threads.call_handler import VoiceCallHandlerThread
from time import sleep

if __name__ == "__main__":
    vct = VolumeControlThread()
    pct = PlaybackControlThread()
    vcht = VoiceCallHandlerThread()

    sleep(20)
    pct.play()
    sleep(2)
    pct.pause()
    sleep(2)
    pct.nextTrack()
    
    input("Press return to exit...")

