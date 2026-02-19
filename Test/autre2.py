from machine import Timer

def delay_ms_non_blocking(ms, callback):
    """
    Appelle callback après ms millisecondes, sans bloquer le CPU.
    """
    tim = Timer(-1)
    tim.init(period=ms, mode=Timer.ONE_SHOT, callback=lambda t: callback())



def fin_delay():
    print("Délai terminé !")

delay_ms_non_blocking(5, fin_delay)
