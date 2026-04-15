import grpc
from concurrent import futures

import invoice_pb2
import invoice_pb2_grpc

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
    
    server.add_insecure_port("[::]:50052")
    server.start()

    print("gRPC-Server läuft auf Port 50052...")
    
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
