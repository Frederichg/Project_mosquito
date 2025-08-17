"""
Step 3: PyQt6 Interface for MQTT Communication
Minimal GUI with 2 boxes for ESP32 devices
Each box shows ESP32 name, last received data, and command entry
"""

import sys
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QLabel, QLineEdit, QGroupBox, QPushButton,
                            QTextEdit, QGridLayout)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import paho.mqtt.client as mqtt

# MQTT Configuration
MQTT_BROKER = "localhost"  # Change to your MQTT broker address
MQTT_PORT = 1883

class MQTTWorker(QThread):
    """MQTT worker thread to handle communication without blocking UI"""
    data_received = pyqtSignal(str, str)  # esp_name, data
    connection_status = pyqtSignal(bool)  # connected/disconnected
    
    def __init__(self):
        super().__init__()
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.connected = False
        self.running = True
        
        # MQTT Topics
        self.listen_topics = {
            "ESP32_1": "mosquito/esp32_1/data",
            "ESP32_2": "mosquito/esp32_2/data"
        }
        
        self.send_topics = {
            "ESP32_1": "mosquito/esp32_1/command",
            "ESP32_2": "mosquito/esp32_2/command"
        }

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.connection_status.emit(True)
            # Subscribe to both ESP32 topics
            for esp_name, topic in self.listen_topics.items():
                client.subscribe(topic, qos=2)
        else:
            self.connected = False
            self.connection_status.emit(False)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        message = msg.payload.decode()
        
        # Determine which ESP32 sent the message
        for esp_name, esp_topic in self.listen_topics.items():
            if topic == esp_topic:
                self.data_received.emit(esp_name, message)
                break

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.connection_status.emit(False)

    def run(self):
        """Connect to MQTT and start loop"""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_forever()
        except Exception as e:
            print(f"MQTT connection error: {e}")

    def send_command(self, esp_name, command):
        """Send command to specific ESP32"""
        if self.connected and esp_name in self.send_topics:
            topic = self.send_topics[esp_name]
            self.client.publish(topic, str(command), qos=2)
            return True
        return False

    def stop(self):
        """Stop the MQTT worker"""
        self.running = False
        if self.connected:
            self.client.disconnect()
        self.quit()

class ESP32Widget(QGroupBox):
    """Widget representing one ESP32 device"""
    
    def __init__(self, esp_name, mqtt_worker):
        super().__init__(f"ESP32 Device: {esp_name}")
        self.esp_name = esp_name
        self.mqtt_worker = mqtt_worker
        self.last_data = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # ESP32 Name Label
        self.name_label = QLabel(f"Name: {self.esp_name}")
        self.name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.name_label)
        
        # Last received data display
        data_layout = QHBoxLayout()
        data_layout.addWidget(QLabel("Last Data:"))
        self.data_display = QLabel("No data received")
        self.data_display.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
        data_layout.addWidget(self.data_display)
        layout.addLayout(data_layout)
        
        # Command entry
        command_layout = QHBoxLayout()
        command_layout.addWidget(QLabel("LED Blinks:"))
        self.command_entry = QLineEdit()
        self.command_entry.setPlaceholderText("Enter number (1-20)")
        self.command_entry.editingFinished.connect(self.send_command)
        command_layout.addWidget(self.command_entry)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_command)
        command_layout.addWidget(self.send_button)
        
        layout.addLayout(command_layout)
        
        # Status indicator
        self.status_label = QLabel("Status: Waiting for data...")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
    def update_data(self, data):
        """Update the displayed data from ESP32"""
        self.last_data = data
        timestamp = time.strftime("%H:%M:%S")
        self.data_display.setText(f"{data} ({timestamp})")
        self.status_label.setText(f"Last update: {timestamp}")
        
    def send_command(self):
        """Send LED blink command to ESP32"""
        try:
            command_text = self.command_entry.text().strip()
            if command_text:
                command = int(command_text)
                if 1 <= command <= 20:
                    if self.mqtt_worker.send_command(self.esp_name, command):
                        self.status_label.setText(f"Sent command: {command} blinks")
                        self.command_entry.clear()
                    else:
                        self.status_label.setText("Failed to send command (not connected)")
                else:
                    self.status_label.setText("Invalid number (1-20 allowed)")
        except ValueError:
            self.status_label.setText("Invalid input (numbers only)")

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.mqtt_worker = None
        self.setup_ui()
        self.setup_mqtt()
        
    def setup_ui(self):
        self.setWindowTitle("ESP32 MQTT Controller")
        self.setGeometry(100, 100, 800, 400)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("ESP32 MQTT Communication Interface")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("padding: 10px; background-color: #e0e0e0;")
        main_layout.addWidget(title_label)
        
        # Connection status
        self.connection_label = QLabel("MQTT Status: Connecting...")
        self.connection_label.setStyleSheet("padding: 5px; color: #666;")
        main_layout.addWidget(self.connection_label)
        
        # ESP32 widgets layout
        esp_layout = QHBoxLayout()
        
        # Create ESP32 widgets (will be initialized after MQTT worker is created)
        self.esp32_widgets = {}
        
        esp_layout.addStretch()
        main_layout.addLayout(esp_layout)
        main_layout.addStretch()
        
        central_widget.setLayout(main_layout)
        
        # Store layout reference for later use
        self.esp_layout = esp_layout
        
    def setup_mqtt(self):
        """Initialize MQTT worker and ESP32 widgets"""
        # Create and start MQTT worker
        self.mqtt_worker = MQTTWorker()
        self.mqtt_worker.data_received.connect(self.on_data_received)
        self.mqtt_worker.connection_status.connect(self.on_connection_status)
        self.mqtt_worker.start()
        
        # Create ESP32 widgets
        for esp_name in ["ESP32_1", "ESP32_2"]:
            widget = ESP32Widget(esp_name, self.mqtt_worker)
            self.esp32_widgets[esp_name] = widget
            self.esp_layout.insertWidget(self.esp_layout.count() - 1, widget)
    
    def on_data_received(self, esp_name, data):
        """Handle data received from ESP32"""
        if esp_name in self.esp32_widgets:
            self.esp32_widgets[esp_name].update_data(data)
    
    def on_connection_status(self, connected):
        """Handle MQTT connection status changes"""
        if connected:
            self.connection_label.setText("MQTT Status: Connected")
            self.connection_label.setStyleSheet("padding: 5px; color: green;")
        else:
            self.connection_label.setText("MQTT Status: Disconnected")
            self.connection_label.setStyleSheet("padding: 5px; color: red;")
    
    def closeEvent(self, event):
        """Handle application close"""
        if self.mqtt_worker:
            self.mqtt_worker.stop()
            self.mqtt_worker.wait()
        event.accept()

def main():
    """Main function to start the PyQt6 application"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
