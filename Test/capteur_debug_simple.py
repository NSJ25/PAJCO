from machine import Pin
from time import sleep

# Testez les capteurs
capteur_enter = Pin(21, Pin.IN, Pin.PULL_UP)
capteur_exit = Pin(20, Pin.IN, Pin.PULL_UP)

print("="*50)
print("TEST CAPTEURS - Appuyez sur Ctrl+C pour arrêter")
print("="*50)
print("(0 = détecté/proche, 1 = libre/loin)\n")

try:
    while True:
        enter_val = capteur_enter.value()
        exit_val = capteur_exit.value()
        
        # Affichage
        enter_status = "🔴 DÉTECTÉ" if enter_val == 0 else "🟢 LIBRE"
        exit_status = "🔴 DÉTECTÉ" if exit_val == 0 else "🟢 LIBRE"
        
        print(f"\rCapteur ENTRÉE (GPIO 21): {enter_val} {enter_status}  |  Capteur SORTIE (GPIO 20): {exit_val} {exit_status}", end="")
        
        sleep(0.1)
        
except KeyboardInterrupt:
    print("\n\n❌ Test arrêté")
    print("\nDiagnostic:")
    print("- Si les capteurs ne changent PAS d'état → Vérifiez le câblage ou l'alimentation")
    print("- Si TOUJOURS 0 → Capteur peut-être défaillant ou mal calibré")
    print("- Si TOUJOURS 1 → Les capteurs ne voient rien (normal au départ)")
