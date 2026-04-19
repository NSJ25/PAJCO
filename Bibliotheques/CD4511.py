from machine import Pin
import _thread
import time


class CD4511:
    """
    Double afficheur 7 segments (0-99)
    avec CD4511 + 2 transistors (multiplexage)

    - 4 pins BCD (A, B, C, D)
    - 2 pins transistors (unités / dizaines)
    - affichage automatique via thread
    """

   
    def __init__(self, bcd_pins, transistor_pins):

        # -------- Validation --------
        if len(bcd_pins) != 4:
            raise ValueError("Il faut exactement 4 pins BCD (A, B, C, D)")

        if len(transistor_pins) != 2:
            raise ValueError("Il faut exactement 2 pins pour les transistors")

        # -------- Hardware BCD --------
        self.bcd = [Pin(p, Pin.OUT) for p in bcd_pins]

        # -------- Transistors --------
        self.digits = [Pin(p, Pin.OUT) for p in transistor_pins]

        # Éteindre les digits au départ
        for d in self.digits:
            d.value(0)

       
        self.value = 0          # nombre affiché (0-99)
        self.active = 0         # digit actif (0 ou 1)
        self.running = True     # contrôle thread

       
        _thread.start_new_thread(self._loop, ())

   
    def _write_bcd(self, number):
        """Envoie un chiffre (0-9) vers le CD4511"""
        for i in range(4):
            self.bcd[i].value((number >> i) & 1)

    
    def show(self, number):
        """
        Définit le nombre à afficher (0-99)
        """
        if number < 0:
            number = 0
        elif number > 99:
            number = 99

        self.value = number

    def _loop(self):
        while self.running:

            # -------- découpage nombre --------
            tens = self.value // 10
            units = self.value % 10

            # -------- gestion < 10 --------
            if self.value < 10:
                tens = 0

            digits = [tens, units]

            # -------- éteindre les digits --------
            self.digits[0].value(0)
            self.digits[1].value(0)

            # -------- envoyer BCD --------
            self._write_bcd(digits[self.active])

            # -------- activer digit --------
            self.digits[self.active].value(1)

            # -------- switch digit --------
            self.active = 1 - self.active

            # petit délai multiplexage
            time.sleep(0.002)

    
    def stop(self):
        self.running = False

        for d in self.digits:
            d.value(0)


if __name__ == "__main__":
    print("CD4511 prêt à l'utilisation")