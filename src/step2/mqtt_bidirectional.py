"""
Step 2: Python MQTT Bidirectional Communication
Listens to and sends MQTT messages to 2 ESP32 devices
Implements both ESPtoPC and PCtoESP communication

Note: QoS 2 is supported by paho-mqtt but NOT by PubSubClient on ESP32.
      Effective QoS is the minimum of publisher and subscriber, so QoS 1 is used.
"""

import paho.mqtt.client as mqtt
import time
import threading

# MQTT Configuration
MQTT_BROKER = "test.mosquitto.org"  # Public broker for initial integration tests
MQTT_PORT = 1883
MQTT_NAMESPACE = "udem/pfh3221/mosquito"

# Auto round-trip behavior: switch state from ESP triggers a command back to ESP
AUTO_TRIGGER_FROM_SWITCH = True
AUTO_LED_ON_COMMAND = "ON"
AUTO_LED_OFF_COMMAND = "OFF"

# MQTT Topics
LISTEN_TOPICS = {
    "ESP32_1": f"{MQTT_NAMESPACE}/esp32_1/data",
    "ESP32_2": f"{MQTT_NAMESPACE}/esp32_2/data"
}

SEND_TOPICS = {
    "ESP32_1": f"{MQTT_NAMESPACE}/esp32_1/command",
    "ESP32_2": f"{MQTT_NAMESPACE}/esp32_2/command"
}

# Variables to store data from ESP32s (with thread lock)
_data_lock = threading.Lock()
ESPtoPC1 = ""
ESPtoPC2 = ""

class MQTTManager:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.connected = False
        self.last_switch_state = {"ESP32_1": "RELEASED", "ESP32_2": "RELEASED"}

    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the client receives a CONNACK response from the server."""
        if rc == 0:
            print("Connected to MQTT Broker!")
            self.connected = True
            # Subscribe to both ESP32 topics with QoS 1
            for esp_name, topic in LISTEN_TOPICS.items():
                client.subscribe(topic, qos=1)
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
        with _data_lock:
            if topic == LISTEN_TOPICS["ESP32_1"]:
                ESPtoPC1 = message
                print(f"ESPtoPC1 updated: {ESPtoPC1}")
                self.handle_switch_round_trip("ESP32_1", message)
            elif topic == LISTEN_TOPICS["ESP32_2"]:
                ESPtoPC2 = message
                print(f"ESPtoPC2 updated: {ESPtoPC2}")
                self.handle_switch_round_trip("ESP32_2", message)

    def handle_switch_round_trip(self, esp_name, message):
        """Send command back when switch state is reported by ESP32."""
        if not AUTO_TRIGGER_FROM_SWITCH:
            return

        normalized = message.strip().upper()
        if normalized not in ("PRESSED", "RELEASED"):
            return

        previous = self.last_switch_state.get(esp_name, "RELEASED")
        self.last_switch_state[esp_name] = normalized

        # Trigger only on state changes to avoid repeated commands from periodic status updates.
        if previous != normalized:
            if normalized == "PRESSED":
                print(f"Switch PRESSED on {esp_name}, sending LED command: {AUTO_LED_ON_COMMAND}")
                self.send_command_to_esp32(esp_name, AUTO_LED_ON_COMMAND)
            else:
                print(f"Switch RELEASED on {esp_name}, sending LED command: {AUTO_LED_OFF_COMMAND}")
                self.send_command_to_esp32(esp_name, AUTO_LED_OFF_COMMAND)

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
            # Publish with QoS 1 (at least once)
            result = self.client.publish(topic, str(command), qos=1)
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
    print("  1 on/off - Set LED state on ESP32_1")
    print("  2 on/off - Set LED state on ESP32_2")
    print("  1 or 2 - Select ESP, then you will be asked for on/off")
    print(f"  auto switch-trigger is {'ON' if AUTO_TRIGGER_FROM_SWITCH else 'OFF'}")
    print("  status - Show current ESP32 data")
    print("  quit - Exit program")
    print("=====================================\n")
    
    while True:
        try:
            user_input = input("Enter command: ").strip().lower()
            
            if user_input == "quit":
                break
            elif user_input == "status":
                with _data_lock:
                    print(f"ESPtoPC1: {ESPtoPC1}")
                    print(f"ESPtoPC2: {ESPtoPC2}")
            elif user_input.startswith("1"):
                try:
                    parts = user_input.split()
                    if len(parts) == 1:
                        command = input("LED command for ESP32_1 (on/off): ").strip().upper()
                    else:
                        command = parts[1].upper()
                    if command not in ("ON", "OFF"):
                        raise ValueError("Command must be on or off")
                    mqtt_manager.send_command_to_esp32("ESP32_1", command)
                except (IndexError, ValueError):
                    print("Invalid format. Use: 1 on/off or 1")
            elif user_input.startswith("2"):
                try:
                    parts = user_input.split()
                    if len(parts) == 1:
                        command = input("LED command for ESP32_2 (on/off): ").strip().upper()
                    else:
                        command = parts[1].upper()
                    if command not in ("ON", "OFF"):
                        raise ValueError("Command must be on or off")
                    mqtt_manager.send_command_to_esp32("ESP32_2", command)
                except (IndexError, ValueError):
                    print("Invalid format. Use: 2 on/off or 2")
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
