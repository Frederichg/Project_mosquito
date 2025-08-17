"""
Step 2: Python MQTT Bidirectional Communication
Listens to and sends MQTT messages to 2 ESP32 devices
Implements both ESPtoPC and PCtoESP communication
"""

import paho.mqtt.client as mqtt
import time
import threading

# MQTT Configuration
MQTT_BROKER = "localhost"  # Change to your MQTT broker address
MQTT_PORT = 1883

# MQTT Topics
LISTEN_TOPICS = {
    "ESP32_1": "mosquito/esp32_1/data",
    "ESP32_2": "mosquito/esp32_2/data"
}

SEND_TOPICS = {
    "ESP32_1": "mosquito/esp32_1/command",
    "ESP32_2": "mosquito/esp32_2/command"
}

# Variables to store data from ESP32s
ESPtoPC1 = ""
ESPtoPC2 = ""

class MQTTManager:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the client receives a CONNACK response from the server."""
        if rc == 0:
            print("Connected to MQTT Broker!")
            self.connected = True
            # Subscribe to both ESP32 topics with QoS 2
            for esp_name, topic in LISTEN_TOPICS.items():
                client.subscribe(topic, qos=2)
                print(f"Subscribed to {topic}")
        else:
            print(f"Failed to connect, return code {rc}")
            self.connected = False

    def on_message(self, client, userdata, msg):
        """Callback for when a PUBLISH message is received from the server."""
        global ESPtoPC1, ESPtoPC2
        
        topic = msg.topic
        message = msg.payload.decode()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"[{timestamp}] Received from {topic}: {message}")
        
        # Store message in appropriate variable based on topic
        if topic == LISTEN_TOPICS["ESP32_1"]:
            ESPtoPC1 = message
            print(f"ESPtoPC1 updated: {ESPtoPC1}")
        elif topic == LISTEN_TOPICS["ESP32_2"]:
            ESPtoPC2 = message
            print(f"ESPtoPC2 updated: {ESPtoPC2}")

    def on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the server."""
        print("Disconnected from MQTT Broker")
        self.connected = False

    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()

    def send_command_to_esp32(self, esp_name, command):
        """Send command to specific ESP32"""
        if not self.connected:
            print("Not connected to MQTT broker")
            return False
        
        if esp_name not in SEND_TOPICS:
            print(f"Unknown ESP32: {esp_name}")
            return False
        
        topic = SEND_TOPICS[esp_name]
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # Publish with QoS 2 (exactly once)
            result = self.client.publish(topic, str(command), qos=2)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[{timestamp}] Sent to {esp_name} ({topic}): {command}")
                return True
            else:
                print(f"Failed to send command to {esp_name}")
                return False
        except Exception as e:
            print(f"Error sending command: {e}")
            return False

def user_interface(mqtt_manager):
    """Simple command line interface for sending commands"""
    print("\n=== MQTT Command Interface ===")
    print("Commands:")
    print("  1 <number> - Send LED blink command to ESP32_1")
    print("  2 <number> - Send LED blink command to ESP32_2")
    print("  status - Show current ESP32 data")
    print("  quit - Exit program")
    print("=====================================\n")
    
    while True:
        try:
            user_input = input("Enter command: ").strip().lower()
            
            if user_input == "quit":
                break
            elif user_input == "status":
                print(f"ESPtoPC1: {ESPtoPC1}")
                print(f"ESPtoPC2: {ESPtoPC2}")
            elif user_input.startswith("1 "):
                try:
                    number = int(user_input.split()[1])
                    mqtt_manager.send_command_to_esp32("ESP32_1", number)
                except (IndexError, ValueError):
                    print("Invalid format. Use: 1 <number>")
            elif user_input.startswith("2 "):
                try:
                    number = int(user_input.split()[1])
                    mqtt_manager.send_command_to_esp32("ESP32_2", number)
                except (IndexError, ValueError):
                    print("Invalid format. Use: 2 <number>")
            else:
                print("Unknown command. Type 'quit' to exit.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main function to start MQTT bidirectional communication"""
    print("Starting MQTT Bidirectional Communication...")
    
    # Create MQTT manager
    mqtt_manager = MQTTManager()
    
    try:
        # Connect to broker
        if not mqtt_manager.connect():
            print("Failed to connect to MQTT broker")
            return
        
        # Wait a moment for connection to establish
        time.sleep(2)
        
        print("MQTT connection established. Starting user interface...")
        
        # Start user interface
        user_interface(mqtt_manager)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        mqtt_manager.disconnect()

if __name__ == "__main__":
    main()
