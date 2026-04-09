import grpc
import invoice_pb2
import invoice_pb2_grpc

channel = grpc.insecure_channel("localhost:50052")
stub = invoice_pb2_grpc.InvoiceServiceStub(channel)

try:
    response = stub.SaveInvoice(
        invoice_pb2.Invoice(
            id="",
            supplier="",
            amount=100,
            date=""
        )
    )
    print("Antwort:", response.message)

except grpc.RpcError as e:
    print("gRPC-FEHLER")
    print("Code:", e.code())
    print("Details:", e.details())