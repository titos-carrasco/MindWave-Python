#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rcr.mindwave.MindWave import *
from rcr.utils import Utils

def main():
    # colocar el headset unos 4 minutos antes para que se estabilice
    # el Global Headset Unique Identifier está en la zona de la batería
    mw = MindWave( "/dev/ttyUSB0", 1000, 0x00, 0x00 )
    if( mw.connect() ):
        mwd = MindWaveData()
        for i in range( 1000 ):
            mwd = mw.fillMindWaveData( mwd )
            print "Main [", i, "]:", mw.getGlobalHeadsetID(),
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

            # requerido para el scheduler
            Utils.pause( 10 )
        print i, "lecturas realizadas"
        mw.disconnect()


if( __name__ == "__main__" ):
    main()
