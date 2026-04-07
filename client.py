import pika
import json

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

            try:
                # Verbindung zum lokalen RabbitMQ-Broker herstellen
                connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
                # Kommunikationskanal für die Session öffnen
                channel = connection.channel()
                
                # Sicherstellen, dass die Ziel-Queue existiert
                channel.queue_declare(queue='payment_queue')
                
                # Payload im erwarteten Format vorbereiten
                zahlungs_daten = {
                    "invoiceId": rechnungsnummer
                }
                # Payload in einen JSON-String serialisieren
                nachricht_json = json.dumps(zahlungs_daten)
                
                # Nachricht ohne spezifischen Exchange direkt in die Queue pushen
                channel.basic_publish(
                    exchange='', 
                    routing_key='payment_queue', 
                    body=nachricht_json
                )
                
                print("\nERFOLG: Zahlungsauftrag für Rechnung " + rechnungsnummer + " an RabbitMQ gesendet!")
                
                # Verbindung beenden
                connection.close()

            except Exception:
                # Fallback, falls der RabbitMQ-Container/Server nicht läuft
                print("\nFEHLER: Konnte RabbitMQ nicht erreichen. Ist der Server an?")

        elif auswahl == "3":
            print("\nProgramm wird beendet. Tschüss!")
            break

        else:
            print("\nFEHLER: Falsche Eingabe! Bitte tippe nur 1, 2 oder 3.")

if __name__ == '__main__':
    main()