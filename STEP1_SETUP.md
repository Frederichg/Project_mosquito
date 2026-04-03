# Step 1 Setup Notes

This project currently has a working Step 1 test using:

- ESP32 publisher: [src/mqtt_reader.cpp](src/mqtt_reader.cpp)
- Python listener: [src/mqtt_listener.py](src/mqtt_listener.py)
- Public MQTT broker: `test.mosquitto.org:1883`
- Current topic namespace: `udem/pfh3221/mosquito`

This setup was chosen for initial validation because it avoids local firewall, broker installation, and network configuration issues.

## What Is Working Now

The ESP32:

- connects to Wi-Fi
- connects to the MQTT broker
- publishes random values `L1`, `L2`, and `FP`
- publishes to a topic built as:

```text
udem/pfh3221/mosquito/<esp32_name>/data
```

Example:

```text
udem/pfh3221/mosquito/esp32_1/data
```

The Python listener:

- connects to the same broker
- subscribes to the Step 1 topics
- prints received MQTT messages in the terminal

## Files To Update On Another Computer Or Network

When moving this project to another computer or another Wi-Fi network, these values must be reviewed.

### 1. Wi-Fi settings in the ESP32 file

Edit [src/mqtt_reader.cpp](src/mqtt_reader.cpp):

- `ssid`
- `password`

These must match the target Wi-Fi network.

Important:

- the ESP32 must use a 2.4 GHz Wi-Fi network
- if the router has separate 2.4 GHz and 5 GHz names, use the 2.4 GHz one

### 2. MQTT broker settings in both files

Edit both [src/mqtt_reader.cpp](src/mqtt_reader.cpp) and [src/mqtt_listener.py](src/mqtt_listener.py):

- broker address
- broker port
- topic namespace if needed

These values must match on both sides.

### 3. Python dependencies on the new computer

Install the required packages from [requirements.txt](requirements.txt):

```bash
pip install -r requirements.txt
```

## Current Public Broker Configuration

Right now the code uses a public broker for testing.

In [src/mqtt_reader.cpp](src/mqtt_reader.cpp):

- broker: `test.mosquitto.org`
- port: `1883`
- namespace: `udem/pfh3221/mosquito`

In [src/mqtt_listener.py](src/mqtt_listener.py):

- broker: `test.mosquitto.org`
- port: `1883`
- namespace: `udem/pfh3221/mosquito`

This is acceptable for development and demonstration, but it should not be the final deployment choice.

## Why The Public Broker Should Be Changed Later

The public broker is useful for quick tests, but it has limitations:

- no control over uptime or service changes
- no control over who can publish or subscribe
- data leaves the local network
- no project-specific authentication or access control
- possible topic collisions if namespaces are not unique enough

## Recommended Migration To A Private Broker

Before final deployment, replace the public broker with your own MQTT broker.

This can be done on:

- the final PC
- a Raspberry Pi
- a local server
- a cloud VM if remote access is needed

### X. Install a broker

Recommended option: Mosquitto.

Install it on the target machine that will host the broker.

### Y. Configure the broker for the target network

At minimum:

- choose the listening port, usually `1883`
- allow the ESP32 and Python client to reach that machine over the network
- open the firewall if required

For a LAN setup, the broker should listen on the machine's local IP, not just `localhost`.

### Z. Update both project files

Replace the public broker values in both files:

- [src/mqtt_reader.cpp](src/mqtt_reader.cpp)
- [src/mqtt_listener.py](src/mqtt_listener.py)

Update:

- broker address
- port
- credentials if authentication is enabled
- namespace if your team wants a different prefix

## Minimum Checklist For Another Computer

1. Install Python.
2. Install Python packages with `pip install -r requirements.txt`.
3. Connect the ESP32 computer to the correct 2.4 GHz Wi-Fi.
4. Update Wi-Fi credentials in [src/mqtt_reader.cpp](src/mqtt_reader.cpp).
5. Confirm both files use the same MQTT broker and port.
6. Confirm both files use the same topic namespace.
7. Upload the ESP32 firmware.
8. Start the Python listener.
9. Verify messages are received.

## Verification Expectations

When everything is configured correctly:

- the ESP32 serial monitor should show `Attempting MQTT connection...connected`
- the ESP32 should print sent values such as `L1`, `L2`, or `FP`
- the Python listener should print incoming messages with timestamps

## Notes

- `mqtt_reader.cpp` is a publisher, even though the name says `reader`
- the current Step 1 implementation is intentionally simple and meant as a validated starting point
- this setup should be treated as a working prototype, not the final secure deployment architecture