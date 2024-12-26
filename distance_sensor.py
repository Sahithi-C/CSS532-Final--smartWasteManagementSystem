import lgpio as GPIO
import time
import json
from pathlib import Path

TRIG = 23  
ECHO = 24 

SHARED_FILE = "sensor_data.json"

class DistanceSensor:
    def __init__(self):
        self.h = GPIO.gpiochip_open(0)
        GPIO.gpio_claim_output(self.h, TRIG)
        GPIO.gpio_claim_input(self.h, ECHO)

    def get_distance(self):
        try:
            GPIO.gpio_write(self.h, TRIG, 0)
            time.sleep(0.1)

            GPIO.gpio_write(self.h, TRIG, 1)
            time.sleep(0.00001)
            GPIO.gpio_write(self.h, TRIG, 0)
            
            while GPIO.gpio_read(self.h, ECHO) == 0:
                pulse_start = time.time()
            
            while GPIO.gpio_read(self.h, ECHO) == 1:
                pulse_end = time.time()
            
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150
            return round(distance, 2)
        
        except Exception as e:
            print(f"Error measuring distance: {e}")
            return None

    def save_measurement(self, distance):
        data = {
            "distance": distance,
            "timestamp": time.time()
        }
        try:
            with open(SHARED_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving measurement: {e}")

    def run(self):
        print("Starting distance measurements...")
        try:
            while True:
                distance = self.get_distance()
                
                if distance is not None:
                    print(f"Measured Distance = {distance:.2f} cm")
                    self.save_measurement(distance)
                
                time.sleep(300)  
                
        except KeyboardInterrupt:
            print("Measurement stopped by User")
            self.cleanup()
        except Exception as e:
            print(f"Error in measurement loop: {e}")
            self.cleanup()

    def cleanup(self):
        GPIO.gpiochip_close(self.h)
        print("Cleaned up GPIO resources")

if __name__ == '__main__':
    sensor = DistanceSensor()
    sensor.run()