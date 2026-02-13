import os
from azure.storage.queue import QueueClient

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
queue_name = "orders-queue"

def enqueue_order(order_id):
    try:
        if not connection_string:
            print("AZURE_STORAGE_CONNECTION_STRING not set")
            return
        queue_client = QueueClient.from_connection_string(
            conn_str=connection_string,
            queue_name=queue_name
        )
        queue_client.send_message(str(order_id))
        print(f"Order {order_id} enqueued successfully")
    except Exception as e:
        print(f"Error enqueuing order: {e}")

