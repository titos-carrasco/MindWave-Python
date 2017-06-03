#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import serial
import sys
import time

class MindWaveData:
    def __init__( self ):
        self.poorSignalQuality = 0           # byte      (0 <=> 200) 0=OK; 200=sensor sin contacto con la piel
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
        self.connected = False
        self.conn = None
        self.mutex = threading.Lock()
        self.mwd = MindWaveData()
        self.npacketsOk = 0
        self.npacketsErr = 0
        self.thread = None

    def connect( self ):
        if( self.connected ):
            print "MindWave Connect(): Ya se encuentra conectado a", self.port
            return True

        self.conn = None
        self.mwd = MindWaveData()
        self.npacketsOk = 0
        self.npacketsErr = 0
        self.thread = None

        print "MindWave Connect(): Intentando conectar a", self.port, " ...",
        sys.stdout.flush()
        try:
            conn = serial.Serial( self.port, baudrate=115200, bytesize=8,
                                  parity='N', stopbits=1, timeout=0 )
            conn.flushInput()
            conn.flushOutput()
        except Exception as e:
            print e
            return False
        print "OK"

        #resetea conexión anterior
        print "MindWave Connect(): Limpiando conexión previa ...",
        sys.stdout.flush()
        try:
            # request "Disconnect"
            conn.write( bytearray( [ 0xc1 ] ) )
            time.sleep( 1 )
            conn.flushInput()
        except Exception as e:
            conn.close()
            print e
            return False
        print "OK"

        # conecta con/sin Global Headset Unique Identifier (ghid)
        try:
            if( self.ghid != 0x0000 ):
                print "MindWave Connect(): Enlazando headset ",
                sys.stdout.flush()
                # request "Connect"
                conn.write( bytearray( [ 0xc0, ( self.ghid >> 8 ) & 0xFF, self.ghid & 0xFF ] ) )
                conn.flush()
            else:
                print "MindWave Connect(): Buscando headset ",
                sys.stdout.flush()
                # request "Auto-Connect"
                conn.write( bytearray( [ 0xc2 ] ) )
                conn.flush()
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
                    time.sleep( 0 )
            else:
                err = "ErrInvResponse"
                break

        if( err != None ):
            self.conn.close()
            self.conn = None
            print err
            return False
        print " OK"
        self.connected = True

        print "MindWave Connect(): Levantando tarea de lectura de datos"
        self._trunning = False
        self._thread = threading.Thread( target=self._TRead, args=(), name="TRead" )
        self._thread.start()
        while( not self._trunning ):
            time.sleep( 0.1 )
        return True

    def disconnect( self ):
        if( self.connected ):
            print "MindWave Disconnect(): Deteniendo Tarea ...",
            sys.stdout.flush()
            self._trunning = False
            self._thread.join()
            print "OK"

            # request "Disconnect"
            print "MindWave Disconnect(): Desconectando headset y cerrando puerta ...",
            sys.stdout.flush()
            try:
                self.conn.write( bytearray( [ 0xc1 ] ) )
                time.sleep( 1 )
                self.conn.close()
            except Exception as e:
                pass
            self.connected = False
            self.conn = None
            print "OK"
            print "Paquetes Buenos:", self.npacketsOk
            print "Paquetes Error :", self.npacketsErr

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
    def _TRead( self, *args ):
        self._trunning = True
        while self._trunning:
            #print "TRead"
            #sys.stdout.flush()

            # lee y procesa paquete recibido
            err = self._parsePayload()
            if( err != None ):
                #print "MindWave Task: ", err
                self.npacketsErr = self.npacketsErr + 1
            else:
                self.npacketsOk = self.npacketsOk + 1

            # requerido para el scheduler
            time.sleep( 0.00001 )

    def _parsePayload( self ):
        try:
            payload, err = self._getPayload()
            if( err != None ):
                return err
        except Exception as e:
            return e

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
                    print "ExCodeLevel: %02x, Code: %02x, Data: [%s]" % ( exCodeLevel, code, ''.join(format(x, '02X') for x in data) )
        self.mutex.release()
        return None

    def _readByte( self ):
        while( self.conn.in_waiting == 0 ):
            pass
        b = self.conn.read( 1 )
        if( type(b) is str ):
            b = ord(b)
        else:
            b = b[0]
        return b

    def _getPayload( self ):
        # 0xaa 0xaa [0xaa]*
        scanning = True
        while( scanning ):
            b = self._readByte()
            if( b == 0xaa ):
                b = self._readByte()
                if( b == 0xaa ):
                    while( scanning ):
                        plength = self._readByte()
                        if( plength != 0xaa ):
                            scanning = False

        # packet length
        if( plength <= 0 or plength >= 0xaa ):
            return None, "ErrInvPLength (%02X)" % plength

        # payload
        payload = bytearray( plength )
        for i in range( plength ):
            payload[i] = self._readByte()

        # checksum
        checksum = self._readByte()
        suma = 0
        for i in range( plength ):
            suma = suma + payload[i]
        suma = ( ~( suma & 0xff ) ) & 0xff
        if( checksum != suma ):
            return None, "ErrChecksum (%02X/%02X)" % (checksum, suma)

        # ok
        return payload, None
