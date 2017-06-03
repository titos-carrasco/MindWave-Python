#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from rcr.mindwave.MindWave import *

def main():
    # colocar el headset unos 4 minutos antes para que se estabilice
    # el Global Headset Unique Identifier está en la zona de la batería
    mw = MindWave( "/dev/ttyUSB0", 1000, 0x0000 )
    if( mw.connect() ):
        mwd = MindWaveData()
        t = time.time()
        while( time.time() -t < 10 ):
            mw.fillMindWaveData( mwd )
            print mw.getGlobalHeadsetID(),
            print mwd.poorSignalQuality,
            print mwd.attentionESense,
            print mwd.meditationESense,
            print mwd.blinkStrength,
            print mwd.rawWave16Bit,
            print mwd.delta,
            print mwd.theta,
            print mwd.lowAlpha,
            print mwd.highAlpha,
            print mwd.lowBeta,
            print mwd.highBeta,
            print mwd.lowGamma,
            print mwd.midGamma
            time.sleep( 0.0001 )
        mw.disconnect()


if( __name__ == "__main__" ):
    main()
