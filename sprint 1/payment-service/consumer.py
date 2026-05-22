import pika
import json
import time
from dotenv import load_dotenv
import os

load_dotenv()
host = os.getenv("HOST")

def process_payment(nachricht):
    print("Zahlung empfangen:", nachricht)

    # Simuliere die Zahlungsabwicklung
    print(f"Zahle {nachricht['invoiceId']}...")
    time.sleep(2)  # Simuliere Verzögerung

    print("Zahlung erfolgreich abgeschlossen!\n")


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