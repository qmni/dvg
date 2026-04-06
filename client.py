def main():
    print("Willkommen im Rechnungs-Client von Team 8!")

    while True:
        print("\n" + "="*30)
        print("HAUPTMENÜ")
        print("="*30)
        print("1: Neue Rechnung erfassen")
        print("2: Zahlung veranlassen")
        print("3: Programm beenden")
        print("="*30)

        auswahl = input("\nWas möchtest du tun? (1, 2 oder 3 eingeben): ")

        if auswahl == "1":
            print("\nRechnung erfassen:")
            rechnungsnummer = input("Bitte Rechnungsnummer eingeben: ")
            lieferant = input("Bitte Lieferant eingeben: ")
            betrag = input("Bitte Betrag in Euro eingeben: ")

            # HIER KOMMT SPÄTER DER GRPC CODE HIN!
            
            print("ERFOLG: Rechnung " + rechnungsnummer + " von " + lieferant + " über " + betrag + "€ würde jetzt per gRPC gespeichert werden!")

        elif auswahl == "2":
            print("\nZahlung veranlassen:")
            rechnungsnummer = input("Welche Rechnungsnummer soll bezahlt werden?: ")

            # HIER KOMMT SPÄTER DER RABBITMQ CODE HIN!
            
            print("ERFOLG: Zahlungsauftrag für Rechnung " + rechnungsnummer + " würde jetzt an RabbitMQ gesendet werden!")

        elif auswahl == "3":
            print("\nProgramm wird beendet. Tschüss!")
            break

        else:
            print("\nFEHLER: Falsche Eingabe! Bitte tippe nur 1, 2 oder 3.")

if __name__ == '__main__':
    main()