/*
Step 1: ESP32 MQTT Sender (1-way communication)
Sends random data strings (L1, L2, FP) at random intervals
Uses unique ESP32 name stored in EEPROM
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <EEPROM.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

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
  
  // Read ESP32 name from EEPROM or set default
  esp32_name = readStringFromEEPROM(0);
  if (esp32_name == "") {
    esp32_name = "ESP32_1"; // Default name, change for each device
    writeStringToEEPROM(0, esp32_name);
    EEPROM.commit();
  }
  
  // Set MQTT topic based on ESP32 name
  mqtt_topic = "mosquito/" + esp32_name.toLowerCase() + "/data";
  
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

void reconnect() {
  while (!client.connected()) {
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
  
  // Publish with QoS 2 (exactly once)
  if (client.publish(mqtt_topic.c_str(), dataToSend.c_str(), true)) {
    Serial.println("Sent: " + dataToSend + " to " + mqtt_topic);
  } else {
    Serial.println("Failed to send: " + dataToSend);
  }
}

// EEPROM helper functions
void writeStringToEEPROM(int address, String data) {
  int len = data.length();
  EEPROM.write(address, len);
  for (int i = 0; i < len; i++) {
    EEPROM.write(address + 1 + i, data[i]);
  }
}

String readStringFromEEPROM(int address) {
  int len = EEPROM.read(address);
  String data = "";
  for (int i = 0; i < len; i++) {
    data += char(EEPROM.read(address + 1 + i));
  }
  return data;
}
