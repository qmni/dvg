import grpc
from concurrent import futures
from shared import invoice_pb2
from shared import invoice_pb2_grpc
from dotenv import load_dotenv
import os

load_dotenv()

host = os.getenv("HOST")
port = int(os.getenv("INVOICE_PORT"))

# Speicher
invoices = []


class InvoiceService(invoice_pb2_grpc.InvoiceServiceServicer):

    def SaveInvoice(self, request, context):
        print("SaveInvoice wurde aufgerufen")

        if request.id.strip() == "":
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("id darf nicht leer sein.")
            return invoice_pb2.Response()

        if request.supplier.strip() == "":
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("supplier darf nicht leer sein.")
            return invoice_pb2.Response()

        if request.amount <= 0:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("amount muss größer als 0 sein.")
            return invoice_pb2.Response()

        if request.date.strip() == "":
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("date darf nicht leer sein.")
            return invoice_pb2.Response()
            
        invoice = {
            "id": request.id,
            "supplier": request.supplier,
            "amount": request.amount,
            "date": request.date
            }
            
        invoices.append(invoice)

        print("Rechnung gespeichert:")
        print(invoice)
            
        return invoice_pb2.Response(
             message=f"Rechnung {request.id} wurde gespeichert."
        )
        
        

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    invoice_pb2_grpc.add_InvoiceServiceServicer_to_server(InvoiceService(), server)
    
    server.add_insecure_port(f"{host}:{port}")
    server.start()

    print("gRPC-Server läuft auf Port 50052...")
    
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
