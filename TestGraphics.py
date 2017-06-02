#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt

from rcr.mindwave.MindWave import *
from rcr.utils import Utils


def main():
    plt.ion()
    attentionESense = []
    meditationESense = []
    delta = []
    theta = []

    npts = 30
    mw = MindWave( "/dev/ttyUSB0", 1000, 0x00, 0x00 )
    if( mw.connect() ):
        mwd = MindWaveData()
        while( True ):
            try:
                mwd = mw.fillMindWaveData( mwd )
                print mwd.poorSignalQuality, mwd.attentionESense, mwd.meditationESense, mwd.delta, mwd.theta
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
                print e
                break
        mw.disconnect()

        """
        while True: # While loop that loops forever
            dataArray = [ 0, 0 ]
            dataArray[0] = random.randint( 800, 900 ) / 10.0
            dataArray[1] = random.randint( 934500, 935250 ) / 10.0
            temp = float( dataArray[0])            #Convert first element to floating number and put in temp
            P =    float( dataArray[1])            #Convert second element to floating number and put in P
            tempF.append(temp)                     #Build our tempF array by appending temp readings
            pressure.append(P)                     #Building our pressure array by appending P readings
            drawnow(makeFig)                       #Call drawnow to update our live graph
            plt.pause(.000001)                     #Pause Briefly. Important to keep drawnow from crashing
            cnt=cnt+1
            if(cnt>50):                            #If you have 50 or more points, delete the first one from the array
                tempF.pop(0)                       #This allows us to just see the last 50 data points
                pressure.pop(0)
        """

if( __name__ == "__main__" ):
    main()
