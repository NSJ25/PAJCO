from machine import Pin

led_vert = Pin(20, Pin.OUT)
led_orange = Pin(21, Pin.OUT)
led_rouge = Pin(22, Pin.OUT)
led_lumiere = Pin(26, Pin.OUT)

def update_leds(places):
    led_vert.value(0)
    led_orange.value(0)
    led_rouge.value(0)

    if places >= 8:
        led_vert.value(1)
    elif places >= 1:
        led_orange.value(1)
    else:
        led_rouge.value(1)

def lumiere_on():
    led_lumiere.value(1)

def lumiere_off():
    led_lumiere.value(0)