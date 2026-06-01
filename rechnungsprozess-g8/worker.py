import asyncio
import logging
import json
import os
import pika
import sys
from pathlib import Path

import grpc
from dotenv import load_dotenv
from pyzeebe import ZeebeWorker, create_camunda_cloud_channel, BusinessError

try:
    import invoice_pb2
    import invoice_pb2_grpc
except ImportError:
    pass


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO)

INVOICE_HOST = os.getenv("INVOICE_HOST", "localhost")
INVOICE_PORT = os.getenv("INVOICE_PORT", "50052")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

ZEEBE_CLIENT_ID = os.getenv("ZEEBE_CLIENT_ID") or os.getenv("CAMUNDA_CLIENT_ID")
ZEEBE_CLIENT_SECRET = os.getenv("ZEEBE_CLIENT_SECRET") or os.getenv("CAMUNDA_CLIENT_SECRET")
ZEEBE_CLUSTER_ID = os.getenv("ZEEBE_CLUSTER_ID") or os.getenv("CAMUNDA_CLUSTER_ID")
ZEEBE_REGION = os.getenv("ZEEBE_REGION") or os.getenv("CAMUNDA_REGION")

if ZEEBE_CLIENT_ID:
    os.environ["ZEEBE_CLIENT_ID"] = ZEEBE_CLIENT_ID
    os.environ["CAMUNDA_CLIENT_ID"] = ZEEBE_CLIENT_ID

if ZEEBE_CLIENT_SECRET:
    os.environ["ZEEBE_CLIENT_SECRET"] = ZEEBE_CLIENT_SECRET
    os.environ["CAMUNDA_CLIENT_SECRET"] = ZEEBE_CLIENT_SECRET

if ZEEBE_CLUSTER_ID:
    os.environ["ZEEBE_CLUSTER_ID"] = ZEEBE_CLUSTER_ID
    os.environ["CAMUNDA_CLUSTER_ID"] = ZEEBE_CLUSTER_ID

if ZEEBE_REGION:
    os.environ["ZEEBE_REGION"] = ZEEBE_REGION
    os.environ["CAMUNDA_REGION"] = ZEEBE_REGION


async def main():
    print("[DEBUG] ZEEBE_CLIENT_ID geladen:", ZEEBE_CLIENT_ID is not None)
    print("[DEBUG] ZEEBE_CLIENT_SECRET geladen:", ZEEBE_CLIENT_SECRET is not None)
    print("[DEBUG] ZEEBE_CLUSTER_ID geladen:", ZEEBE_CLUSTER_ID)
    print("[DEBUG] ZEEBE_REGION geladen:", ZEEBE_REGION)

    channel = create_camunda_cloud_channel()
    worker = ZeebeWorker(channel)

    @worker.task(task_type="save-invoice")
    async def save_invoice(id=None, supplier=None, amount=None, date=None):
        print("\n[Camunda-Worker] Task 'save-invoice' empfangen.")
        print("[DEBUG] id:", id)
        print("[DEBUG] supplier:", supplier)
        print("[DEBUG] amount:", amount)
        print("[DEBUG] date:", date)

        if not id or not supplier or amount is None or not date:
            fehlermeldung = "Pflichtdaten fehlen: id, supplier, amount oder date"
            print(f"[FEHLER] {fehlermeldung}")
            raise BusinessError(
                error_code="INVOICE_SAVE_FAILED",
                error_message=fehlermeldung
            )

        try:
            grpc_channel = grpc.insecure_channel(f"{INVOICE_HOST}:{INVOICE_PORT}")
            stub = invoice_pb2_grpc.InvoiceServiceStub(grpc_channel)

            rechnung = invoice_pb2.Invoice(
                id=str(id),
                supplier=str(supplier),
                amount=float(amount),
                date=str(date)
            )

            print(f"[gRPC] Sende Rechnung {id} an {INVOICE_HOST}:{INVOICE_PORT} ...")
            antwort = stub.SaveInvoice(rechnung)
            print(f"[gRPC] Antwort vom Invoice Service: {antwort.message}")

            return {
                "invoice_saved": True,
                "invoice_message": antwort.message,
                "invoice_error": None
            }

        except ValueError:
            fehlermeldung = f"amount ist keine gültige Zahl: {amount}"
            print(f"[FEHLER] {fehlermeldung}")
            raise BusinessError(
                error_code="INVOICE_SAVE_FAILED",
                error_message=fehlermeldung
            )

        except grpc.RpcError as e:
            fehlermeldung = e.details() or str(e)
            print(f"[FEHLER] gRPC-Fehler: {fehlermeldung}")
            raise BusinessError(
                error_code="INVOICE_SAVE_FAILED",
                error_message=fehlermeldung
            )

        except Exception as e:
            fehlermeldung = str(e)
            print(f"[FEHLER] Unerwarteter Fehler: {fehlermeldung}")
            raise BusinessError(
                error_code="INVOICE_SAVE_FAILED",
                error_message=fehlermeldung
            )

    @worker.task(task_type="rechnungsdaten-validieren")
    async def task_validation():
        print("[Camunda-Worker] Task 'rechnungsdaten-validieren' empfangen.")

        return {
            "complianceCheckNotwendig": False
        }

    @worker.task(task_type="erp-system")
    async def task_erp():
        print("[Camunda-Worker] Task 'erp-system' empfangen.")

        return {
            "manuelleFreigabeNoetig": False,
            "erp_erfolgreich": True
        }

    # ------------------------------------------------------------
    # TASK: Zahlungsauftrag an Payment Service senden
    # BPMN Task Type: payment-service
    # Nutzt bevorzugt Camunda-Variable id als invoiceId
    # ------------------------------------------------------------

    @worker.task(task_type="send-payment-order")
    async def send_payment_notification(id=None):
        print("\n[Camunda-Worker] Task 'send-payment-order' empfangen.")
        print("[DEBUG] id:", id)

        invoice_id = id or "UNBEKANNT"

        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            rabbit_channel = connection.channel()
            rabbit_channel.queue_declare(queue="payment_queue")

            zahlungs_daten = {
                "invoiceId": invoice_id
            }

            nachricht_json = json.dumps(zahlungs_daten)

            rabbit_channel.basic_publish(
                exchange="",
                routing_key="payment_queue",
                body=nachricht_json
            )

            print(f"[RabbitMQ] Zahlungsauftrag für Rechnung {invoice_id} gesendet.")
            connection.close()

            return {
                "payment_message_sent": True,
                "payment_error": None
            }

        except Exception as e:
            fehlermeldung = str(e)
            print(f"[FEHLER] RabbitMQ nicht erreichbar: {fehlermeldung}")

            return {
                "payment_message_sent": False,
                "payment_error": fehlermeldung
            }

    @worker.task(task_type="zahlung-ausführen")
    async def task_final():
        print("[Camunda-Worker] Task 'zahlung-ausführen' empfangen.")
        print("[Camunda-Worker] Workflow abgeschlossen.")
        return {}

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
        print("\nWorker manuell gestoppt.")