#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
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
            print(  mw.getGlobalHeadsetID(),
                    mwd.poorSignalQuality,
                    mwd.attentionESense,
                    mwd.meditationESense,
                    mwd.blinkStrength,
                    mwd.rawWave16Bit,
                    mwd.delta,
                    mwd.theta,
                    mwd.lowAlpha,
                    mwd.highAlpha,
                    mwd.lowBeta,
                    mwd.highBeta,
                    mwd.lowGamma,
                    mwd.midGamma
            )
            time.sleep( 0.0001 )
        mw.disconnect()


if( __name__ == "__main__" ):
    main()
