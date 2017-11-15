import machine
import time
import utime
import pycom
import socket
from network import Sigfox
from network import Bluetooth
import struct

from micropyGPS import MicropyGPS
import bme280

# Initialize GPS
com = machine.UART(1, pins=("P3", "P4"), baudrate=9600)
my_gps = MicropyGPS()
chrono = machine.Timer.Chrono() #also alarm for sigfox, and start/reset
rtc = machine.RTC()
rtc.init((2017, 1, 1, 00, 00, 00, 0, 0))
print("GPS ok")
#chrono.start()

i2c = machine.I2C(0, machine.I2C.MASTER, pins=("G9", "G10"))
print(i2c.scan())
bme = bme280.BME280(i2c=i2c)
print("BME280 ok")

def send_sigfox_msg(tx_nbr, gps_lat, gps_lng, bme_temp, bme_humi, bme_pres):
    #pycom.rgbled(0x7f0000) # red
    #chrono.start()
    sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ1)
    s = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)
    s.setblocking(True)

    s.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False)# uplink only
    ba = bytearray(struct.pack("f", gps_lat))
    ba = bytearray(struct.pack("f", gps_lng))
    ba = bytearray(struct.pack("f", bme_temp))
    ba = bytearray(struct.pack("f", bme_humi))
    ba = bytearray(struct.pack("f", bme_pres))
    print(ba)
    #print(bytes([tx_nbr, 0, 0, tx_nbr]))
    #s.send(ba)
    #s.send(bytes([tx_nbr, 0, 0, tx_nbr]))

    '''chrono.stop()
    total = chrono.read()
    print("Sigfox Message Sent in %f" % total)

    pycom.rgbled(0x007f00) # green
    utime.sleep_ms(500)
    pycom.rgbled(0x000000) # off'''

class Keytrack:
    def __init__(self):
        self.state=0
        self.bme_temp=0
        self.bme_humi=0
        self.bme_pres=0
        self.gps_lat=0
        self.gps_lng=0
        self.sigfox_tx_nbr = 0
        #send_sigfox_msg(0)
        #self.__alarm =
        #machine.Timer.Alarm(self._sigfox_handler, 30, periodic=True)
        #machine.Timer.Alarm(self.refresh_bme, 4, periodic=True)
        #machine.Timer.Alarm(self.refresh_gps, 2, periodic=True)

    def _sigfox_handler(self, alarm):
        self.sigfox_tx_nbr += 1
        send_sigfox_msg(self.sigfox_tx_nbr, self.gps_lat, self.gps_lng, self.bme_temp, self.bme_humi, self.bme_pres)

        print("%02d messages have been sent" % self.sigfox_tx_nbr)
        if self.sigfox_tx_nbr == 40:
            print("end of messages")
            alarm.cancel() # stop counting after 10 seconds

    def refresh_bme(self, alarm):
        #print(bme.temperature, bme.pressure, bme.humidity)
        self.bme_temp = bme.read_temperature() / 100
        self.bme_humi = bme.read_humidity() / 1024
        self.bme_pres = bme.read_pressure() / 25600
        print(self.bme_temp, self.bme_humi, self.bme_pres)

    def refresh_gps(self, alarm):
        pycom.rgbled(0x7f7f00) # yellow
        my_sentence = com.readline()
        for x in my_sentence:
            my_gps.update(chr(x))
        #gps_array = tools.convert_latlon(my_gps.latitude[0] + (my_gps.latitude[1] / 60), my_gps.longitude[0] + (my_gps.longitude[1] / 60))
        #print(gps_array)
        #print("GPS data")
        self.gps_lat = my_gps.latitude[0] + (my_gps.latitude[1] / 60)
        self.gps_lng = my_gps.longitude[0] + (my_gps.longitude[1] / 60)
        #print("Coordinates: ", my_gps.latitude[0] + (my_gps.latitude[1] / 60), my_gps.longitude[0] + (my_gps.longitude[1] / 60))
        print("Coordinates: ", self.gps_lat, self.gps_lng)
        #print("Date, time, speed: ", my_gps.date, my_gps.timestamp, my_gps.speed)
        print("Fix time, Sat in view, Sat in use, Sat used: ", my_gps.fix_time, my_gps.satellites_in_view, my_gps.satellites_in_use, my_gps.satellites_used)
        print("Time: ",rtc.now())
        pycom.rgbled(0x000000) # stop
        #s.send(gps_array)

    def refresh_ble(characteristic):
        characteristic.value(self.bme_temp)


    def get_bme_data(self):
        return self.bme_temp

    def get_bme_gps(self):
        return self.gps_lat

bluetooth = Bluetooth()
bluetooth.set_advertisement(name='IOTG-AA-01', service_uuid=b'1234567890123456')

def conn_cb (bt_o):
    events = bt_o.events()
    if  events & Bluetooth.CLIENT_CONNECTED:
        print("Client connected")
        pycom.rgbled(0x007f00) # green
    elif events & Bluetooth.CLIENT_DISCONNECTED:
        print("Client disconnected")
        pycom.rgbled(0x7f0000) # red
bluetooth.callback(trigger=Bluetooth.CLIENT_CONNECTED | Bluetooth.CLIENT_DISCONNECTED, handler=conn_cb)

bluetooth.advertise(True)

control_serv = bluetooth.service(uuid=b'0101010190123456', isprimary=True)
control_char = control_serv.characteristic(uuid=b'ab34567890123456', value=5)

char1_read_counter = 0
def char1_cb_handler(chr):
    global char1_read_counter
    char1_read_counter += 1

    events = chr.events()
    if events & Bluetooth.CHAR_WRITE_EVENT:
        pycom.rgbled(0x7f7f00) # yellow
        print("Write request with value = {}".format(chr.value()))
    elif events & Bluetooth.CHAR_READ_EVENT:
        pycom.rgbled(0x00007F) # blue
        print("Read request with value ")
    else:
        print("Unknown request")
    '''else:
        if char1_read_counter < 3:
            print('Read request on char 1')
        else:
            return 'ABC DEF'''

char1_cb = control_char.callback(trigger=Bluetooth.CHAR_WRITE_EVENT | Bluetooth.CHAR_READ_EVENT, handler=char1_cb_handler)

srv2 = bluetooth.service(uuid=1234, isprimary=True)

chr2 = srv2.characteristic(uuid=4567, value=0x1234)
char2_read_counter = 0xF0
def char2_cb_handler(chr):
    global char2_read_counter
    char2_read_counter += 1
    if char2_read_counter > 0xF1:
        return char2_read_counter

char2_cb = chr2.callback(trigger=Bluetooth.CHAR_READ_EVENT, handler=char2_cb_handler)

iotgKeyTrack = Keytrack()

sf_tx_nbr = 0

while True:
    iotgKeyTrack.refresh_bme()
    #if com.any():
    #    iotgKeyTrack.refresh_gps()
    time.sleep(2)#0.5
    iotgKeyTrack.refresh_gps()
    iotgKeyTrack.refresh_ble(chr2)

    print("2 sec sleep")
    pycom.rgbled(0)

'''
print("60 sleep")
time.sleep(60)'''
