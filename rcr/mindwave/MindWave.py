#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import serial
import sys

from rcr.utils.Serial import Serial
from rcr.utils import Utils

class MindWaveData:
    poorSignalQuality = 0           # byte      (0 <=> 200) 0=OK; 200=sensor sin contacto con la piel
    attentionESense = 0             # byte      (1 <=> 100) 0=no confiable
    meditationESense = 0            # byte      (1 <=> 100) 0=no confiable
    blinkStrength = 0               # byte      (1 <=> 255)
    rawWave16Bit = 0                # int16     (-32768 <=> 32767)
    delta = 0                       # uint32    (0 <=> 16777215)
    theta = 0                       # uint32    (0 <=> 16777215)
    lowAlpha = 0                    # uint32    (0 <=> 16777215)
    highAlpha = 0                   # uint32    (0 <=> 16777215)
    lowBeta = 0                     # uint32    (0 <=> 16777215)
    highBeta = 0                    # uint32    (0 <=> 16777215)
    lowGamma = 0                    # uint32    (0 <=> 16777215)
    midGamma = 0                    # uint32    (0 <=> 16777215)

class MindWave():
    def __init__( self, port, timeout, ghid_high, ghid_low ):
        self.port = port
        self.timeout = timeout
        self.ghid_high = ghid_high
        self.ghid_low = ghid_low
        self.connected = False
        self.conn = None
        self.mutex = threading.Lock()
        self.poorSignalQuality = 0           # byte      (0 <=> 200) 0=OK; 200=sensor sin contacto con la piel
        self.attentionESense = 0             # byte      (1 <=> 100) 0=no confiable
        self.meditationESense = 0            # byte      (1 <=> 100) 0=no confiable
        self.blinkStrength = 0               # byte      (1 <=> 255)
        self.rawWave16Bit = 0                # int16     (-32768 <=> 32767)
        self.delta = 0                       # uint24    (0 <=> 16777215)
        self.theta = 0                       # uint24    (0 <=> 16777215)
        self.lowAlpha = 0                    # uint24    (0 <=> 16777215)
        self.highAlpha = 0                   # uint24    (0 <=> 16777215)
        self.lowBeta = 0                     # uint24    (0 <=> 16777215)
        self.highBeta = 0                    # uint24    (0 <=> 16777215)
        self.lowGamma = 0                    # uint24    (0 <=> 16777215)
        self.midGamma = 0                    # uint24    (0 <=> 16777215)

    def connect( self ):
        if( self.connected ):
            print "MindWave Connect(): Ya se encuentra conectado a ", self.port
            return True

        print "MindWave Connect(): Intentando conectar a ", self.port, " =>",
        sys.stdout.flush()
        try:
            conn = Serial( self.port, 115200, self.timeout )
        except Exception as e:
            print e
            return False
        print "OK"

        #resetea conexión anterior
        print "MindWave Connect(): Limpiando conexión previa =>",
        sys.stdout.flush()
        try:
            # request "Disconnect"
            conn.write( bytearray( [ 0xc1 ] ) )
        except Exception as e:
            conn.close()
            print e
            return False
        conn.flushRead( 1000 )
        print "OK"

        # conecta con/sin Global Headset Unique Identifier (ghid)
        try:
            if( self.ghid_high != 0  or self.ghid_low != 0):
                print "MindWave Connect(): Enlazando headset =>",
                sys.stdout.flush()
                # request "Connect"
                conn.write( bytearray( [ 0xc0, self.ghid_high, self.ghid_low ] ) )
            else:
                print "MindWave Connect(): Buscando headset =>",
                sys.stdout.flush()
                # request "Auto-Connect"
                conn.write( bytearray( [ 0xc2 ] ) )
        except Exception as e:
            conn.close()
            print e
            return False

        # esperamos la respuesta del dongle
        self.conn = conn
        while True:
            sys.stdout.write( "." )
            sys.stdout.flush()

            # lee respuesta
            payload, err = self.parsePacket()
            if( err != None ):
                if( err == "ErrChecksum" ):     # se deben ignorar los errores de checksum
                    continue
                break

            # analiza respuesta
            cmd = payload[0]
            if( cmd == 0xd0 ):                  # headset found and connected
                self.ghid_high = payload[2]
                self.ghid_low = payload[3]
                break
            if( cmd == 0xd1 ):                  # headset not found
                if( payload[1] == 0x00 ):
                    err = "ErrNoHeadsetFound"
                else:
                    err = "ErrHeadsetNotFound"
                break
            if( cmd == 0xd2 ):                  # headset disconnected
                err = "ErrDisconnected"
                break
            if( cmd == 0xd3 ):                  # request denied
                err = "ErrRequestDenied"
                break
            if( cmd == 0xd4 ):
                if( payload[2] == 0x00 ):       # dongle in stand by mode
                    break
                else:                           # searching
                    Utils.pause( 1 )
            else:
                break

        if( err != None ):
            self.conn.close()
            self.conn = None
            print err
            return False
        print "OK"
        self.connected = True

        print "MindWave Connect(): Levantando tarea de lectura de datos"
        self._trunning = False
        self._tread = threading.Thread( target=self._TRead, args=(), name="TRead" )
        self._tread.start()
        while( not self._trunning ):
            Utils.pause( 10 )
        return True

    def _TRead( self, *args ):
        self._trunning = True
        while self._trunning:
            #print "TRead"
            #sys.stdout.flush()

            # lee y procesa paquete recibido
            err = self.parsePayload()
            if( err != None ):
                print "MindWave: ", err

            # requerido para el scheduler
            Utils.pause( 10 )

    def disconnect( self ):
        if( self.connected ):
            print "MindWave Disconnect(): Deteniendo Tarea =>",
            sys.stdout.flush()
            self._trunning = False
            self._tread.join()
            print "OK"

            # request "Disconnect"
            print "MindWave Disconnect(): Desconectando headset y cerrando puerta =>",
            sys.stdout.flush()
            self.conn.write( bytearray( [ 0xc1 ] ) )
            self.conn.flushRead( 1000 )
            self.conn.close()
            self.connected = False
            self.conn = None
            print "OK"

    def isConnected( self ):
        return self.connected

    def getGlobalHeadsetID( self ):
        return "%02X%02X" % ( self.ghid_high, self.ghid_low )

    def getMindWaveData( self ):
        self.mutex.acquire()
        mwd = MindWaveData()
        mwd.poorSignalQuality = self.poorSignalQuality
        mwd.attentionESense = self.attentionESense
        mwd.meditationESense = self.meditationESense
        mwd.blinkStrength = self.blinkStrength
        mwd.rawWave16Bit = self.rawWave16Bit
        mwd.delta = self.delta
        mwd.theta = self.theta
        mwd.lowAlpha = self.lowAlpha
        mwd.highAlpha = self.highAlpha
        mwd.lowBeta = self.lowBeta
        mwd.highBeta = self.highBeta
        mwd.lowGamma = self.lowGamma
        mwd.midGamma = self.midGamma
        self.mutex.release()
        return mwd

    def parsePacket( self ):
        inHeader = True
        plength = 0

        while inHeader:
            try:
                b = self.conn.read( 1 )
                if( b[0] == 0xaa ):
                    b = self.conn.read( 1 )
                    if( b[0] == 0xaa ):
                        while True:
                            b = self.conn.read( 1 )
                            plength = b[0]
                            if( plength > 0xaa ):
                                break
                            if( plength < 0xaa ):
                                inHeader = False
                                break
            except Exception as e:
                return None, "ErrRead"

        if( plength <= 0 ):
            return None, "ErrZeroPlength"

        try:
            payload = self.conn.read( plength )
            b = self.conn.read( 1 )
        except Exception as e:
            return None, "ErrRead"
        checksum = b[0]
        suma = 0
        for i in range( plength ):
            suma = suma + payload[i]
        suma = ( ~( suma & 0xff ) ) & 0xff
        if( checksum != suma ):
            return None, "ErrChecksum"
        else:
            return payload, None

    def parsePayload( self ):
        payload, err = self.parsePacket()
        if( err!= None ):
            return err

        if( payload[0] == 0xd2 ):       # disconnected
            return "ErrDisconnected"

        if( payload[0] == 0xd4 ):       # alive message in stand by mode
            return None


        self.mutex.acquire()
        pos = 0
        while pos < len( payload ):
            exCodeLevel = 0
            while( payload[pos] == 0x55 ):
                exCodeLevel = exCodeLevel + 1
                pos = pos + 1
            code = payload[pos]
            pos = pos + 1
            if( code >= 0x80 ):
                vlength = payload[pos]
                pos = pos + 1
            else:
                vlength = 1

            data = bytearray( vlength )
            for i in range( vlength ):
                data[i] = payload[pos + i]
            pos = pos + vlength

            if( exCodeLevel == 0 ):
                if( code == 0x02 ):    # poor signal quality (0 to 255) 0=>OK; 200 => no skin contact
                        self.poorSignalQuality = data[0]
                elif( code == 0x04 ):  # attention eSense (0 to 100) 40-60 => neutral, 0 => result is unreliable
                        self.attentionESense = data[0]
                elif( code == 0x05 ):  # meditation eSense (0 to 100) 40-60 => neutral, 0 => result is unreliable
                        self.meditationESense = data[0]
                elif( code == 0x16 ):  # blink strength (1 to 255)
                        self.blinkStrength = data[0]
                elif( code == 0x80 ):  # raw wave value (-32768 to 32767) - big endian
                        n = ( data[0]<<8 ) + data[1]
                        if( n >= 32768 ):
                            n = n - 65536
                        self.rawWave16Bit = n
                elif( code == 0x83 ):  # asic eeg power struct (8, 3 bytes unsigned int big indian)
                        self.delta     = ( data[0]<<16 ) + ( data[1]<<8 ) + data[2]
                        self.theta     = ( data[3]<<16 ) + ( data[4]<<8 ) + data[5]
                        self.lowAlpha  = ( data[6]<<16 ) + ( data[7]<<8 ) + data[8]
                        self.highAlpha = ( data[9]<<16 ) + ( data[10]<<8 ) + data[11]
                        self.lowBeta   = ( data[12]<<16 ) + ( data[13]<<8 ) + data[14]
                        self.highBeta  = ( data[15]<<16 ) + ( data[16]<<8 ) + data[17]
                        self.lowGamma  = ( data[18]<<16 ) + ( data[19]<<8 ) + data[20]
                        self.midGamma  = ( data[21]<<16 ) + ( data[22]<<8 ) + data[23]
                # elif( code == 0x01 ):  # code battery - battery low (0x00)
                # elif( code == 0x03 ):  # heart rate (0 to 255)
                # elif( code == 0x06 ):  # 8bit raw wave value (0 to 255)
                # elif( code == 0x07 ):  # raw marker section start (0)
                # elif( code == 0x81 ):  # eeg power struct (legacy float)
                # elif( code == 0x86 ):  # rrinterval (0 to 65535)
                else:
                    print "ExCodeLevel: %02x, Code: %02x, Data: [%s]\n" % ( exCodeLevel, code, ''.join(format(x, '02X') for x in data) )
        self.mutex.release()
        return None
