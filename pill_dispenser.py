from machine import Pin, ADC, I2C
from stepper import Stepper
import time
import ssd1306
from buttons import Button
from counter import Counter
from led import Led
from lora import Lora

motor = Stepper(2,3,4,5)

opto = Pin(16, mode = Pin.IN, pull = Pin.PULL_UP)
#piezo = Pin(15, mode = Pin.IN, pull = Pin.PULL_UP)

pin0 = Button(9, Pin.IN, Pin.PULL_UP)
pin1 = Button(8, Pin.IN, Pin.PULL_UP)
pin2 = Button(7, Pin.IN, Pin.PULL_UP)
lora = Lora(0, Pin(0), Pin(1), 9600)
rotary = Button(12, Pin.IN, Pin.PULL_UP)

piezo_hit = False
dose_counter = 0
day_counter = 0
counter = Counter(17)
led = Led(20)
max_days = 7
max_doses = 7

sda=machine.Pin(14) 
scl=machine.Pin(15) # Sda and scl pins is for the oled 
i2c=machine.I2C(1, sda=sda, scl=scl, freq=400000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)

def pills_received(dose_counter, operation):
    cTime = time.localtime()
    d = '{:02d}.{:02d}.{:02d}'.format(cTime[2], cTime[1], cTime[0]) # Format date
    t = '{:02d}:{:02d}:{:02d}'.format(cTime[3], cTime[4], cTime[5]) # Format time
    #print(d, t)
    display.poweron()
    display.fill(0) # Clear display
    if day_counter < max_doses and operation is "dose":
        display.text(d, 0, 0, 1)
        display.text(t, 0, 10, 1)
        display.text('%s doses received' % dose_counter, 0, 40, 1)
        display.show()
    elif day_counter is max_days and operation is "dose":
        display.text(d, 0, 0, 1)
        display.text(t, 0, 10, 1)
        display.text('%s doses received' % dose_counter, 0, 40, 1)
        display.text('Please calibrate doser', 0, 50, 1)
        display.show()
    elif day_counter is max_days and operation is "no_pill":
        display.text(d, 0, 0, 1)
        display.text(t, 0, 10, 1)
        display.text('%s doses received' % dose_counter, 0, 40, 1)
        display.text('Please calibrate doser', 0, 50, 1)
        display.show()
    elif operation is "history":
        display.poweron() 
        display.fill(0) # Clear display
        display.text(d, 0, 0, 1)
        display.text(t, 0, 10, 1)
        display.text('HISTORY:', 0, 30, 1)
        display.text('%s doses received ' % dose_counter, 0, 40, 1)
        display.show()
    elif operation is "no_pill":
        display.poweron()
        display.fill(0)
        display.text(d, 0, 0, 1)
        display.text(t, 0, 10, 1)
        display.text('No dose detected', 0, 40, 1)
        display.show()
        
def lora_send():
    cTime = time.localtime()
    d = '{:02d}.{:02d}.{:02d}'.format(cTime[2], cTime[1], cTime[0]) # Format date
    t = '{:02d}:{:02d}:{:02d}'.format(cTime[3], cTime[4], cTime[5]) # Format time
    lora.at(f'+MSG="Daily dose received. Doses: {dose_counter}"')
    lora.wait('MSG: Done', 10)  
    lora.at(f'+MSG="Day: {d}. Time: {t} Day count: {day_counter}"')
    lora.wait('MSG: Done', 10)
    
def lora_error():
    cTime = time.localtime()
    d = '{:02d}.{:02d}.{:02d}'.format(cTime[2], cTime[1], cTime[0]) # Format date
    t = '{:02d}:{:02d}:{:02d}'.format(cTime[3], cTime[4], cTime[5]) # Format time
    
    lora.at(f'+MSG="No pill detected. Past doses: {dose_counter}"')
    lora.wait('MSG: Done', 10)
    lora.at(f'+MSG="Day: {d}. Time: {t} Day count: {day_counter}"')
    lora.wait('MSG: Done', 10)
    
lora.at('+ID')
lora.wait('AppEui')
lora.at('+MODE=LWOTAA')
lora.wait('+MODE: LWOTAA')
lora.at('+DR')
lora.wait('EU868')
lora.at('+KEY=APPKEY,"3a8ade218c80b491249468af6438d186"')
lora.wait('+KEY: APPKEY')
lora.at('+CLASS=A')
lora.wait('+CLASS: A')
lora.at('+PORT=8')
lora.wait('+PORT: 8')

lora.at('+JOIN')
status, res = lora.wait('+JOIN: Done',12)

while not status or res.find('failed') >= 0:
    lora.at('+JOIN')
    status, res = lora.wait('+JOIN: Done',12)


lora.at('+ID')
                

#4112 rotate dispenser full circle
#514 rotate dispenser one slot forward

pills_received(dose_counter, "dose")

# Run doser
while True:
    time.sleep(0.010)
    if pin0.pressed(): # Calibrate dispenser to start position, SW_0
        print("dose_counter: ", dose_counter)
        print("day_counter: ", day_counter)
        display.poweroff()
        run = 1 # Permission to run
        opto_zero = True # Set True as a default value

        if opto() == 0: # If opto returns zero, dispenser is still near start position
            opto_zero = True

        while run == 1: # Run dispenser while 1
            motor.step(False)
            time.sleep(0.002)
            if opto() == 1 and opto_zero: # When opto stops returning 0
                opto_zero = False 
            if opto() == 0 and not opto_zero: # Opto 0 detected. Stop dispenser
                run = 0
        
                for i in range(140): # Position dispenser neatly to start position
                    motor.step(False)
                    time.sleep(0.002)
                counter.reset()
                dose_counter = 0
                day_counter = 0
                pills_received(dose_counter, "dose")
    
    if pin1.pressed() and day_counter < max_days: # Move dispenser one slot ccw SW_1
        counter.reset()
        day_counter += 1
        print("day_counter: ", day_counter)
        for i in range(514):
            motor.step(False)
            time.sleep(0.002)
        time.sleep(0.1)
         
        if counter.get() > 0:
            print("Piezo hit")
            piezo_hit = True
            led.off()
            
            if piezo_hit:
                dose_counter += 1
                piezo_hit = False
                time.sleep(0.002)
                print("dose_counter: ", dose_counter)
                counter.reset()
                pills_received(dose_counter, "dose")
                lora_send()
        else:
            pills_received(dose_counter, "no_pill")
            for i in range(5):
                led.on()
                time.sleep(0.5)
                led.off()
                time.sleep(0.5)
            lora_error()

    if pin2.pressed(): # SW_2
        pills_received(dose_counter, "history")
    
    if rotary.pressed():
        
        for i in range(10):
                led.on()
                time.sleep(0.5)
                led.off()
                time.sleep(0.5)
            
print(opto())
