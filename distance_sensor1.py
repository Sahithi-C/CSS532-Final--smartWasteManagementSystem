import lgpio as GPIO
import time
import json
from pathlib import Path
from time import perf_counter as perf_time

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
            time.sleep(0.002)  

            GPIO.gpio_write(self.h, TRIG, 1)
            time.sleep(0.00001)
            GPIO.gpio_write(self.h, TRIG, 0)

            start_time = perf_time()
            timeout = 0.02  

            while GPIO.gpio_read(self.h, ECHO) == 0:
                pulse_start = perf_time()
                if pulse_start - start_time > timeout:
                    return None 

            while GPIO.gpio_read(self.h, ECHO) == 1:
                pulse_end = perf_time()
                if pulse_end - pulse_start > timeout:
                    return None  

            pulse_duration = pulse_end - pulse_start


            if pulse_duration < 0.00005:
                return 0.86 

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
            print("Measurement saved successfully.")
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
                else:
                    print("No valid distance measured (timeout or out of range).")

                time.sleep(120)  

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
