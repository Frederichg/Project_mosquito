"""
Step 4: PyQt6 Interface with Excel Logging
Enhanced interface that logs all MQTT communication to Excel files
Creates separate log files for each ESP32 device
"""

import sys
import time
import os
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QLabel, QLineEdit, QGroupBox, QPushButton,
                            QTextEdit, QGridLayout, QFileDialog, QMessageBox)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import paho.mqtt.client as mqtt
import pandas as pd

# MQTT Configuration
MQTT_BROKER = "localhost"  # Change to your MQTT broker address
MQTT_PORT = 1883

class MQTTWorker(QThread):
    """MQTT worker thread to handle communication without blocking UI"""
    data_received = pyqtSignal(str, str)  # esp_name, data
    connection_status = pyqtSignal(bool)  # connected/disconnected
    command_sent = pyqtSignal(str, str)  # esp_name, command
    
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
            if self.client.publish(topic, str(command), qos=2):
                self.command_sent.emit(esp_name, str(command))
                return True
        return False

    def stop(self):
        """Stop the MQTT worker"""
        self.running = False
        if self.connected:
            self.client.disconnect()
        self.quit()

class Logger:
    """Excel logger for MQTT communication"""
    
    def __init__(self, esp_name):
        self.esp_name = esp_name
        self.log_file = None
        self.log_data = []
        self.setup_log_file()
        
    def setup_log_file(self):
        """Create log file with header"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mqtt_log_{self.esp_name}_{timestamp}.xlsx"
        
        # Create logs directory if it doesn't exist
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        self.log_file = os.path.join(logs_dir, filename)
        
        # Create initial DataFrame with header
        header_data = {
            'Timestamp': [],
            'ESP32_Name': [],
            'Direction': [],  # 'Received' or 'Sent'
            'Message_Type': [],  # 'Data' or 'Command'
            'Message': [],
            'Notes': []
        }
        
        df = pd.DataFrame(header_data)
        df.to_excel(self.log_file, index=False)
        
    def log_received_data(self, data):
        """Log data received from ESP32"""
        self.log_entry('Received', 'Data', data, 'Data from ESP32')
        
    def log_sent_command(self, command):
        """Log command sent to ESP32"""
        self.log_entry('Sent', 'Command', command, 'Command to ESP32')
        
    def log_entry(self, direction, message_type, message, notes):
        """Add entry to log and save to Excel"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        entry = {
            'Timestamp': timestamp,
            'ESP32_Name': self.esp_name,
            'Direction': direction,
            'Message_Type': message_type,
            'Message': message,
            'Notes': notes
        }
        
        self.log_data.append(entry)
        self.save_to_excel()
        
    def save_to_excel(self):
        """Save current log data to Excel file"""
        try:
            df = pd.DataFrame(self.log_data)
            df.to_excel(self.log_file, index=False)
        except Exception as e:
            print(f"Error saving log file: {e}")

