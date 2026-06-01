import pika
import json
import time
from dotenv import load_dotenv
import os

load_dotenv()
host = os.getenv("HOST") or "localhost"

def process_payment(nachricht):
    print("=" * 40)
    print("📥 NEUE ZAHLUNG EMPFANGEN")
    print("-" * 40)
    
    # Hier holen wir die Werte mit den exakten Keys, die der Worker sendet
    invoice_id = nachricht.get('invoiceId', 'N/A')
    betrag = nachricht.get('amount', 0.0)
    lieferant = nachricht.get('supplier', 'N/A')
    datum = nachricht.get('date', 'N/A')
    
    print(f"📄 Rechnungs-ID: {invoice_id}")
    print(f"🏢 Lieferant:    {lieferant}")
    print(f"💰 Betrag:       {betrag:.2f} €")
    print(f"📅 Datum:        {datum}")
    print("-" * 40)

    print(f"Verarbeite Zahlung für Rechnung {invoice_id}...")
    time.sleep(2)  # Simuliere Verzögerung

    print("✅ Zahlung erfolgreich abgeschlossen!")
    print("=" * 40 + "\n")


def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        process_payment(data)
    except Exception as e:
        print(f"Fehler beim Verarbeiten der Zahlung: {e}")  


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host))
    channel = connection.channel()

    channel.queue_declare(queue='payment_queue')

    channel.basic_consume(queue='payment_queue', on_message_callback=callback, auto_ack=True)   

    print('Warte auf Zahlungen. Drücke Strg+C zum Beenden.')
    channel.start_consuming()
    
if __name__ == "__main__":
    main()