from usocket import socket
from machine import Pin,WIZNET_PIO_SPI,UART, Pin
import network
import time

# Initialize UART on UART 0
uart = UART(0, baudrate=115200, tx=Pin(12), rx=Pin(13))

buff = bytearray(5)
final_buff = bytearray(64)
b_read = 0
b_discard = 0
i = 0
j = 0
prosesflag = 0
flag = 0
hexSys = hexDias = hexBPM = 0

# W5x00 Ethernet initialization
def w5x00_init():
    spi = WIZNET_PIO_SPI(baudrate=31_250_000, mosi=Pin(23),miso=Pin(22),sck=Pin(21)) #W55RP20 PIO_SPI
    nic = network.WIZNET5K(spi,Pin(20),Pin(25)) #spi,cs,reset pin
    nic.active(True)
# If you use the Dynamic IP(DHCP), you must use the "nic.ifconfig('dhcp')".
    nic.ifconfig('dhcp')
# If you use the Static IP, you must use the  "nic.ifconfig("IP","subnet","Gateway","DNS")".
    #nic.ifconfig(('192.168.100.13','255.255.255.0','192.168.100.1','8.8.8.8'))
       
    print('IP address :', nic.ifconfig())
    while not nic.isconnected():
        time.sleep(1)
        print(nic.regs())

# Function to send data to server
def submit_to_server(hexSys, hexDias, hexBPM):
    addr = ('192.168.110.54', 80)  # Replace with your server's IP and port
    s = socket()  # Create a socket
    s.connect(addr)
    
    # Form an HTTP POST request with the data
    request = f"""POST /digitalnurse/receive.php HTTP/1.1\r
Host: 192.168.110.54\r
Content-Type: application/x-www-form-urlencoded\r
Content-Length: {len('hexSys='+str(hexSys)+'&hexDias='+str(hexDias)+'&hexBPM='+str(hexBPM))}\r
\r
hexSys={hexSys}&hexDias={hexDias}&hexBPM={hexBPM}\r
"""
    s.send(request)
    response = s.recv(1024)
    print(response)
    s.close()

# Reading and processing data from UART
def bacaalat():
    global b_read, b_discard, i, j, prosesflag, flag, hexSys, hexDias, hexBPM

    while uart.any():
        if b_read == 0:
            if prosesflag == 0:
                buff[0] = uart.read(1)[0]
                if buff[0] == ord('s'):
                    buff[1] = uart.read(1)[0]
                    if buff[1] == ord('t'):
                        buff[2] = uart.read(1)[0]
                        if buff[2] == ord('a'):
                            buff[3] = uart.read(1)[0]
                            if buff[3] == ord('r'):
                                buff[4] = uart.read(1)[0]
                                if buff[4] == ord('t'):
                                    prosesflag = 1

            if prosesflag == 1:
                buff[0] = uart.read(1)[0]
                if buff[0] == ord('e'):
                    buff[1] = uart.read(1)[0]
                    if buff[1] == ord('r'):
                        buff[2] = uart.read(1)[0]
                        if buff[2] == ord('r'):
                            buff[3] = uart.read(1)[0]
                            if buff[3] == ord(':'):
                                buff[4] = uart.read(1)[0]
                                if buff[4] == ord('0'):
                                    b_read = 1
                                    j = 0
                                    b_discard = 0
                                    i = 0
                                    flag = 1  # err:0 --> success
                                elif buff[4] == ord('2'):
                                    flag = 2  # err:2 --> failure

        if b_read:
            if b_discard == 0:
                discard = uart.read(1)[0]
                i += 1
            elif j < 11:
                final_buff[j] = uart.read(1)[0]
                j += 1
            else:
                b_read = 0

            if i == 30:
                b_discard = 1

        time.sleep(0.002)  # Delay 2 milliseconds

    # HexSys, HexDias, HexBPM conversion
    if final_buff[0] > ord('9'):
        hexSys = (final_buff[0] - ord('7')) * 16
    else:
        hexSys = (final_buff[0] - ord('0')) * 16

    if final_buff[1] > ord('9'):
        hexSys += (final_buff[1] - ord('7'))
    else:
        hexSys += (final_buff[1] - ord('0'))

    if final_buff[3] > ord('9'):
        hexDias = (final_buff[3] - ord('7')) * 16
    else:
        hexDias = (final_buff[3] - ord('0')) * 16

    if final_buff[4] > ord('9'):
        hexDias += (final_buff[4] - ord('7'))
    else:
        hexDias += (final_buff[4] - ord('0'))

    if final_buff[9] > ord('9'):
        hexBPM = (final_buff[9] - ord('7')) * 16
    else:
        hexBPM = (final_buff[9] - ord('0')) * 16

    if final_buff[10] > ord('9'):
        hexBPM += (final_buff[10] - ord('7'))
    else:
        hexBPM += (final_buff[10] - ord('0'))

# Main loop
nic = w5x00_init()
last_hexSys = -1  # To store the last submitted value of hexSys
last_hexDias = -1  # To store the last submitted value of hexDias
last_hexBPM = -1  # To store the last submitted value of hexBPM

while True:
    bacaalat()

    # Check if valid data is available (i.e., hexBPM is greater than 0)
    if hexBPM > 0:
        print(f"BPM: {hexBPM}, SYS: {hexSys}, DIA: {hexDias}")

        # Check if the current data is different from the last submitted data
        if hexSys != last_hexSys or hexDias != last_hexDias or hexBPM != last_hexBPM:
            # Submit the data to the server
            submit_to_server(hexSys, hexDias, hexBPM)

            # Update the last submitted values to the current values
            last_hexSys = hexSys
            last_hexDias = hexDias
            last_hexBPM = hexBPM

            print("Data submitted. Waiting for new data...")

    time.sleep(1)  # Wait for a second before the next read
