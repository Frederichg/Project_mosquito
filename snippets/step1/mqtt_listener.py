"""
Step 1: Python MQTT Listener (1-way communication)
Listens to MQTT channels from 2 ESP32 devices
Uses Paho MQTT client with QoS 2 (exactly once)
"""

import paho.mqtt.client as mqtt
import time

# MQTT Configuration
MQTT_BROKER = "localhost"  # Change to your MQTT broker address
MQTT_PORT = 1883
MQTT_TOPICS = {
    "ESP32_1": "mosquito/esp32_1/data",
    "ESP32_2": "mosquito/esp32_2/data"
}

# Variables to store data from ESP32s
ESPtoPC1 = ""
ESPtoPC2 = ""

def on_connect(client, userdata, flags, rc):
    """Callback for when the client receives a CONNACK response from the server."""
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to both ESP32 topics with QoS 2
        for esp_name, topic in MQTT_TOPICS.items():
            client.subscribe(topic, qos=2)
            print(f"Subscribed to {topic}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """Callback for when a PUBLISH message is received from the server."""
    global ESPtoPC1, ESPtoPC2
    
    topic = msg.topic
    message = msg.payload.decode()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"[{timestamp}] Received from {topic}: {message}")
    
    # Store message in appropriate variable based on topic
    if topic == MQTT_TOPICS["ESP32_1"]:
        ESPtoPC1 = message
        print(f"ESPtoPC1 updated: {ESPtoPC1}")
    elif topic == MQTT_TOPICS["ESP32_2"]:
        ESPtoPC2 = message
        print(f"ESPtoPC2 updated: {ESPtoPC2}")

def on_disconnect(client, userdata, rc):
    """Callback for when the client disconnects from the server."""
    print("Disconnected from MQTT Broker")

def main():
    """Main function to start MQTT listener"""
    print("Starting MQTT Listener for ESP32 devices...")
    
    # Create MQTT client
    client = mqtt.Client()
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        # Connect to broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Start the loop
        print("Listening for messages... Press Ctrl+C to exit")
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        client.disconnect()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