class ESP32Widget(QGroupBox):
    """Widget representing one ESP32 device with logging"""
    
    def __init__(self, esp_name, mqtt_worker):
        super().__init__(f"ESP32 Device: {esp_name}")
        self.esp_name = esp_name
        self.mqtt_worker = mqtt_worker
        self.last_data = ""
        self.logger = Logger(esp_name)
        self.communication_started = False
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # ESP32 Name Label
        self.name_label = QLabel(f"Name: {self.esp_name}")
        self.name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.name_label)
        
        # Log file info
        self.log_info_label = QLabel(f"Log: {os.path.basename(self.logger.log_file)}")
        self.log_info_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(self.log_info_label)
        
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
        
        # Log counter
        self.log_counter_label = QLabel("Log entries: 0")
        self.log_counter_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(self.log_counter_label)
        
        self.setLayout(layout)
        
    def update_data(self, data):
        """Update the displayed data from ESP32 and log it"""
        self.last_data = data
        timestamp = time.strftime("%H:%M:%S")
        self.data_display.setText(f"{data} ({timestamp})")
        self.status_label.setText(f"Last update: {timestamp}")
        
        # Start logging when first communication is received
        if not self.communication_started:
            self.communication_started = True
            self.status_label.setText(f"Communication started - logging active")
        
        # Log the received data
        self.logger.log_received_data(data)
        self.update_log_counter()
        
    def send_command(self):
        """Send LED blink command to ESP32 and log it"""
        try:
            command_text = self.command_entry.text().strip()
            if command_text:
                command = int(command_text)
                if 1 <= command <= 20:
                    if self.mqtt_worker.send_command(self.esp_name, command):
                        self.status_label.setText(f"Sent command: {command} blinks")
                        self.command_entry.clear()
                        # Log the sent command
                        self.logger.log_sent_command(command)
                        self.update_log_counter()
                    else:
                        self.status_label.setText("Failed to send command (not connected)")
                else:
                    self.status_label.setText("Invalid number (1-20 allowed)")
        except ValueError:
            self.status_label.setText("Invalid input (numbers only)")
            
    def update_log_counter(self):
        """Update the log entry counter"""
        count = len(self.logger.log_data)
        self.log_counter_label.setText(f"Log entries: {count}")

class MainWindow(QMainWindow):
    """Main application window with logging capabilities"""
    
    def __init__(self):
        super().__init__()
        self.mqtt_worker = None
        self.setup_ui()
        self.setup_mqtt()
        
    def setup_ui(self):
        self.setWindowTitle("ESP32 MQTT Controller with Logging")
        self.setGeometry(100, 100, 900, 500)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("ESP32 MQTT Communication Interface with Excel Logging")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("padding: 10px; background-color: #e0e0e0;")
        main_layout.addWidget(title_label)
        
        # Connection status
        self.connection_label = QLabel("MQTT Status: Connecting...")
        self.connection_label.setStyleSheet("padding: 5px; color: #666;")
        main_layout.addWidget(self.connection_label)
        
        # Log directory info
        logs_dir = os.path.abspath("logs")
        log_dir_label = QLabel(f"Log files saved to: {logs_dir}")
        log_dir_label.setStyleSheet("padding: 5px; color: #666; font-size: 10px;")
        main_layout.addWidget(log_dir_label)
        
        # ESP32 widgets layout
        esp_layout = QHBoxLayout()
        
        # Create ESP32 widgets (will be initialized after MQTT worker is created)
        self.esp32_widgets = {}
        
        esp_layout.addStretch()
        main_layout.addLayout(esp_layout)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        self.open_logs_button = QPushButton("Open Logs Folder")
        self.open_logs_button.clicked.connect(self.open_logs_folder)
        controls_layout.addWidget(self.open_logs_button)
        
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)
        
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
        self.mqtt_worker.command_sent.connect(self.on_command_sent)
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
    
    def on_command_sent(self, esp_name, command):
        """Handle command sent to ESP32"""
        # Command logging is handled in the ESP32Widget
        pass
    
    def on_connection_status(self, connected):
        """Handle MQTT connection status changes"""
        if connected:
            self.connection_label.setText("MQTT Status: Connected")
            self.connection_label.setStyleSheet("padding: 5px; color: green;")
        else:
            self.connection_label.setText("MQTT Status: Disconnected")
            self.connection_label.setStyleSheet("padding: 5px; color: red;")
    
    def open_logs_folder(self):
        """Open the logs folder in file explorer"""
        logs_dir = os.path.abspath("logs")
        if os.path.exists(logs_dir):
            if sys.platform == "win32":
                os.startfile(logs_dir)
            elif sys.platform == "darwin":
                os.system(f"open {logs_dir}")
            else:
                os.system(f"xdg-open {logs_dir}")
        else:
            QMessageBox.information(self, "Info", "Logs folder will be created when communication starts.")
    
    def closeEvent(self, event):
        """Handle application close"""
        if self.mqtt_worker:
            self.mqtt_worker.stop()
            self.mqtt_worker.wait()
        event.accept()

def main():
    """Main function to start the PyQt6 application with logging"""
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
