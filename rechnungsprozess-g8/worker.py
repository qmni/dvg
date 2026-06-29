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

        async with aiohttp.ClientSession() as session: 
            try: 
                data = aiohttp.FormData()
                fallback_path = BASE_DIR / "deine_test_rechnung.pdf"
                
                if fallback_path.exists():
                    with open(fallback_path, 'rb') as f:
                        file_bytes = f.read()
                else:
                    raise FileNotFoundError("Keine Rechnungsdatei verfügbar.")

                data.add_field('Rechnung', file_bytes, filename='rechnung.pdf', content_type='application/pdf')
                data.add_field('context', json.dumps(kwargs))

                print(f"[INFO] Sende Binärdaten an n8n Webhook: {N8N_WEBHOOK_URL}")
                async with session.post(N8N_WEBHOOK_URL, data=data) as response: 
                    
                    # 1. Status-Check der HTTP-Antwort
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"n8n antwortete mit Status {response.status}: {error_text}")
                    
                    # 2. Text empfangen und prüfen, ob überhaupt etwas ankam
                    response_text = await response.text()
                    if not response_text or response_text.strip() == "":
                        raise Exception("n8n hat eine komplett leere Antwort zurückgegeben.")
                    
                    # 3. Sicher in JSON umwandeln
                    try:
                        result = json.loads(response_text)
                    except json.JSONDecodeError:
                        raise Exception(f"n8n-Antwort ist kein gültiges JSON. Inhalt: {response_text}")

                    # 4. n8n kann manchmal ein JSON-Array zurückgeben; wir nutzen das erste Objekt
                    if isinstance(result, list):
                        if len(result) >= 1 and isinstance(result[0], dict):
                            result = result[0]
                        else:
                            raise Exception(
                                f"n8n-Antwort ist ein JSON-Array, aber ein Objekt wurde erwartet. Inhalt: {response_text}"
                            )

                    # 5. n8n kann die Daten unter 'output' oder 'response' verschachteln
                    raw_data = result
                    if isinstance(raw_data, dict):
                        if "output" in raw_data and isinstance(raw_data["output"], (dict, list)):
                            raw_data = raw_data["output"]
                        elif "response" in raw_data and isinstance(raw_data["response"], (dict, list)):
                            raw_data = raw_data["response"]

                    if isinstance(raw_data, list):
                        if len(raw_data) >= 1 and isinstance(raw_data[0], dict):
                            raw_data = raw_data[0]
                        else:
                            raise Exception(
                                f"n8n-Antwort enthält eine Liste ohne gültiges Objekt. Inhalt: {response_text}"
                            )

                    if not isinstance(raw_data, dict):
                        raise Exception(
                            f"n8n-Antwort ist kein JSON-Objekt. Inhalt: {response_text}"
                        )

                    def get_value(source, keys, default=""):
                        for key in keys:
                            if key in source:
                                return source[key]
                        return default

                    # --- DATUMS-NORMALISIERUNG (DD.MM.YYYY -> YYYY-MM-DD) ---
                    raw_date = get_value(raw_data, ["date"])
                    normalized_date = raw_date
                    if raw_date and isinstance(raw_date, str) and "." in raw_date:
                        try:
                            parts = raw_date.split(".")
                            if len(parts) == 3:
                                normalized_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        except Exception:
                            normalized_date = raw_date

                    # --- POSITIONEN ALS ECHTES ARRAY SICHERSTELLEN ---
                    raw_positions = get_value(raw_data, ["positions"], [])
                    clean_positions = []
                    if isinstance(raw_positions, list):
                        for pos in raw_positions:
                            if isinstance(pos, dict):
                                clean_positions.append({
                                    "description": pos.get("description", ""),
                                    "quantity": int(pos.get("quantity", 1)) if pos.get("quantity") else 1,
                                    "unit": pos.get("unit", "Stk."),
                                    "unitPrice": float(pos.get("unitPrice", 0.0)) if pos.get("unitPrice") else 0.0,
                                    "tax": pos.get("tax", "19%")
                                })

                    # --- EXAKTES CAMUNDA-MAPPING ---
                    camunda_variables = {
                        "id": get_value(raw_data, ["id", "invoice_id"]),
                        "supplier": get_value(raw_data, ["supplier", "vendor"]),
                        "amount": float(get_value(raw_data, ["amount", "total_amount"], 0.0)) if get_value(raw_data, ["amount", "total_amount"], None) is not None else 0.0,
                        "date": normalized_date,
                        "positions": clean_positions
                    }
                    
                    print("\n" + "="*40)
                    print("[n8n -> CAMUNDA] DATEN ÜBERGEBEN:")
                    print(json.dumps(camunda_variables, indent=2, ensure_ascii=False))
                    print("="*40 + "\n")
                    
                    return camunda_variables
                    
            except Exception as e: 
                print(f"[FEHLER] n8n Aufruf fehlgeschlagen: {str(e)}") 
                raise BusinessError("AI_EXTRACTION_FAILED", str(e))

    # 2. TASK: Rechnung
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

    # DIE START-AUSGABE
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