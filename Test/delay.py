import time

def delay_ms(ms):
    """
    Attendre le nombre de millisecondes passé en paramètre,
    sans bloquer complètement le CPU pour d'autres tâches.
    """
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < ms:
        pass  # le CPU continue de tourner très rapidement

