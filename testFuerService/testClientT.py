import grpc
import gRPC.invoice_pb2 as invoice_pb2
import gRPC.invoice_pb2_grpc as invoice_pb2_grpc

channel = grpc.insecure_channel("localhost:50052")
stub = invoice_pb2_grpc.InvoiceServiceStub(channel)

try:
    response = stub.SaveInvoice(
        invoice_pb2.Invoice(
            id="1002",
            supplier="Beispiel-Lieferant",
            amount=100,
            date="2024-06-01"
        )
    )
    print("Antwort:", response.message)

except grpc.RpcError as e:
    print("gRPC-FEHLER")
    print("Code:", e.code())
    print("Details:", e.details())