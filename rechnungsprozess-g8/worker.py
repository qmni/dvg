import asyncio 
import logging 
import json 
import os 
import pika 
import sys 
import aiohttp  # Für den n8n-Aufruf 
from pathlib import Path 
import grpc 
from dotenv import load_dotenv 
from pyzeebe import ZeebeWorker, create_camunda_cloud_channel 
from pyzeebe.errors import BusinessError 

try: 
    import invoice_pb2 
    import invoice_pb2_grpc 
except ImportError: 
    pass 

if sys.platform == "win32": 
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) 

# 1. Pfad zur .env Datei explizit definieren und laden
BASE_DIR = Path(__file__).resolve().parent 
load_dotenv(BASE_DIR / ".env") 

logging.basicConfig(level=logging.INFO) 

# Verbindungseinstellungen für andere Services
INVOICE_HOST = os.getenv("INVOICE_HOST", "localhost") 
INVOICE_PORT = os.getenv("INVOICE_PORT", "50052") 
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost") 
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/deine-id") 

# Camunda Konfiguration aus der .env laden
ZEEBE_CLIENT_ID = os.getenv("ZEEBE_CLIENT_ID") or os.getenv("CAMUNDA_CLIENT_ID") 
ZEEBE_CLIENT_SECRET = os.getenv("ZEEBE_CLIENT_SECRET") or os.getenv("CAMUNDA_CLIENT_SECRET") 
ZEEBE_CLUSTER_ID = os.getenv("ZEEBE_CLUSTER_ID") or os.getenv("CAMUNDA_CLUSTER_ID") 
ZEEBE_REGION = os.getenv("ZEEBE_REGION") or os.getenv("CAMUNDA_REGION") 

