import pika
import json
import grpc
from shared import invoice_pb2
from shared import invoice_pb2_grpc
from dotenv import load_dotenv
import os

load_dotenv()

host = os.getenv("HOST")
port = int(os.getenv("INVOICE_PORT"))

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
            datum = input("Bitte Rechnungsdatum eingeben: ")
            
            try:
                # 1. Verbindung zum Server auf Port 50052 aufbauen
                channel = grpc.insecure_channel(f"{host}:{port}")
                stub = invoice_pb2_grpc.InvoiceServiceStub(channel)
                
                # 2. Daten in das erwartete format umwandeln
                rechnung = invoice_pb2.Invoice(
                    id=rechnungsnummer,
                    supplier=lieferant,
                    amount=float(betrag),
                    date=datum
                )
                
                # 3. Den Speichern-Befehl an den Server schicken
                antwort = stub.SaveInvoice(rechnung)
                
                print(f"\nERFOLG: Der Server meldet: {antwort.message}")
                
            except ValueError:
                print("\nFEHLER: Bitte nur gültige Zahlen eingeben (nicht leer, keine Buchstaben, kein Komma!).")   
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.ALREADY_EXISTS:
                    print (f"\nUngültige Eingabe! (Details: {e.details()})")
                else:
                    print(f"\nFEHLER: Konnte gRPC-Server nicht erreichen. Läuft er? (Details: {e.details()})")
                
        elif auswahl == "2":
            print("\nZahlung veranlassen:")
            rechnungsnummer = input("Welche Rechnungsnummer soll bezahlt werden?: ")
            
            try:
                # Verbindung zum lokalen RabbitMQ-Broker herstellen
                connection = pika.BlockingConnection(pika.ConnectionParameters(host))
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
                
                print(f"\nERFOLG: Zahlungsauftrag für Rechnung {rechnungsnummer} an RabbitMQ gesendet!")
                
                # Verbindung beenden
                connection.close()
                
            except Exception:
                # Fehler-message, falls der RabbitMQ-Container/Server nicht läuft
                print(f"\nFEHLER: Konnte RabbitMQ nicht erreichen. Ist der Server an?")
                
        elif auswahl == "3":
            print("\nProgramm wird beendet. Tschüss!")
            break

        else:
            print("\nFEHLER: Falsche Eingabe! Bitte tippe nur 1, 2 oder 3.")

if __name__ == '__main__':
    main()
