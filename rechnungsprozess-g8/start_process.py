import asyncio
from pyzeebe import ZeebeClient, create_camunda_cloud_channel
from config import CAMUNDA_CONFIG

async def main():
    channel = create_camunda_cloud_channel(
        client_id=CAMUNDA_CONFIG["client_id"],
        client_secret=CAMUNDA_CONFIG["client_secret"],
        cluster_id=CAMUNDA_CONFIG["cluster_id"],
        region=CAMUNDA_CONFIG["region"]
    )
    client = ZeebeClient(channel)

    process_id = "G8_Digitaler_Rechnungsprozess" 
    
    print(f"Sende Start-Signal für '{process_id}' an die Camunda SaaS Cloud...")
    
    # Test-Daten für deinen gRPC-Server
    test_variablen = {
        "rechnungsNummer": "TEAM8-SAAS-999",
        "lieferant": "SaaS Testlieferant",
        "betrag": 1250.00,
        "datum": "2026-05-27"
    }

    try:
        await client.run_process(process_id, variables=test_variablen)
        print("\n[ERFOLG] Prozessinstanz in der Cloud gestartet!")
        print("Wechsle jetzt in dein 'worker.py' Terminal, um das Protokoll zu sehen.")
    except Exception as e:
        print(f"\n[FEHLER] Konnte Prozess nicht starten: {e}")
        print("Hinweis: Überprüfe, ob das Diagramm mit der ID 'G8_Digitaler_Rechnungsprozess' im Web-Modeler deployed wurde.")

if __name__ == "__main__":
    asyncio.run(main())