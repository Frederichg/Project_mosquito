# Project_mosquito
It is the project for linking multiple ESP32 to a central PC via MQTT protocol 
Fadhi and Fred

## Overview
This project implements MQTT communication between multiple ESP32 devices and a Python application with PyQt6 interface.

> **QoS Note:** The SRS specifies QoS 2 (exactly once), but the PubSubClient Arduino library 
> only supports QoS 0 and QoS 1. All code uses **QoS 1** (at least once) as the best available option.

## Project Structure
```
Project_mosquito/
├── snippets/
│   ├── step1/          # One-way communication (ESP32 → PC)
│   ├── step2/          # Bidirectional communication
│   ├── step3/          # PyQt6 GUI interface
│   └── step4/          # GUI with Excel logging
├── wokwi/
│   ├── esp32_1/        # Wokwi simulation - ESP32_1
│   │   ├── diagram.json
│   │   ├── sketch.ino
│   │   ├── libraries.txt
│   │   └── wokwi.toml
│   └── esp32_2/        # Wokwi simulation - ESP32_2
│       ├── diagram.json
│       ├── sketch.ino
│       ├── libraries.txt
│       └── wokwi.toml
├── logs/               # Auto-generated Excel log files
├── requirements.txt    # Python dependencies
├── README.md           # Setup instructions
└── SRS.md              # Software Requirements Specification
```

## Setup Instructions

### 1. Python Environment Setup
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. MQTT Broker Setup
You need an MQTT broker. Options:
- **Local**: Install Mosquitto MQTT broker
- **Cloud**: Use a cloud MQTT service
- **Docker**: Run `docker run -it -p 1883:1883 eclipse-mosquitto`

### 3. ESP32 Setup
1. Install Arduino IDE with ESP32 board support
2. Install required libraries:
   - `WiFi` (built-in)
   - `PubSubClient` for MQTT
   - `EEPROM` (built-in)

### 4. Configuration
- Update WiFi credentials in ESP32 code
- Update MQTT broker IP in both Python and ESP32 code
- Set unique ESP32 names in EEPROM

## Running the Project

### Testing without Hardware (Wokwi Simulator)

You can test the full ESP32 ↔ PC communication without any physical hardware using **Wokwi**.

#### Prerequisites
1. **VS Code** with the [Wokwi extension](https://marketplace.visualstudio.com/items?itemName=wokwi.wokwi-vscode) installed
2. **Wokwi license** (free for personal/educational use — activate via the extension)
3. **MQTT broker** running locally (e.g. Mosquitto on port 1883)

#### Quick Start
```powershell
# 1. Start your local MQTT broker (if using Mosquitto)
mosquitto -v

# 2. In VS Code, open wokwi/esp32_1/ folder
#    Press F1 → "Wokwi: Start Simulator"
#    The simulated ESP32_1 will connect to WiFi and start publishing MQTT messages.

# 3. Open a second VS Code window, open wokwi/esp32_2/
#    Press F1 → "Wokwi: Start Simulator"

# 4. In a terminal, run the Python GUI:
python snippets/step4/pyqt6_interface_with_logging.py
```

The Wokwi simulated ESP32s connect via the `Wokwi-GUEST` WiFi network and reach your PC's MQTT broker through the Wokwi IoT Gateway. You will see:
- Random data strings (L1, L2, FP) arriving in the PyQt6 GUI
- LED blinking in the Wokwi simulator when you send commands from the GUI
- Excel log files created in the `logs/` folder

> **Note:** If the ESP32 can't reach `host.wokwi.internal`, install and run the Wokwi CLI gateway:
> `npm i -g @wokwi/wokwi-cli` then `wokwi-cli gateway`

### Step 1: One-way Communication
```powershell
# Run Python listener
python snippets/step1/mqtt_listener.py

# Upload and run esp32_sender.ino on ESP32
```

### Step 2: Bidirectional Communication
```powershell
# Run Python bidirectional client
python snippets/step2/mqtt_bidirectional.py

# Upload and run esp32_bidirectional.ino on ESP32
```

### Step 3: PyQt6 Interface
```powershell
# Run GUI interface
python snippets/step3/pyqt6_interface.py
```

### Step 4: Interface with Logging
```powershell
# Run GUI with Excel logging
python snippets/step4/pyqt6_interface_with_logging.py
```

## Code Snippets Reference

See `SRS.md` for detailed requirements and snippet descriptions.

## Troubleshooting

### Common Issues
1. **MQTT Connection Failed**: Check broker IP and port
2. **WiFi Connection Issues**: Verify ESP32 WiFi credentials
3. **PyQt6 Import Error**: Ensure virtual environment is activated
4. **Excel Permission Error**: Close Excel files before running