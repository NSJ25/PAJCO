# Imports nécessaires pour Raspberry Pi Pico / MicroPython
from machine import Pin

class Decode:
    """
    Classe pour gérer deux afficheurs 7 segments via un décodeur 7447
    avec transistors pour dizaines et unités.
    Permet d'afficher un nombre (0-99) avec 0 devant si <10.
    """

    def __init__(self, bcd_pins, transistor_pins):
        """
        Initialise la classe Decode.

        Parameters:
        -----------
        bcd_pins : list[int]
            Pins GPIO connectées aux entrées BCD du 7447 [A,B,C,D]
        transistor_pins : list[int]
            Pins GPIO pour les transistors (unités, dizaines)
        """
        # Pins BCD
        self.bcd_pins = [Pin(pin, Pin.OUT) for pin in bcd_pins]

        # Pins pour les transistors
        self.transistors = [Pin(pin, Pin.OUT) for pin in transistor_pins]
        for t in self.transistors:
            t.value(0)  # éteint au départ

        # Nombre à afficher
        self.value = 0

        # Pour multiplexage non bloquant
        self.current_digit = 0  # 0 = premier afficheur, 1 = deuxième

    # ---------- Méthode interne ----------
    def set_bcd(self, number):
        """Envoie un chiffre 0-9 vers le 7447"""
        if number < 0 or number > 9:
            raise ValueError("Chiffre BCD doit être entre 0 et 9")
        for i, pin in enumerate(self.bcd_pins):
            pin.value((number >> i) & 1)

    # ---------- Mettre la valeur ----------
    def set_value(self, number):
        """
        Met à jour le nombre à afficher (0-99).
        Le chiffre <10 sera affiché avec un 0 devant.
        """
        if number < 0 or number > 99:
            raise ValueError("Nombre doit être entre 0 et 99")
        self.value = number

    # ---------- Allumer / Éteindre ----------
    def on(self):
        """Allume tous les afficheurs (transistors activés)"""
        for t in self.transistors:
            t.value(1)

    def off(self):
        """Éteint tous les afficheurs (transistors désactivés)"""
        for t in self.transistors:
            t.value(0)

    # ---------- Refresh non bloquant ----------
    def refresh(self, delay_ms=5):
        """
        Multiplexage entre dizaines et unités.
        Non bloquant : ne fait pas de sleep, juste alternance.
        delay_ms : int, millisecondes pour info (pas utilisé ici, mais pour thread externe)
        """
        # Découper le nombre en dizaines / unités
        if self.value < 10:
            digits = [0, self.value]  # 07, 03, etc.
        else:
            dizaines = self.value // 10
            unites = self.value % 10
            digits = [dizaines, unites]

        # Éteindre tous les transistors
        for t in self.transistors:
            t.value(0)

        # Activer transistor courant
        self.transistors[self.current_digit].value(1)

        # Envoyer chiffre BCD
        self.set_bcd(digits[self.current_digit])

        # Passer au digit suivant
        self.current_digit = (self.current_digit + 1) % len(self.transistors)

if __name__ == "__main__":
    print("Jeremie est le meilleur étudiant de la classe")