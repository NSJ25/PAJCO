from machine import Pin, PWM
import time

servo = PWM(Pin(15))
servo.freq(50)

def set_angle(angle):
    # plage élargie
    duty = int(1000 + (angle / 180) * 8000)
    servo.duty_u16(duty)

while True:
    set_angle(0)
    time.sleep(2)

    set_angle(90)
    time.sleep(2)

    set_angle(180)
    time.sleep(2)

