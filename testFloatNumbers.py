from awscrt import mqtt, http
from awsiot import mqtt_connection_builder
import sys
import threading
import time
import json
import random

endpoint = "myEndPoint"
client_id = "myClient"
topic = "myTopic"

received_message = False
received_event = threading.Event()

def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))
    global received_message
    received_message = True

    try:
        data = json.loads(payload)
        if isinstance(data, list):
            print(f"Received numbers: {data}")
        else:
            print("Didn't receive numbers")
    except json.JSONDecodeError:
        print("Received invalid JSON message.")

    received_event.set()

mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=endpoint,
        cert_filepath="myFilePath",
        pri_key_filepath="myPrivateKey",
        ca_filepath="myCaFilePath",
        client_id=client_id,
        clean_session=False)

print(f"Connecting to endpoint {endpoint} with client ID '{client_id}'...")

connect_future = mqtt_connection.connect()
connect_future.result()
print("Connected!")

print("Subscribing to topic '{}'...".format(topic))
subscribe_future, packet_id = mqtt_connection.subscribe(
    topic=topic,
    qos=mqtt.QoS.AT_LEAST_ONCE,
    callback=on_message_received)
subscribe_result = subscribe_future.result()
print("Subscribed with {}".format(str(subscribe_result['qos'])))


random_number = round(random.uniform(1.0, 100000.0), 2)

print(f"Generated number: {random_number:.2f}")

print(f"Publishing {random_number} to topic '{topic}'")
mqtt_connection.publish(
    topic=topic,
    payload=json.dumps(random_number),
    qos=mqtt.QoS.AT_LEAST_ONCE)


received_event.wait(timeout=5) 

if received_message:
    print("Message successfully sent and received.")
else:
    print("No message received within timeout period.")

print("Disconnecting...")
disconnect_future = mqtt_connection.disconnect()
disconnect_future.result()
print("Disconnected!")
