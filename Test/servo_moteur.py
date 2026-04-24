from machine import Pin, PWM
import time

servo = PWM(Pin(26))
servo.freq(50)

def set_angle(angle):
    duty = int(1638 + (angle / 180) * (8192 - 1638))
    servo.duty_u16(duty)

while True:
    set_angle(0)
    time.sleep(2)

    set_angle(90)
    time.sleep(2)