async def main(): 
    # Sicherheits-Check für dich im Terminal
    print(f"[DEBUG] Lade aus .env... Cluster-ID: {ZEEBE_CLUSTER_ID}")

    if not ZEEBE_CLUSTER_ID:
        print("!!! FEHLER: ZEEBE_CLUSTER_ID ist leer. Die .env wurde nicht geladen oder ist falsch!")
        sys.exit(1)

    # 2. Variablen direkt an den Channel übergeben (Verhindert den SettingsError)
    channel = create_camunda_cloud_channel(
        client_id=ZEEBE_CLIENT_ID,
        client_secret=ZEEBE_CLIENT_SECRET,
        cluster_id=ZEEBE_CLUSTER_ID,
        region=ZEEBE_REGION
    ) 
    worker = ZeebeWorker(channel) 

    # 1. TASK: Daten per KI aus n8n holen 
    @worker.task(task_type="call-n8n") 
    async def call_n8n(**kwargs): 
        print("\n[Camunda-Worker] Task 'call-n8n' empfangen.") 
        print(f"[DEBUG] Variablen aus Camunda: {kwargs}")

        async with aiohttp.ClientSession() as session: 
            try: 
                data = aiohttp.FormData()

                # Lokales Dokumenten-Streaming (Simuliertes Camunda-SaaS-Storage-Handling)
                fallback_path = BASE_DIR / "deine_test_rechnung.pdf"
                print(f"[INFO] Bereite Rechnungsdatei für n8n vor...")
                
                if fallback_path.exists():
                    with open(fallback_path, 'rb') as f:
                        file_bytes = f.read()
                    print(f"[INFO] Datei '{fallback_path.name}' erfolgreich als Binär-Stream geladen.")
                else:
                    print("[FEHLER] 'deine_test_rechnung.pdf' nicht im Projektverzeichnis gefunden!")
                    raise FileNotFoundError("Keine Rechnungsdatei verfügbar.")

                # Datei als Binärfeld an n8n übergeben
                # 'Rechnung' entspricht exakt dem Namen in deinem n8n 'Extract from File' Node!
                data.add_field('Rechnung', file_bytes, filename='rechnung.pdf', content_type='application/pdf')
                
                # Optionale Metadaten mitsenden
                data.add_field('context', json.dumps(kwargs))

                print(f"[INFO] Sende Binärdaten an n8n Webhook: {N8N_WEBHOOK_URL}")
                async with session.post(N8N_WEBHOOK_URL, data=data) as response: 
                    result = await response.json() 
                    print(f"[DEBUG] Antwort von n8n erhalten: {result}")
                    
                    if not result:
                        raise Exception("n8n hat leere Daten zurückgegeben.")

                    # Das Mapping der Felder auf die Camunda-Variablen
                    mapped_variables = { 
                        "id": result.get("id"), 
                        "supplier": result.get("supplier"), 
                        "amount": float(result.get("amount", 0)) if result.get("amount") else 0.0, 
                        "date": result.get("date"), 
                        "position_description": result.get("positions", [{}])[0].get("description") if result.get("positions") else None, 
                        "position_quantity": result.get("positions", [{}])[0].get("quantity") if result.get("positions") else None, 
                        "position_unit": result.get("positions", [{}])[0].get("unit") if result.get("positions") else None, 
                        "position_unit_price": float(result.get("positions", [{}])[0].get("unitPrice", 0)) if result.get("positions") else 0.0, 
                        "position_tax": result.get("positions", [{}])[0].get("tax") if result.get("positions") else None 
                    } 
                    print("[n8n] Mapping erfolgreich:", mapped_variables) 
                    return mapped_variables 
            except Exception as e: 
                print(f"[FEHLER] n8n Aufruf fehlgeschlagen: {str(e)}") 
                raise BusinessError("N8N_CALL_FAILED", str(e))

    # 2. TASK: Rechnung speichern 
    @worker.task(task_type="save-invoice") 
    async def save_invoice(id=None, supplier=None, amount=None, date=None): 
        try: 
            grpc_channel = grpc.insecure_channel(f"{INVOICE_HOST}:{INVOICE_PORT}") 
            stub = invoice_pb2_grpc.InvoiceServiceStub(grpc_channel) 
            rechnung = invoice_pb2.Invoice(id=str(id), supplier=str(supplier), amount=float(amount), date=str(date)) 
            antwort = stub.SaveInvoice(rechnung) 
            return {"invoice_saved": True, "invoice_message": antwort.message} 
        except Exception as e: 
            raise BusinessError("INVOICE_SAVE_FAILED", str(e)) 

    # 3. TASK: Payment-Order an RabbitMQ 
    @worker.task(task_type="send-payment-order") 
    async def send_payment_notification(**kwargs): 
        try: 
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST)) 
            rabbit_channel = connection.channel() 
            rabbit_channel.queue_declare(queue="payment_queue") 
            rabbit_channel.basic_publish(exchange="", routing_key="payment_queue", body=json.dumps(kwargs)) 
            connection.close() 
            return {"payment_message_sent": True} 
        except Exception as e: 
            return {"payment_message_sent": False, "payment_error": str(e)} 

    # Weitere Tasks 
    @worker.task(task_type="rechnungsdaten-validieren") 
    async def task_validation(): return {"complianceCheckNotwendig": False} 
     
    @worker.task(task_type="erp-system") 
    async def task_erp(): return {"erp_erfolgreich": True} 

    @worker.task(task_type="zahlung-ausführen") 
    async def task_final(): return {} 

    # DIE ALTE AUSGABE
    print("\n" + "=" * 50) 
    print("--- CAMUNDA WORKER GESTARTET ---") 
    print(f"Invoice gRPC Server: {INVOICE_HOST}:{INVOICE_PORT}") 
    print(f"RabbitMQ Host: {RABBITMQ_HOST}") 
    print("Lausche auf Tasks aus Camunda Cloud...") 
    print("=" * 50) 

    await worker.work() 

if __name__ == "__main__": 
    try: 
        asyncio.run(main()) 
    except KeyboardInterrupt: 
        print("\nWorker gestoppt.")