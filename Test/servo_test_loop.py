from machine import PWM, Pin
from time import sleep

# Initialiser les servos
servo_enter = PWM(Pin(26))
servo_exit = PWM(Pin(22))

servo_enter.freq(50)
servo_exit.freq(50)

# Valeurs de calibration (À ADAPTER selon servo_calibration.py)
SERVO_CLOSED = 3276   # 1ms → 0° (FERMÉ)
SERVO_OPEN = 6553     # 2ms → 180° (OUVERT)
SERVO_NEUTRAL = 2457  # 1.5ms → 90° (NEUTRE)

print("="*60)
print("TEST SERVO - OUVERTURE/FERMETURE EN BOUCLE")
print("="*60)
print(f"\nVALEURS UTILISÉES:")
print(f"  Fermé (0°): {SERVO_CLOSED}")
print(f"  Neutre (90°): {SERVO_NEUTRAL}")
print(f"  Ouvert (180°): {SERVO_OPEN}")
print("="*60)

def test_servo(servo, name):
    print(f"\n🔧 TEST {name}")
    print("-" * 60)
    
    for cycle in range(1, 6):
        print(f"\n📍 Cycle {cycle}:")
        
        # Neutre
        print(f"  1️⃣  Position NEUTRE...")
        servo.duty_u16(SERVO_NEUTRAL)
        sleep(1)
        
        # Ouvert
        print(f"  2️⃣  Position OUVERTE...")
        servo.duty_u16(SERVO_OPEN)
        sleep(2)
        
        # Neutre
        print(f"  3️⃣  Position NEUTRE...")
        servo.duty_u16(SERVO_NEUTRAL)
        sleep(1)
        
        # Fermé
        print(f"  4️⃣  Position FERMÉE...")
        servo.duty_u16(SERVO_CLOSED)
        sleep(2)
        
        print(f"  ✅ Cycle {cycle} terminé")

# Tester les servos
try:
    test_servo(servo_enter, "SERVO ENTRÉE (GPIO 26)")
    test_servo(servo_exit, "SERVO SORTIE (GPIO 22)")
    
    print("\n" + "="*60)
    print("✅ TEST TERMINÉ")
    print("="*60)
    print("\n📋 DIAGNOSTIC:")
    print("  ✓ Si les servos se déplacent correctement → OK")
    print("  ✗ Si un servo ne bouge qu'une fois:")
    print("    → Lancez servo_calibration.py pour ajuster les valeurs")
    print("    → Vérifiez l'alimentation (5V stable)")
    print("    → Testez les câbles de connexion")
    
except KeyboardInterrupt:
    print("\n❌ Test arrêté")
    # Position neutre finale
    servo_enter.duty_u16(SERVO_NEUTRAL)
    servo_exit.duty_u16(SERVO_NEUTRAL)
