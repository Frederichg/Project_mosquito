/*
Step 2: ESP32 MQTT Bidirectional Communication
Sends random data strings and listens for LED blink commands
Includes LED control functionality
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
  
  // Read ESP32 name from EEPROM or set default
  esp32_name = readStringFromEEPROM(0);
  if (esp32_name == "") {
    esp32_name = "ESP32_1"; // Default name, change for each device
    writeStringToEEPROM(0, esp32_name);
    EEPROM.commit();
  }
  
  // Set MQTT topics based on ESP32 name
  data_topic = "mosquito/" + esp32_name.toLowerCase() + "/data";
  command_topic = "mosquito/" + esp32_name.toLowerCase() + "/command";
  
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

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    if (client.connect(esp32_name.c_str())) {
      Serial.println("connected");
      // Subscribe to command topic
      client.subscribe(command_topic.c_str(), 2); // QoS 2
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
  
  // Publish with QoS 2 (exactly once)
  if (client.publish(data_topic.c_str(), dataToSend.c_str(), true)) {
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
