from machine import Pin
import time

A = Pin(13, Pin.OUT)
B = Pin(12, Pin.OUT)
C = Pin(11, Pin.OUT)
D = Pin(10, Pin.OUT)

A2 = Pin(9, Pin.OUT)
B2 = Pin(8, Pin.OUT)
C2 = Pin(7, Pin.OUT)
D2 = Pin(6, Pin.OUT)

digit1 = Pin(2, Pin.OUT)
digit2 = Pin(3, Pin.OUT)

def set_bcd(val, A,B,C,D):
    A.value(val & 1)
    B.value((val >> 1) & 1)
    C.value((val >> 2) & 1)
    D.value((val >> 3) & 1)

def afficher(nombre):
    dizaines = nombre // 10
    unites = nombre % 10

    digit1.value(1)
    digit2.value(0)
    set_bcd(dizaines, A2,B2,C2,D2)
    time.sleep(0.005)

    digit1.value(0)
    digit2.value(1)
    set_bcd(unites, A,B,C,D)
    time.sleep(0.005)