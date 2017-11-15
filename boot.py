import os
import machine
import pycom

uart = machine.UART(0, 115200)
os.dupterm(uart)

pycom.heartbeat(False)

machine.main('main.py')
print('==========Starting main.py==========\n')
