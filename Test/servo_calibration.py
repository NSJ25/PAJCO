from machine import PWM, Pin
from time import sleep

# Initialiser les servos
servo_enter = PWM(Pin(26))
servo_exit = PWM(Pin(22))

servo_enter.freq(50)
servo_exit.freq(50)

print("="*60)
print("CALIBRATION SERVO MOTEUR")
print("="*60)
print("\nFréquence: 50 Hz (20ms)")
print("Duty cycle (0-65535):")
print("  - 1ms (0°)   = 1638")
print("  - 1.5ms (90°) = 2457")
print("  - 2ms (180°) = 3276")
print("="*60)

# Valeurs par défaut
default_closed = 3276  # 1ms
default_open = 6553    # 2ms

print("\n🔧 TEST SERVO ENTRÉE (GPIO 26)")
print("-" * 60)

servo = servo_enter

# Test positions progressives
positions = {
    "Position 1 (500)": 500,
    "Position 2 (1000)": 1000,
    "Position 3 (1638 = 1ms/0°)": 1638,
    "Position 4 (2457 = 1.5ms/90°)": 2457,
    "Position 5 (3276 = 2ms/180°)": 3276,
    "Position 6 (4500)": 4500,
    "Position 7 (6000)": 6000,
    "Position 8 (6553 = 2.5ms)": 6553,
    "Position 9 (8000)": 8000,
}

for name, duty in positions.items():
    print(f"\n{name}")
    print(f"  → Envoi duty={duty}")
    servo.duty_u16(duty)
    sleep(1.5)
    print(f"  ✓ Attendez le mouvement du servo")

print("\n\n🔧 TEST SERVO SORTIE (GPIO 22)")
print("-" * 60)

servo = servo_exit

for name, duty in positions.items():
    print(f"\n{name}")
    print(f"  → Envoi duty={duty}")
    servo.duty_u16(duty)
    sleep(1.5)
    print(f"  ✓ Attendez le mouvement du servo")

# Positions finales (IMPORTANT: Revenir en position neutre)
print("\n" + "="*60)
print("POSITION NEUTRE (1.5ms = 90°) - Servo relaxé")
print("="*60)
servo_enter.duty_u16(2457)
servo_exit.duty_u16(2457)
sleep(1)

print("\n✅ Calibration terminée")
print("\n📝 NOTEZ LES VALEURS QUI CORRESPONDENT À:")
print("  - FERMÉ (0°): ___________")
print("  - OUVERT (180°): ___________")
print("\nPuis mettez à jour main_DEBUG.py avec ces valeurs!")
