Software requirement specification

# Project general description
This project is to write a code for a central PC-windows computer to communicate back and forth with multiple ESP32
The project will use MQTT protocol for the communication back and forth
    MQTT-Quality of service No 2: exactly once
On the PC there will be a program made in python 3.11 that will do the MQTT to the user interface
The Python program will use the 'Paho' toolbox
The interface will be 'PyQt6'

On the ESP32 side their EPROMM will be set with a unique name
    This is to avoid any confusion among the ESP32, at the end there maybe 16 to 20 ESP32 running at the same time.
For programming and debuging we can now simply put a program on them that will randomly send string of data
    Like this : L1, L2, FP,
        Their will be a random on the string selection and a random time of sending the string (like once every sec. +- 0.5sec). This rate of event mimic the real life application.
        This variable will be called ESPtoPC
    The program will also listen via MQTT for command from the PC
    The PC will send string like this : 2, 4, 6.
        When the ESP32 receive e.g. 4, he will blink a led 4 times
        This variable will be called PCtoESP

# Project steps
1. **Snippets 1 way** - [Code: `snippets/step1/`]
    A python minimal program that will listen MQTT channel of 2 ESP32 and have ESPtoPC1 and ESPtoPC2 variables
    - **Python Code**: `snippets/step1/mqtt_listener.py`
    - **ESP32 Code**: `snippets/step1/esp32_sender.ino`
    
    A very basic program for the ESP32 with the send ESPtoPC via MQTT program

2. **Snippets 2 ways** - [Code: `snippets/step2/`]
    A python minimal program that will listen and send MQTT channel of 2 ESP32, PCtoESP
    - **Python Code**: `snippets/step2/mqtt_bidirectional.py`
    - **ESP32 Code**: `snippets/step2/esp32_bidirectional.ino`
    
    A very basic program for the ESP32 with listen (with a led for confirmation) and send

3. **Minimal PyQt6 interface for the py program** - [Code: `snippets/step3/`]
    - **GUI Application**: `snippets/step3/pyqt6_interface.py`
    
    2 Boxes, one for each ESP32
        On each box there will be the ESP32 name displayed
        One display box that will show the last 'string' sended from ESPtoPC
        One user entry box so the user can enter the number of led pulse whated to ESPtoPC to do
            As soon as click out of the entry box it will send the command to the ESP32

4. **Add the LOG** - [Code: `snippets/step4/`]
    - **GUI with Logging**: `snippets/step4/pyqt6_interface_with_logging.py`
    
    For each boxes, when the communication start with the related ESP32
        Start a new LOG file (.xls) 
            First line will be the header with the box identification
            After that it will append line each time there some information from ESP32 comming from MQTT
            It will write if something is send from PC to ESP32 too. 
            For now, it can save the .xls file every time there a new line. 
