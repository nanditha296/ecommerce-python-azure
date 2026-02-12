from azure.storage.queue import QueueClient
import os

# Create a queue client using connection string from environment variables
queue_client = QueueClient.from_connection_string(
    conn_str=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
    queue_name="orders-queue"
)

def enqueue_order(order_id: int):
    # Convert order ID to string before sending
    queue_client.send_message(str(order_id))
    print(f"Order {order_id} placed into queue")
