from machine import Pin

class CD4511:
    """
    Gestion de deux afficheurs 7 segments cathode commune
    via CD4511 + 2 transistors NPN (multiplexage).
    """

    def __init__(self, bcd_pins, transistor_pins, le_pin, bi_pin, lt_pin):
        """
        bcd_pins : [A, B, C, D]
        transistor_pins : [unites, dizaines]
        le_pin : Latch Enable
        bi_pin : Blanking Input
        lt_pin : Lamp Test
        """

        # BCD
        self.bcd_pins = [Pin(pin, Pin.OUT) for pin in bcd_pins]

        # Transistors (digit select)
        self.transistors = [Pin(pin, Pin.OUT) for pin in transistor_pins]
        for t in self.transistors:
            t.value(0)

        # Pins de contrôle CD4511
        self.le = Pin(le_pin, Pin.OUT)
        self.bi = Pin(bi_pin, Pin.OUT)
        self.lt = Pin(lt_pin, Pin.OUT)

        # Configuration normale
        self.le.value(0)  # Pas de latch
        self.bi.value(1)  # Pas de blank
        self.lt.value(1)  # Pas de lamp test

        self.value = 0
        self.current_digit = 0

    # ---------- BCD ----------
    def set_bcd(self, number):
        if number < 0 or number > 9:
            raise ValueError("Chiffre doit être entre 0 et 9")

        for i, pin in enumerate(self.bcd_pins):
            pin.value((number >> i) & 1)

    # ---------- Valeur ----------
    def set_value(self, number):
        if number < 0 or number > 99:
            raise ValueError("Nombre doit être entre 0 et 99")
        self.value = number

    # ---------- ON / OFF ----------
    def on(self):
        self.bi.value(1)

    def off(self):
        self.bi.value(0)

    # ---------- Test segments ----------
    def test_segments(self):
        self.lt.value(0)  # Allume tous les segments

    def stop_test(self):
        self.lt.value(1)

    # ---------- Multiplexage ----------
    def refresh(self):
        if self.value < 10:
            digits = [0, self.value]
        else:
            digits = [self.value // 10, self.value % 10]

        # Désactiver tous les digits
        for t in self.transistors:
            t.value(0)

        # Envoyer BCD
        self.set_bcd(digits[self.current_digit])

        # Activer digit courant
        self.transistors[self.current_digit].value(1)

        # Prochain digit
        self.current_digit = (self.current_digit + 1) % 2


# Test
if __name__ == "__main__":
    print("Decode CD4511 prêt.")