#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import numpy as np
import matplotlib.pyplot as plt
import time

from rcr.mindwave.MindWave import *

def main():
    plt.ion()
    attentionESense = []
    meditationESense = []
    delta = []
    theta = []

    npts = 30
    mw = MindWave( "/dev/ttyUSB0", 1000, 0x0000 )
    if( mw.connect() ):
        mwd = MindWaveData()
        while( True ):
            try:
                mw.fillMindWaveData( mwd )
                print( mwd.poorSignalQuality, mwd.attentionESense, mwd.meditationESense, mwd.delta, mwd.theta )
                attentionESense.append( mwd.attentionESense );
                meditationESense.append( mwd.meditationESense );
                delta.append( mwd.delta )
                theta.append( mwd.theta )

                plt.figure( 1 )
                plt.clf()
                plt.title( "MindWave Headset" )
                plt.grid( True )
                plt.ylim( 0, 100 )
                plt.plot( attentionESense, "ro-", label="attentionESense" )
                plt.plot( meditationESense, "b^-", label="meditationESense" )
                plt.legend( loc="upper left" )
                plt.text( 0, 10, "Signal Quality: %d" % mwd.poorSignalQuality )

                plt.figure( 2 )
                plt.clf()
                plt.title( "MindWave Headset" )
                plt.grid( True )
                #plt.ylim( 0, 16777215 )
                plt.plot( delta, "ro-", label="delta" )
                plt.plot( theta, "g^-", label="theta" )
                plt.legend( loc="upper left" )

                plt.draw_all()
                plt.pause( 0.0001 )

                if( npts > 0 ):
                    npts = npts - 1
                else:
                    attentionESense.pop( 0 )
                    meditationESense.pop( 0 )
                    delta.pop( 0 )
                    theta.pop( 0 )
            except Exception as e:
                print( e )
                break
        mw.disconnect()

if( __name__ == "__main__" ):
    main()
