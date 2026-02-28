/*
Step 2: ESP32 MQTT Bidirectional Communication
Sends random data strings and listens for LED blink commands
Includes LED control functionality

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
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT Broker settings
const char* mqtt_server = "YOUR_MQTT_BROKER_IP";
const int mqtt_port = 1883;

// ESP32 unique name (stored in EEPROM)
String esp32_name = "";
String data_topic = "";
String command_topic = "";

// LED pin
const int LED_PIN = 2; // Built-in LED on most ESP32 boards

// Random data strings to send
String data_strings[] = {"L1", "L2", "FP"};
const int num_strings = sizeof(data_strings) / sizeof(data_strings[0]);

// Timing variables
unsigned long lastSendTime = 0;
unsigned long sendInterval = 1000; // Base interval of 1 second

// LED blinking variables
bool isBlinking = false;
int blinkCount = 0;
int targetBlinks = 0;
unsigned long lastBlinkTime = 0;
const unsigned long blinkInterval = 250; // 250ms on/off
bool ledState = false;

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);
  
  // Initialize LED pin
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
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
  data_topic = "mosquito/" + nameLower + "/data";
  command_topic = "mosquito/" + nameLower + "/command";
  
  Serial.println("ESP32 Name: " + esp32_name);
  Serial.println("Data Topic: " + data_topic);
  Serial.println("Command Topic: " + command_topic);
  
  // Connect to WiFi
  setup_wifi();
  
  // Set MQTT server and callback
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
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

void callback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.println("Message received [" + String(topic) + "]: " + message);
  
  // Check if this is a command for this ESP32
  if (String(topic) == command_topic) {
    int blinkNumber = message.toInt();
    if (blinkNumber > 0 && blinkNumber <= 20) { // Reasonable limit
      startBlinking(blinkNumber);
      Serial.println("Starting LED blink sequence: " + String(blinkNumber) + " times");
    } else {
      Serial.println("Invalid blink number: " + message);
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
  
  // Handle LED blinking
  handleLEDBlinking(currentTime);
  
  // Check if it's time to send data (only if not blinking)
  if (!isBlinking && (currentTime - lastSendTime >= sendInterval)) {
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
  
  // Publish with QoS 0 - PubSubClient max is QoS 1
  // Note: publish(topic, payload) uses QoS 0; not using retained flag
  if (client.publish(data_topic.c_str(), dataToSend.c_str())) {
    Serial.println("Sent: " + dataToSend + " to " + data_topic);
  } else {
    Serial.println("Failed to send: " + dataToSend);
  }
}

void startBlinking(int times) {
  targetBlinks = times * 2; // Each blink is on+off
  blinkCount = 0;
  isBlinking = true;
  ledState = false;
  digitalWrite(LED_PIN, LOW);
  lastBlinkTime = millis();
}

void handleLEDBlinking(unsigned long currentTime) {
  if (!isBlinking) return;
  
  if (currentTime - lastBlinkTime >= blinkInterval) {
    if (blinkCount < targetBlinks) {
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState ? HIGH : LOW);
      blinkCount++;
      lastBlinkTime = currentTime;
    } else {
      // Blinking sequence complete
      isBlinking = false;
      digitalWrite(LED_PIN, LOW);
      Serial.println("LED blinking sequence completed");
    }
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
