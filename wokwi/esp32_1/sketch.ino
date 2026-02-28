/*
  ESP32_1 - Wokwi Simulation Sketch
  Bidirectional MQTT communication for testing with Wokwi simulator.
  
  SETUP: 
    1. Install Wokwi VS Code extension
    2. Run Wokwi IoT Gateway (wokwi-cli) on your PC for network access
    3. Start a local MQTT broker (e.g. Mosquitto on port 1883)
    4. Open this folder in VS Code and start the Wokwi simulation
    
  WiFi: Uses "Wokwi-GUEST" (open network provided by Wokwi simulator)
  
  NOTE: PubSubClient only supports QoS 0 and QoS 1 (not QoS 2).
*/

#include <WiFi.h>
#include <PubSubClient.h>

// ─── Wokwi WiFi (open network, no password needed) ───
const char* ssid     = "Wokwi-GUEST";
const char* password = "";

// ─── MQTT Broker ──────────────────────────────────────
// When using Wokwi IoT Gateway, the host PC is reachable
// at the gateway IP. Typically use your PC's local IP.
const char* mqtt_server = "host.wokwi.internal";  // Wokwi gateway alias for host PC
const int   mqtt_port   = 1883;

// ─── Device identity ─────────────────────────────────
const String ESP32_NAME    = "ESP32_1";
const String DATA_TOPIC    = "mosquito/esp32_1/data";
const String COMMAND_TOPIC = "mosquito/esp32_1/command";

// LED pin (GPIO 2 = built-in LED on most devkit boards)
const int LED_PIN = 2;

// Random data strings to send (simulating sensor events)
const String DATA_STRINGS[] = {"L1", "L2", "FP"};
const int    NUM_STRINGS     = 3;

// Timing
unsigned long lastSendTime  = 0;
unsigned long sendInterval  = 1000;

// LED blink state
bool isBlinking        = false;
int  blinkCount        = 0;
int  targetBlinks      = 0;
unsigned long lastBlinkTime = 0;
const unsigned long BLINK_INTERVAL = 250;
bool ledState          = false;

WiFiClient   espClient;
PubSubClient client(espClient);

// ─── WiFi ────────────────────────────────────────────
void setup_wifi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected  IP: " + WiFi.localIP().toString());
}

void ensure_wifi() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost – reconnecting...");
    WiFi.disconnect();
    WiFi.begin(ssid, password);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts++ < 20) delay(500);
    if (WiFi.status() == WL_CONNECTED) Serial.println("WiFi reconnected");
  }
}

// ─── MQTT callback (commands from PC) ────────────────
void callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.println("RX [" + String(topic) + "]: " + msg);

  if (String(topic) == COMMAND_TOPIC) {
    int n = msg.toInt();
    if (n > 0 && n <= 20) {
      targetBlinks = n * 2;   // each blink = on + off
      blinkCount   = 0;
      isBlinking   = true;
      ledState     = false;
      digitalWrite(LED_PIN, LOW);
      lastBlinkTime = millis();
      Serial.println("Blinking LED " + String(n) + " times");
    }
  }
}

// ─── MQTT reconnect ─────────────────────────────────
void reconnect() {
  if (!client.connected()) {
    Serial.print("MQTT connecting...");
    if (client.connect(ESP32_NAME.c_str())) {
      Serial.println("ok");
      client.subscribe(COMMAND_TOPIC.c_str(), 1);  // QoS 1 max
    } else {
      Serial.println("fail rc=" + String(client.state()));
      delay(3000);
    }
  }
}

// ─── Setup ──────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println("\n=== " + ESP32_NAME + " (Wokwi) ===");
  setup_wifi();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  randomSeed(analogRead(0));
}

// ─── Loop ───────────────────────────────────────────
void loop() {
  ensure_wifi();
  if (!client.connected()) reconnect();
  client.loop();

  unsigned long now = millis();

  // Handle LED blinking
  if (isBlinking && (now - lastBlinkTime >= BLINK_INTERVAL)) {
    if (blinkCount < targetBlinks) {
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState ? HIGH : LOW);
      blinkCount++;
      lastBlinkTime = now;
    } else {
      isBlinking = false;
      digitalWrite(LED_PIN, LOW);
      Serial.println("Blink sequence done");
    }
  }

  // Send random data at random intervals (~1 s ± 0.5 s)
  if (!isBlinking && (now - lastSendTime >= sendInterval)) {
    String data = DATA_STRINGS[random(0, NUM_STRINGS)];
    if (client.publish(DATA_TOPIC.c_str(), data.c_str())) {
      Serial.println("TX -> " + DATA_TOPIC + ": " + data);
    }
    lastSendTime = now;
    sendInterval = random(500, 1500);
  }
}
