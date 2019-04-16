# Copyright (c) 2017 Adafruit Industries
# Author: Tony DiCola & James DeVito
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import time
import os
import json
import datetime
import sys, platform, requests, gzip
import RPi.GPIO as GPIO
import threading
import math
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import subprocess

# Set Relay Info for Tendeka Azure VM
#relay_url = "https://13.91.92.47:5460/ingress/messages"
#producertoken = "uid=88c085ef-276d-4cbd-b425-1a2b573c2ac3&sig=Ni0a5Xhxy6awpqwQzt5RlC95a+nV2f/BJMIpGP21mww="
VERIFY_SSL = False

# Set Relay Info for OCS
relay_url = "https://historianmain.osipi.com/api/omf"
producertoken = "1/0aab5307c9f1421e94fa5e85951b7c4f/a7c7a56684024214aba90597eba88fb3/a445ee81-2b91-4806-883b-1dc673d59147/65234833200/xczHpGxn3n%2F5I9n43luXgxllM4NdT%2FCsX3KW8dIHzvI%3D"


GPIO.setmode(GPIO.BCM)
echo = 21
trigger = 23
led1 = 13
led2 = 12
GPIO.setup(echo, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(trigger, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(led1, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(led2, GPIO.OUT, initial=GPIO.HIGH)

# Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0
YellowHeight = 16
BlueHeight = 48


# Beaglebone Black pin configuration:
# RST = 'P9_12'
# Note the following are only used with SPI:
# DC = 'P9_15'
# SPI_PORT = 1
# SPI_DEVICE = 0

# 128x32 display with hardware I2C:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)

# 128x64 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

# Note you can change the I2C address by passing an i2c_address parameter like:
# disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, i2c_address=0x3C)

# Alternatively you can specify an explicit I2C bus number, for example
# with the 128x32 display you would use:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST, i2c_bus=2)

# 128x32 display with hardware SPI:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=8000000))

# 128x64 display with hardware SPI:
# disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=8000000))

# Alternatively you can specify a software SPI implementation by providing
# digital GPIO pin numbers for all the required display pins.  For example
# on a Raspberry Pi with the 128x32 display you might use:
# disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST, dc=DC, sclk=18, din=25, cs=22)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create the type messages
distanceType = {
	"id": "Aisle_Distance_1",
	"description": "A Distance + timestamp object",
	"type": "object",
	"classification": "dynamic",
	"properties": {
		"Time": {"type": "string", 
			"format": "date-time", 
			"isindex": True
			},
		"Aisle_Distance": {"type": "number" 
			}
	}
}

json_types = json.dumps([distanceType])

#Define Container (Stream)
container_distance = {
	"id":"aisle_distanceContainer",
	"typeid": "Aisle_Distance"
	}
json_container = json.dumps([container_distance]) 

# Send the Type Message
msg_header = {'producertoken': producertoken, 'messagetype': 'type', 'action': 'create', 'omfversion': '1.0', 'messageformat': 'json'}
response = requests.post(url=relay_url, headers=msg_header, data=json_types, verify=VERIFY_SSL)
print ('Sending:' , msg_header, json_types)
print(
	'Response from relay from sending message of type ' + 
	':{0} {1}' .format(
	response.status_code,
	response.text
	)
)

#sys.exit()

# Send the container (streams) message
#msg_header = {'producertoken': producertoken, 'messagetype': 'Container', 'action': 'create', 'omfversion': '1.0', 'messageformat': 'json'}
msg_header = {'producertoken': producertoken, 'messagetype': 'Stream', 'action': 'create', 'omfversion': '1.0', 'messageformat': 'json'}

response = requests.post(url=relay_url, headers=msg_header, data=json_container, verify=VERIFY_SSL)
print("Sending Stream: ", json_container)
print(
	'Response from relay from sending message of container ' + 
	':{0} {1}' .format(
	response.status_code,
	response.text
	)
)

now = datetime.datetime.utcnow().isoformat() + 'Z'

aisle_distance_value = {
	"containerid": "aisle_distanceContainer",
	"values":[
		{ "Time": now, "Aisle_Distance": 0}
	]
}

values = [aisle_distance_value]
json_values = json.dumps(values)

msg_header = {'producertoken' : producertoken, 'messagetype' : 'data', 'action' : 'create', 'omfversion' : '1.0', 'messageformat' : 'json'}
response = requests.post(url=relay_url, headers=msg_header, data=json_values, verify=VERIFY_SSL)
print(
    "Response from Relay when sending data message", response.status_code, response.text
    )
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
fontsize=14
font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf",size=fontsize)
font_default = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('Minecraftia.ttf', 8)
# Draw a black filled box to clear the image.
draw.rectangle((0,0,width-1,YellowHeight-1), outline=255, fill=0)
draw.rectangle((0,YellowHeight,width-1,height-1), outline=255, fill=0)

# Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
#cmd = "hostname -I | cut -d\' \' -f1"
cmd = "hostname -I "
IP = subprocess.check_output(cmd, shell = True )
cmd = "top -bn1 | grep load | awk '{printf \"CPU: %.2f\", $(NF-2)}'"
CPU = subprocess.check_output(cmd, shell = True )
cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
MemUsage = subprocess.check_output(cmd, shell = True )
cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
Disk = subprocess.check_output(cmd, shell = True )

    # Write two lines of text.

draw.text((x, top+3),     str(IP),  font=font, fill=255)
draw.text((x, top+YellowHeight+2),    str(CPU), font=font, fill=255)
draw.text((x, YellowHeight + 18),    str(MemUsage),  font=font, fill=255)
draw.text((x, YellowHeight +34),    str(Disk),  font=font, fill=255)

# Display image.
disp.image(image)
disp.display()
time.sleep(5)
    
# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

CPU_List=[0]
CPU_Max = max(CPU_List)
Trend_Height = 48

while True:

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width-1,YellowHeight-1), outline=255, fill=0)
    draw.rectangle((0,YellowHeight,width-1,height-1), outline=255, fill=0)

    # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    #cmd = "hostname -I | cut -d\' \' -f1"
    cmd = "hostname -I "
    IP = subprocess.check_output(cmd, shell = True )
    cmd = "top -bn1 | grep load | awk '{printf \"CPU: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell = True )
    CPU_Value = CPU[6:10]
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell = True )
    cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
    Disk = subprocess.check_output(cmd, shell = True )
    
    GPIO.output(trigger, False)
    print (".")
    time.sleep(.05)
    
    GPIO.output(trigger, True)                  #Set TRIG as HIGH
    time.sleep(0.00002)                     #Delay of 0.00001 seconds
    GPIO.output(trigger, False)                 #Set TRIG as LOW

    while GPIO.input(echo)==0:               #Check whether the ECHO is LOW
        pulse_start = time.time()              #Saves the last known time of LOW pulse

    while GPIO.input(echo)==1:               #Check whether the ECHO is HIGH
        pulse_end = time.time()                #Saves the last known time of HIGH pulse 

    pulse_duration = pulse_end - pulse_start #Get pulse duration to a variable

    distance = pulse_duration * 17150        #Multiply pulse duration by 17150 to get distance
    distance_cm = round(distance, 1)
    distance_in = round(distance/2.54, 1)
    distance_ft = round((distance/2.54)/12, 1)
    
    
    #Round to two decimal points

    if distance_cm > 2 and distance_cm < 400:      #Check whether the distance is within range
    #    print ("Distance: ",distance_cm - 0.5, " cm   ", distance_in, " in    ", distance_ft, " ft")  #Print distance with 0.5 cm calibration
        distance_display = distance_in
        if distance_in < 70 and distance_in > 1:
            GPIO.output(led2,0)
        else:
            GPIO.output(led2, 1)
            
    else:
        print ("Out of Range")                   #display out of range
        
        
    CPU_List.append(float(distance_in))

    if len(CPU_List) == 127:
        CPU_List.pop(0)
    print (CPU_List)    
    CPU_Max = 70
    #CPU_Max = float(max(CPU_List))    
    CPU_Display_Multiplier = Trend_Height / CPU_Max     
        
        
    # Write two lines of text.
    Last_Value = str(CPU_List[-1])
    Max_Value = str(CPU_Max)

    draw.text((x, top+3), "DIST: " ,  font=font, fill=255)
    draw.text((x+48, top+3), Last_Value, font=font, fill=255)
    
              
    for i in range(len(CPU_List)):
#        draw.rectangle((i, height, i+4, Trend_Height - (CPU_Display_Multiplier * CPU_List[i])), outline=255, fill=0)
         if (CPU_List[i]) < height:
            draw.rectangle((i, (height - (CPU_Display_Multiplier * CPU_List[i])), i+1, height), outline=255, fill=0)
        
         else:
            draw.rectangle(((i, height), (i+1, height)), outline=255, fill=0)
    
    #draw.text((x, YellowHeight + 18),    str(MemUsage),  font=font, fill=255)
    #draw.text((x, YellowHeight +34),    str(Disk),  font=font, fill=255)
    draw.rectangle((86,0, 132, 15), outline=0, fill=255)
    draw.text((96, top+3), Max_Value, font=font, fill=0)
    # Display image.
    disp.image(image)
    disp.display()
    time.sleep(.05)
