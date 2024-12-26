from awscrt import mqtt
from awsiot import mqtt_connection_builder
import json
import time
from pathlib import Path

ENDPOINT = "myEndPoint"  
CLIENT_ID = "myClient"
TOPIC = "myTopic"
CERT_PATH = "myFile" 
KEY_PATH = "myPrivateKey"  
CA_PATH = "myCAFile" 

SHARED_FILE = "sensor_data.json"

class AWSPublisher:
    def __init__(self):
        self.mqtt_connection = self.setup_aws_connection()
        self.last_published_time = 0

    def setup_aws_connection(self):
        return mqtt_connection_builder.mtls_from_path(
            endpoint=ENDPOINT,
            cert_filepath=CERT_PATH,
            pri_key_filepath=KEY_PATH,
            ca_filepath=CA_PATH,
            client_id=CLIENT_ID,
            clean_session=False
        )

    def connect(self):
        print(f"Connecting to AWS IoT Core...")
        connect_future = self.mqtt_connection.connect()
        connect_future.result()
        print("Connected to AWS IoT Core!")

    def read_sensor_data(self):
        try:
            if Path(SHARED_FILE).exists():
                with open(SHARED_FILE, 'r') as f:
                    data = json.load(f)
                    return data
        except Exception as e:
            print(f"Error reading sensor data: {e}")
        return None

    def publish_measurement(self, data):
        try:
            message = {
                "distance_cm": data["distance"],
                "timestamp": data["timestamp"],
                "bin_id": "bin1"
            }
            
            self.mqtt_connection.publish(
                topic=TOPIC,
                payload=json.dumps(message),
                qos=mqtt.QoS.AT_LEAST_ONCE
            )
            print(f"Published measurement: {message}")
            
        except Exception as e:
            print(f"Error publishing measurement: {e}")

    def run(self):
        self.connect()
        print("Starting AWS IoT publisher...")
        
        try:
            while True:
                data = self.read_sensor_data()
                
                if data and data["timestamp"] > self.last_published_time:
                    self.publish_measurement(data)
                    self.last_published_time = data["timestamp"]
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("Publisher stopped by user")
            self.cleanup()
        except Exception as e:
            print(f"Error in publisher loop: {e}")
            self.cleanup()

    def cleanup(self):
        try:
            self.mqtt_connection.disconnect()
            print("Disconnected from AWS IoT Core")
        except Exception as e:
            print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    publisher = AWSPublisher()
    publisher.run()
