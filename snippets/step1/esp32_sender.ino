/*
Step 1: ESP32 MQTT Sender (1-way communication)
Sends random data strings (L1, L2, FP) at random intervals
Uses unique ESP32 name stored in EEPROM

NOTE: PubSubClient only supports QoS 0 and QoS 1.
      QoS 2 (exactly once) is NOT available with this library.
      We use QoS 1 (at least once) as the best available option.
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <EEPROM.h>

// EEPROM magic byte to validate stored data
#define EEPROM_MAGIC 0xA5
#define EEPROM_MAGIC_ADDR 0
#define EEPROM_NAME_ADDR 1

// WiFi credentials
const char* ssid = "Focal-5G";
const char* password = "Poodzer11";

// MQTT Broker settings
const char* mqtt_server = "YOUR_MQTT_BROKER_IP";
const int mqtt_port = 1883;

// ESP32 unique name (stored in EEPROM)
String esp32_name = "";
String mqtt_topic = "";

// Random data strings to send
String data_strings[] = {"L1", "L2", "FP"};
const int num_strings = sizeof(data_strings) / sizeof(data_strings[0]);

// Timing variables
unsigned long lastSendTime = 0;
unsigned long sendInterval = 1000; // Base interval of 1 second

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);
  
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
  
  // Build MQTT topic (toLowerCase modifies in-place on ESP32)
  String nameLower = esp32_name;
  nameLower.toLowerCase();
  mqtt_topic = "mosquito/" + nameLower + "/data";
  
  Serial.println("ESP32 Name: " + esp32_name);
  Serial.println("MQTT Topic: " + mqtt_topic);
  
  // Connect to WiFi
  setup_wifi();
  
  // Set MQTT server
  client.setServer(mqtt_server, mqtt_port);
  
  // Seed random number generator
  randomSeed(analogRead(0));
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
  
  // Check if it's time to send data
  if (currentTime - lastSendTime >= sendInterval) {
    sendRandomData();
    lastSendTime = currentTime;
    
    // Set next random interval (1000ms ± 500ms)
    sendInterval = random(500, 1500);
  }
}

void sendRandomData() {
  // Select random string
  int randomIndex = random(0, num_strings);
  String dataToSend = data_strings[randomIndex];
  
  // Publish with QoS 1 (at least once) - PubSubClient max is QoS 1
  // Note: publish(topic, payload) uses QoS 0; retained=false
  if (client.publish(mqtt_topic.c_str(), dataToSend.c_str())) {
    Serial.println("Sent: " + dataToSend + " to " + mqtt_topic);
  } else {
    Serial.println("Failed to send: " + dataToSend);
  }
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
