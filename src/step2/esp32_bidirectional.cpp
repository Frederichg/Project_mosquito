/*
Step 2: ESP32 MQTT Bidirectional Communication
Publishes switch state and receives LED ON/OFF commands
Includes MCP23017-based switch and LED control

NOTE: PubSubClient only supports QoS 0 and QoS 1.
      QoS 2 (exactly once) is NOT available with this library.
      We use QoS 1 (at least once) as the best available option.
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <EEPROM.h>
#include <Wire.h>
#include <Adafruit_MCP23X17.h>

// EEPROM magic byte to validate stored data
#define EEPROM_MAGIC 0xA5
#define EEPROM_MAGIC_ADDR 0
#define EEPROM_NAME_ADDR 1

// WiFi credentials
const char* ssid = "Focal";
const char* password = "Poodzer11";

// MQTT Broker settings
const char* mqtt_server = "test.mosquitto.org";
const int mqtt_port = 1883;
const char* mqtt_namespace = "udem/pfh3221/mosquito";

// ESP32 unique name (stored in EEPROM)
String esp32_name = "";
String data_topic = "";
String command_topic = "";

// MCP23017 I2C settings
static const int I2C_SDA_PIN = 21;
static const int I2C_SCL_PIN = 22;
static const uint8_t MCP_ADDR = 0x20;
static const uint8_t MCP_SW_PIN = 7;  // GPA7 input (active low with pull-up)
static const uint8_t MCP_LED_PIN = 8; // GPB0 output

// Switch reporting variables
bool lastSwitchPressed = false;
unsigned long lastDebounceMs = 0;
const unsigned long debounceMs = 25;
unsigned long lastSwitchReportMs = 0;
const unsigned long switchReportPeriodMs = 1000;

bool ledState = false;

Adafruit_MCP23X17 mcp;
bool mcpReady = false;

WiFiClient espClient;
PubSubClient client(espClient);

// Forward declarations
void setup_wifi();
void callback(char* topic, byte* payload, unsigned int length);
void ensure_wifi();
void reconnect();
void handleSwitchAndPublish(unsigned long currentTime);
void publishSwitchState(bool pressed);
void setLedOutput(bool on);
String readStringFromEEPROM(int address);
void writeStringToEEPROM(int address, String data);

void setup() {
  Serial.begin(115200);
  
  // Initialize MCP23017 for LED control
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.setClock(100000);
  if (mcp.begin_I2C(MCP_ADDR, &Wire)) {
    mcpReady = true;
    mcp.pinMode(MCP_SW_PIN, INPUT_PULLUP);
    mcp.pinMode(MCP_LED_PIN, OUTPUT);
    mcp.digitalWrite(MCP_LED_PIN, LOW);
    lastSwitchPressed = (mcp.digitalRead(MCP_SW_PIN) == LOW);
    Serial.println("PASS: MCP23017 detected for LED/switch I/O");
  } else {
    Serial.println("WARN: MCP23017 not found, LED/switch features disabled");
  }
  
  // Initialize EEPROM
  EEPROM.begin(512);
  
  // Read ESP32 name from EEPROM (with magic byte validation)
  if (EEPROM.read(EEPROM_MAGIC_ADDR) == EEPROM_MAGIC) {
    esp32_name = readStringFromEEPROM(EEPROM_NAME_ADDR);
  }
  
  if (esp32_name.length() == 0 || esp32_name.length() > 30) {
    esp32_name = "ESP32_1"; // Default name, change for each device
    EEPROM.write(EEPROM_MAGIC_ADDR, EEPROM_MAGIC);
    writeStringToEEPROM(EEPROM_NAME_ADDR, esp32_name);
    EEPROM.commit();
  }
  
  // Build MQTT topics (toLowerCase modifies in-place on ESP32)
  String nameLower = esp32_name;
  nameLower.toLowerCase();
  data_topic = String(mqtt_namespace) + "/" + nameLower + "/data";
  command_topic = String(mqtt_namespace) + "/" + nameLower + "/command";
  
  Serial.println("ESP32 Name: " + esp32_name);
  Serial.println("Data Topic: " + data_topic);
  Serial.println("Command Topic: " + command_topic);
  
  // Connect to WiFi
  setup_wifi();
  
  // Use public broker for first validation to avoid local firewall issues
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.println("Message received [" + String(topic) + "]: " + message);
  
  // Check if this is a command for this ESP32
  if (String(topic) == command_topic) {
    String command = message;
    command.trim();
    command.toUpperCase();

    if (command == "ON" || command == "1") {
      ledState = true;
      setLedOutput(true);
      Serial.println("LED set to ON");
    } else if (command == "OFF" || command == "0") {
      ledState = false;
      setLedOutput(false);
      Serial.println("LED set to OFF");
    } else {
      Serial.println("Invalid LED command (use ON/OFF): " + message);
    }
  }
}

void ensure_wifi() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost, reconnecting...");
    WiFi.disconnect();
    WiFi.begin(ssid, password);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      Serial.print(".");
      attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWiFi reconnected");
    } else {
      Serial.println("\nWiFi reconnection failed, will retry...");
    }
  }
}

void reconnect() {
  if (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    if (client.connect(esp32_name.c_str())) {
      Serial.println("connected");
      // Subscribe to command topic with QoS 1 (PubSubClient max)
      client.subscribe(command_topic.c_str(), 1);
      Serial.println("Subscribed to: " + command_topic);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void loop() {
  ensure_wifi();
  
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  unsigned long currentTime = millis();

  // Publish switch state when it changes and as periodic status
  handleSwitchAndPublish(currentTime);
}

void handleSwitchAndPublish(unsigned long currentTime) {
  if (!mcpReady) {
    return;
  }

  bool switchPressed = (mcp.digitalRead(MCP_SW_PIN) == LOW);

  // Debounced change reporting
  if (switchPressed != lastSwitchPressed) {
    if ((currentTime - lastDebounceMs) > debounceMs) {
      lastSwitchPressed = switchPressed;
      publishSwitchState(switchPressed);
    }
    lastDebounceMs = currentTime;
  }

  // Periodic status reporting
  if ((currentTime - lastSwitchReportMs) >= switchReportPeriodMs) {
    lastSwitchReportMs = currentTime;
    publishSwitchState(switchPressed);
  }
}

void publishSwitchState(bool pressed) {
  const char* payload = pressed ? "PRESSED" : "RELEASED";

  // Publish with QoS 0 - PubSubClient max is QoS 1
  if (client.publish(data_topic.c_str(), payload)) {
    Serial.println("Sent switch state: " + String(payload) + " to " + data_topic);
  } else {
    Serial.println("Failed to send switch state: " + String(payload));
  }
}

void setLedOutput(bool on) {
  if (!mcpReady) {
    return;
  }
  mcp.digitalWrite(MCP_LED_PIN, on ? HIGH : LOW);
}

// EEPROM helper functions
void writeStringToEEPROM(int address, String data) {
  int len = data.length();
  if (len > 100) len = 100; // Safety limit
  EEPROM.write(address, len);
  for (int i = 0; i < len; i++) {
    EEPROM.write(address + 1 + i, data[i]);
  }
}

String readStringFromEEPROM(int address) {
  int len = EEPROM.read(address);
  if (len == 0 || len > 100) return ""; // Validate length (0xFF = 255 on fresh EEPROM)
  String data = "";
  for (int i = 0; i < len; i++) {
    data += char(EEPROM.read(address + 1 + i));
  }
  return data;
}
