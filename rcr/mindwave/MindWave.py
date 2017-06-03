#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import threading
import serial
import time

class MindWaveData:
    def __init__( self ):
        self.poorSignalQuality = 200         # byte      (0 <=> 200) 0=OK; 200=sensor sin contacto con la piel
        self.attentionESense = 0             # byte      (1 <=> 100) 0=no confiable
        self.meditationESense = 0            # byte      (1 <=> 100) 0=no confiable
        self.blinkStrength = 0               # byte      (1 <=> 255)
        self.rawWave16Bit = 0                # int16     (-32768 <=> 32767)
        self.delta = 0                       # uint32    (0 <=> 16777215)
        self.theta = 0                       # uint32    (0 <=> 16777215)
        self.lowAlpha = 0                    # uint32    (0 <=> 16777215)
        self.highAlpha = 0                   # uint32    (0 <=> 16777215)
        self.lowBeta = 0                     # uint32    (0 <=> 16777215)
        self.highBeta = 0                    # uint32    (0 <=> 16777215)
        self.lowGamma = 0                    # uint32    (0 <=> 16777215)
        self.midGamma = 0                    # uint32    (0 <=> 16777215)

class MindWave():
    def __init__( self, port, timeout, ghid ):
        self.port = port
        self.timeout = timeout
        self.ghid = ghid
        self.mutex = threading.Lock()
        self.connected = False
        self.mwd = MindWaveData()
        self.conn = None
        self.tRunning = False
        self.tParser = None
        self.queue = None
        self.bytesLeidos = 0
        self.bytesPerdidos = 0

    def connect( self ):
        if( self.connected ):
            print( "MindWave Connect(): Ya se encuentra conectado a", self.port )
            return True

        self.mwd = MindWaveData()
        self.conn = None
        self.tRunning = False
        self.tParser = None
        self.queue = bytearray()
        self.bytesLeidos = 0
        self.bytesPerdidos = 0

        print( "MindWave Connect(): Intentando conectar a", self.port, " ...", end='' )
        try:
            self.conn = serial.Serial( self.port, baudrate=115200, bytesize=8,
                                       parity='N', stopbits=1, timeout=0.1 )
            self.conn.flushInput()
            self.conn.flushOutput()
            self.connected = True
        except Exception as e:
            self.conn = None
            print( e )
            return False
        print( "OK" )

        #resetea conexión anterior
        print( "MindWave Connect(): Limpiando conexión previa ...", end='' )
        try:
            # request "Disconnect"
            self.conn.write( bytearray( [ 0xc1 ] ) )
            time.sleep( 1 )
            self.conn.flushInput()
        except Exception as e:
            self.conn.close()
            self.conn = None
            self.connected = False
            print( e )
            return False
        print( "OK" )

        # conecta al headset
        try:
            # especifica un Global Headset Unique Identifier (ghid)
            if( self.ghid != 0x0000 ):
                print( "MindWave Connect(): Enlazando headset ", end='' )
                # request "Connect"
                self.conn.write( bytearray( [ 0xc0, ( self.ghid >> 8 ) & 0xFF, self.ghid & 0xFF ] ) )
                self.conn.flush()
            # busca un Global Headset Unique Identifier (ghid)
            else:
                print( "MindWave Connect(): Buscando headset ", end='' )
                # request "Auto-Connect"
                self.conn.write( bytearray( [ 0xc2 ] ) )
                self.conn.flush()
        except Exception as e:
            self.conn.close()
            self.conn = None
            self.connected = False
            print( e )
            return False

        # esperamos la respuesta del dongle
        while True:
            print( ".", end = '' )

            # lee respuesta
            payload, err = self._getPayload()
            if( err != None ):
                break

            # analiza respuesta
            cmd = payload[0]
            if( cmd == 0xd0 ):                  # headset found and connected
                self.ghid = ( payload[2] << 8 ) + payload[3]
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
                    time.sleep( 0.0001 )
            else:
                err = "ErrInvResponse"
                break

        if( err != None ):
            self.conn.close()
            self.conn = None
            self.connected = False
            print( err )
            return False
        print( "OK" )

        # levantamos la tarea de apoyo
        print( "MindWave Connect(): Levantando tarea de lectura de datos ...", end='' )
        self.tParser = threading.Thread( target=self._TParser, args=(), name="_TParser" )
        self.tParser.start()
        while ( not self.tRunning ):
            time.sleep( 0.0001 )
        print( "OK" )

        return True

    def disconnect( self ):
        if( self.connected ):
            print( "MindWave Disconnect(): Deteniendo Tarea ...", end='' )
            self.tRunning = False
            self.tParser.join()
            self.tParser = None
            self.queue = bytearray()
            print( "OK" )

            # request "Disconnect"
            print( "MindWave Disconnect(): Desconectando headset y cerrando puerta ...", end='' )
            try:
                self.conn.write( bytearray( [ 0xc1 ] ) )
                time.sleep( 1 )
                self.conn.close()
            except Exception as e:
                pass
            self.connected = False
            self.conn = None

            print( "OK" )
            print( "Bytes Leidos   :", self.bytesLeidos )
            print( "Bytes Perdidos :", self.bytesPerdidos )
            print( threading.enumerate() )

    def isConnected( self ):
        return self.connected

    def getGlobalHeadsetID( self ):
        return "%04X" % self.ghid

    def fillMindWaveData( self, mwd ):
        self.mutex.acquire()
        mwd.poorSignalQuality = self.mwd.poorSignalQuality
        mwd.attentionESense = self.mwd.attentionESense
        mwd.meditationESense = self.mwd.meditationESense
        mwd.blinkStrength = self.mwd.blinkStrength
        mwd.rawWave16Bit = self.mwd.rawWave16Bit
        mwd.delta = self.mwd.delta
        mwd.theta = self.mwd.theta
        mwd.lowAlpha = self.mwd.lowAlpha
        mwd.highAlpha = self.mwd.highAlpha
        mwd.lowBeta = self.mwd.lowBeta
        mwd.highBeta = self.mwd.highBeta
        mwd.lowGamma = self.mwd.lowGamma
        mwd.midGamma = self.mwd.midGamma
        self.mutex.release()

    # privadas
    def _getByte( self ):
        while( True ):
            if( self.conn.in_waiting > 0 ):
                data = self.conn.read( self.conn.in_waiting )
                if( type( data ) == str ):
                    self.queue = self.queue + bytearray( data )
                else:
                    self.queue = self.queue + data
                self.bytesLeidos = self.bytesLeidos + len( data )
            if( len( self.queue ) > 0 ):
                return self.queue.pop( 0 )
            time.sleep( 0.0001 )

    def _getPayload( self ):
        # 0xaa 0xaa [0xaa]*
        scanning = True
        while( scanning ):
            b = self._getByte()
            if( b == 0xaa ):
                b = self._getByte()
                if( b == 0xaa ):
                    while( scanning ):
                        plength = self._getByte()
                        if( plength != 0xaa ):
                            scanning = False
                        else:
                            self.bytesPerdidos = self.bytesPerdidos + 1
                else:
                    self.bytesPerdidos = self.bytesPerdidos + 2
            else:
                self.bytesPerdidos = self.bytesPerdidos + 1

        # packet length
        if( plength <= 0 or plength >= 0xaa ):
            self.bytesPerdidos = self.bytesPerdidos + 1
            return None, "ErrInvPLength (%02X)" % plength

        # payload
        payload = bytearray( plength )
        for i in range( plength ):
            payload[i] = self._getByte()

        # checksum
        checksum = self._getByte()
        suma = 0
        for i in range( plength ):
            suma = suma + payload[i]
        suma = ( ~( suma & 0xff ) ) & 0xff
        if( checksum != suma ):
            self.bytesPerdidos = self.bytesPerdidos + 1 + plength + 1
            return None, "ErrChecksum (%02X/%02X)" % (checksum, suma)

        # ok
        return payload, None

    def _TParser( self, *args ):
        self.bytesLeidos = 0
        self.bytesPerdidos = 0
        self.queue = bytearray()
        self.conn.flushInput()
        self.tRunning = True
        while( self.tRunning ):
            err = self._parsePayload()
            if( err != None ):
                print( "TParser: ", err )

    def _parsePayload( self ):
        payload, err = self._getPayload()
        if( err != None ):
            return err

        if( payload[0] == 0xd2 ):       # disconnected
            return "ErrDisconnected"

        if( payload[0] == 0xd4 ):       # alive message in stand by mode
            return None

        pos = 0
        self.mutex.acquire()
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
                    self.mwd.poorSignalQuality = data[0]
                elif( code == 0x04 ):  # attention eSense (0 to 100) 40-60 => neutral, 0 => result is unreliable
                    self.mwd.attentionESense = data[0]
                elif( code == 0x05 ):  # meditation eSense (0 to 100) 40-60 => neutral, 0 => result is unreliable
                    self.mwd.meditationESense = data[0]
                elif( code == 0x16 ):  # blink strength (1 to 255)
                    self.mwd.blinkStrength = data[0]
                elif( code == 0x80 ):  # raw wave value (-32768 to 32767) - big endian
                    n = ( data[0]<<8 ) + data[1]
                    if( n >= 32768 ):
                        n = n - 65536
                    self.mwd.rawWave16Bit = n
                elif( code == 0x83 ):  # asic eeg power struct (8, 3 bytes unsigned int big indian)
                    self.mwd.delta     = ( data[0]<<16 ) + ( data[1]<<8 ) + data[2]
                    self.mwd.theta     = ( data[3]<<16 ) + ( data[4]<<8 ) + data[5]
                    self.mwd.lowAlpha  = ( data[6]<<16 ) + ( data[7]<<8 ) + data[8]
                    self.mwd.highAlpha = ( data[9]<<16 ) + ( data[10]<<8 ) + data[11]
                    self.mwd.lowBeta   = ( data[12]<<16 ) + ( data[13]<<8 ) + data[14]
                    self.mwd.highBeta  = ( data[15]<<16 ) + ( data[16]<<8 ) + data[17]
                    self.mwd.lowGamma  = ( data[18]<<16 ) + ( data[19]<<8 ) + data[20]
                    self.mwd.midGamma  = ( data[21]<<16 ) + ( data[22]<<8 ) + data[23]
                # elif( code == 0x01 ):  # code battery - battery low (0x00)
                # elif( code == 0x03 ):  # heart rate (0 to 255)
                # elif( code == 0x06 ):  # 8bit raw wave value (0 to 255)
                # elif( code == 0x07 ):  # raw marker section start (0)
                # elif( code == 0x81 ):  # eeg power struct (legacy float)
                # elif( code == 0x86 ):  # rrinterval (0 to 65535)
                else:
                    print( "ExCodeLevel: %02x, Code: %02x, Data: [%s]" % ( exCodeLevel, code, ''.join(format(x, '02X') for x in data) ) )
        self.mutex.release()
        return None
