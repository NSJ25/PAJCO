import network
import time

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

wifi.connect("NomDuWifi", "MotDePasse")

print("Connexion au WiFi...")

while not wifi.isconnected():
    time.sleep(1)

print("Connecté !")

ip, masque, passerelle, dns = wifi.ifconfig()

print(f"Adresse IP : {ip}, Masque réseau : {masque}, Passerelle {passerelle}, DNS  {dns}")
