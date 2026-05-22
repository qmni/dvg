import asyncio
from pyzeebe import ZeebeClient, create_insecure_channel

async def main():
    channel = create_insecure_channel(hostname="localhost", port=26500)
    client = ZeebeClient(channel)

    # Ersetze 'G8_Digitaler_Rechnungsprozess' durch deine tatsächliche Process ID aus dem Modeler
    process_id = "G8_Digitaler_Rechnungsprozess" 
    
    print(f"Versuche Prozess '{process_id}' zu starten...")
    try:
        await client.run_process(process_id, variables={})
        print("Erfolg! Schau in dein Worker-Terminal oder in Camunda Operate (localhost:8081).")
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    asyncio.run(main())