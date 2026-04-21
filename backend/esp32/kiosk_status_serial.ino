#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// --- LED pins (from board_def.ino) ---
#define LED_RED     25   // Red LED (left side, DAC1)
#define LED_GREEN   14   // Green LED (left side, HSPI_CLK)

// --- Ultrasonic sensor pins ---
#define TRIGGER_PIN 27   // Ultrasonic TRIG (left side)
#define ECHO_PIN    26   // Ultrasonic ECHO (left side, via voltage divider)

// --- I2C pins (not used here) ---
#define SDA_PIN     32   // I2C SDA (left side, ADC1_4)
#define SCL_PIN     33   // I2C SCL (left side, ADC1_5)

// --- LCD settings ---
#define LCD_I2C_ADDRESS 0x27
#define LCD_COLS        16
#define LCD_ROWS        2

// --- Wi-Fi credentials (replace with your own) ---
#define WIFI_SSID   "ssid"
#define WIFI_PASS   "password"

// --- Backend URLs (replace with your FastAPI endpoint) ---
// Example: http://192.168.1.100:3009/api/kiosk-status
// Note: Use your computer's local IP address where the FastAPI server is running.
// NOTE ENABLE TCP on YOUR COMPUTER FIREWALL FOR PORT 3009 TO ALLOW ESP32 TO CONNECT
#define API_BASE_URL        "http://192.xxx.xxx.xx:3009"
#define KIOSK_STATUS_PATH     "/api/kiosk-status"
#define HEALTH_PATH           "/api/health"

// --- Configurables ---
static const unsigned long SERVER_POLL_INTERVAL_MS = 30000;   // Avoid spamming when idle.
static const unsigned long WAITING_STATE_INTERVAL_MS = 800;   // Retry delay when status is waiting.
static const unsigned int ENDPOINT_RETRY_TIMES = 5;
static const unsigned long POST_RESULT_DELAY_MS = 1000;       // Delay after greeting/error.
static const unsigned long WIFI_CONNECT_TIMEOUT_MS = 15000;   // Max time to wait for WiFi on boot.
static const unsigned long WIFI_SUCCESS_GREEN_MS = 1200;      // Green LED duration after WiFi connects.
static const unsigned long FLASH_INTERVAL_MS = 1500;          // Slow alternation between welcome and move-close prompts.

static const unsigned long ULTRASONIC_TRIGGER_INTERVAL_MS = 120; // Debounce for trigger.
static const double DETECT_START_RANGE_CM = 10.0;
static const double RETRY_DISTANCE_CM = 6.0;                  // Close enough to confirm retry on common HC-SR04 noise.
static const double MAX_DISTANCE_CM = 400.0;
static const unsigned long STEADY_TIME_US = 100;              // Person must stay in range.

// --- Ultrasonic measurement state ---
volatile unsigned long pulseInTimeBegin = 0;
volatile unsigned long pulseInTimeEnd = 0;
volatile bool newDistanceAvailable = false;

unsigned long lastUltrasonicTriggerMs = 0;
double previousDistanceCm = MAX_DISTANCE_CM;
double lastDistanceCm = MAX_DISTANCE_CM;

// --- Presence/session state ---
bool personDetected = false;
bool waitingForRetry = false;
bool fetchedForPresence = false;
unsigned long lastServerPollMs = 0;
unsigned long inRangeStartUs = 0;
unsigned long lastResultMs = 0;
bool waitingForWifiRetry = false;
bool wifiConnected = false;
unsigned long wifiGreenUntilMs = 0;
bool retryPromptShown = false;

enum RetryReason {
  RETRY_NONE = 0,
  RETRY_API_UNREACHABLE = 1,
  RETRY_WAITING = 2,
  RETRY_RECOGNIZED = 3,
  RETRY_NO_FACE = 4
};

RetryReason retryReason = RETRY_NONE;
String recognizedName = "";
String recognizedConfidence = "";
bool flashVisible = true;
unsigned long lastFlashToggleMs = 0;

LiquidCrystal_I2C lcd(LCD_I2C_ADDRESS, LCD_COLS, LCD_ROWS);

void lcdShow(const String &line1, const String &line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1.substring(0, LCD_COLS));
  lcd.setCursor(0, 1);
  lcd.print(line2.substring(0, LCD_COLS));
}

void setLedRed() {
  digitalWrite(LED_RED, HIGH);
  digitalWrite(LED_GREEN, LOW);
}

void setLedGreen() {
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_GREEN, HIGH);
}

void blinkBoth(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_RED, HIGH);
    digitalWrite(LED_GREEN, HIGH);
    delay(150);
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_GREEN, LOW);
    delay(150);
  }
}

void blinkRed(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_RED, HIGH);
    digitalWrite(LED_GREEN, LOW);
    delay(delayMs);
    digitalWrite(LED_RED, LOW);
    delay(delayMs);
  }
}

bool connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("Connecting to WiFi");
  unsigned long startMs = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startMs < WIFI_CONNECT_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("WiFi connected. IP: ");
    Serial.println(WiFi.localIP());
    lcdShow("WiFi Connected", WiFi.localIP().toString());
    return true;
  }

  Serial.println();
  Serial.println("WiFi connection failed.");
  lcdShow("WiFi Failed", "Move close");
  return false;
}

void triggerUltrasonicSensor() {
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);
}

double computeDistanceCm() {
  double durationMicros = static_cast<double>(pulseInTimeEnd - pulseInTimeBegin);
  double distanceCenti = durationMicros / 58.0;
  if (distanceCenti <= 0.0 || distanceCenti > MAX_DISTANCE_CM) {
    return previousDistanceCm;
  }
  previousDistanceCm = distanceCenti;
  return distanceCenti;
}

void IRAM_ATTR ultrasonicSensorInterrupt() {
  if (digitalRead(ECHO_PIN) == HIGH) {
    pulseInTimeBegin = micros();
  } else {
    pulseInTimeEnd = micros();
    newDistanceAvailable = true;
  }
}

String httpGet(const String &url, bool &ok) {
  HTTPClient http;
  http.begin(url);
  int httpCode = http.GET();
  if (httpCode > 0) {
    ok = true;
    String payload = http.getString();
    http.end();
    return payload;
  }
  ok = false;
  String err = http.errorToString(httpCode);
  http.end();
  return err;
}

String jsonValue(const String &payload, const String &key) {
  String token = "\"" + key + "\":";
  int start = payload.indexOf(token);
  if (start < 0) {
    return "";
  }
  start += token.length();
  while (start < payload.length() && payload.charAt(start) == ' ') {
    start++;
  }
  if (start >= payload.length()) {
    return "";
  }
  if (payload.charAt(start) == '"') {
    start++;
    int end = payload.indexOf('"', start);
    if (end < 0) {
      return "";
    }
    return payload.substring(start, end);
  }
  int end = start;
  while (end < payload.length() && payload.charAt(end) != ',' && payload.charAt(end) != '}') {
    end++;
  }
  String value = payload.substring(start, end);
  value.trim();
  return value;
}

bool parseBool(const String &value) {
  String v = value;
  v.toLowerCase();
  return v == "true" || v == "1";
}

void resetPresenceState() {
  personDetected = false;
  waitingForRetry = false;
  fetchedForPresence = false;
  inRangeStartUs = 0;
  retryReason = RETRY_NONE;
  retryPromptShown = false;
  recognizedName = "";
  recognizedConfidence = "";
  flashVisible = true;
  lastFlashToggleMs = 0;
}

void enterRetryState(RetryReason reason) {
  waitingForRetry = true;
  retryReason = reason;
  retryPromptShown = false;
}

void logDistanceIfNeeded(unsigned long nowMs) {
  (void) nowMs;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(TRIGGER_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Wire.begin(SDA_PIN, SCL_PIN);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Booting...");

  blinkBoth(3);
  setLedRed();

  attachInterrupt(digitalPinToInterrupt(ECHO_PIN), ultrasonicSensorInterrupt, CHANGE);
  wifiConnected = connectWifi();
  if (wifiConnected) {
    setLedGreen();
    wifiGreenUntilMs = millis() + WIFI_SUCCESS_GREEN_MS;
  } else {
    waitingForWifiRetry = true;
  }
}

void loop() {
  unsigned long nowMs = millis();
  unsigned long nowUs = micros();

  if (nowMs - lastUltrasonicTriggerMs >= ULTRASONIC_TRIGGER_INTERVAL_MS) {
    lastUltrasonicTriggerMs = nowMs;
    triggerUltrasonicSensor();
  }

  if (newDistanceAvailable) {
    newDistanceAvailable = false;
    lastDistanceCm = computeDistanceCm();
    logDistanceIfNeeded(nowMs);
  }

  if (wifiConnected && wifiGreenUntilMs > 0 && nowMs < wifiGreenUntilMs) {
    setLedGreen();
  } else if (wifiConnected && wifiGreenUntilMs > 0 && nowMs >= wifiGreenUntilMs) {
    wifiGreenUntilMs = 0;
    setLedRed();
  }

  if (waitingForWifiRetry) {
    blinkRed(1, 120);
    logDistanceIfNeeded(nowMs);
    if (lastDistanceCm <= RETRY_DISTANCE_CM) {
      Serial.println("WiFi retry requested.");
      lcdShow("Retry WiFi", "Connecting...");
      wifiConnected = connectWifi();
      if (wifiConnected) {
        waitingForWifiRetry = false;
        setLedGreen();
        wifiGreenUntilMs = millis() + WIFI_SUCCESS_GREEN_MS;
      }
    }
    delay(20);
    return;
  }

  if (!wifiConnected) {
    waitingForWifiRetry = true;
    delay(20);
    return;
  }

  bool inRange = lastDistanceCm <= DETECT_START_RANGE_CM;

  if (waitingForRetry) {
    setLedRed();
    logDistanceIfNeeded(nowMs);
    if (retryReason == RETRY_RECOGNIZED && millis() - lastFlashToggleMs >= FLASH_INTERVAL_MS) {
      lastFlashToggleMs = millis();
      flashVisible = !flashVisible;
      if (flashVisible) {
        lcdShow("Welcome back", recognizedName);
      } else {
        lcdShow("Move close", "to try again");
      }
    }
    if (!retryPromptShown) {
      if (retryReason == RETRY_API_UNREACHABLE) {
        Serial.println("API unreachable. Move close to retry.");
        lcdShow("API unreachable", "Move < 6cm");
      } else if (retryReason == RETRY_WAITING) {
        Serial.println("Try again. Move close to retry.");
        lcdShow("Try again", "Move < 6cm");
      } else if (retryReason == RETRY_RECOGNIZED) {
        Serial.println("Recognized. Hold close to try again.");
        lcdShow("Welcome back", recognizedName);
      }
      retryPromptShown = true;
    }
    if (lastDistanceCm <= RETRY_DISTANCE_CM) {
      Serial.println("Retry requested. Resetting session.");
      resetPresenceState();
    }
    delay(20);
    return;
  }

  if (!inRange) {
    setLedRed();
    resetPresenceState();
    delay(20);
    return;
  }

  if (inRangeStartUs == 0) {
    inRangeStartUs = nowUs;
  }

  if (nowUs - inRangeStartUs < STEADY_TIME_US) {
    setLedRed();
    delay(5);
    return;
  }

  personDetected = true;
  setLedGreen();

  if (!fetchedForPresence || (nowMs - lastServerPollMs >= SERVER_POLL_INTERVAL_MS)) {
    fetchedForPresence = true;
    lastServerPollMs = nowMs;

    Serial.println("Person detected. Fetching kiosk status...");
    lcdShow("Person detected", "Fetching...");
    String statusUrl = String(API_BASE_URL) + KIOSK_STATUS_PATH;
    bool ok = false;
    String payload = httpGet(statusUrl, ok);
    if (!ok) {
      Serial.println("API unreachable. Please ensure endpoint is accessible and ESP32 is on the network.");
      Serial.print("Details: ");
      Serial.println(payload);
      lcdShow("API unreachable", payload);
      blinkRed(6, 150);
      enterRetryState(RETRY_API_UNREACHABLE);
      lastResultMs = nowMs;
      return;
    }

    String statusValue = jsonValue(payload, "status");
    String nameValue = jsonValue(payload, "name");
    String confidenceValue = jsonValue(payload, "confidence");
    if (statusValue.length() == 0) {
      statusValue = payload;
    }

    bool unrecognizedFace = (nameValue == "Unknown");
    String nameValueLower = nameValue;
    nameValueLower.toLowerCase();
    bool noFaceDetected = nameValueLower.indexOf("no face") >= 0;

    if (noFaceDetected) {
      Serial.println("No face detected, try again.");
      lcdShow("No face detected", "Try again");
      blinkRed(3, 150);
      enterRetryState(RETRY_NO_FACE);
      lastResultMs = nowMs;
      return;
    }

    unsigned int tries = 0;
    while (statusValue == "waiting" && tries < ENDPOINT_RETRY_TIMES) {
      Serial.println("Status is waiting. Retrying...");
      lcdShow("Status waiting", "Retrying...");
      tries++;
      delay(WAITING_STATE_INTERVAL_MS);
      bool retryOk = false;
      String retryPayload = httpGet(statusUrl, retryOk);
      if (!retryOk) {
        Serial.println("API unreachable. Please ensure endpoint is accessible and ESP32 is on the network.");
        Serial.print("Details: ");
        Serial.println(retryPayload);
        lcdShow("API unreachable", retryPayload);
        blinkRed(6, 150);
        enterRetryState(RETRY_API_UNREACHABLE);
        lastResultMs = nowMs;
        return;
      }
      payload = retryPayload;
      statusValue = jsonValue(payload, "status");
      if (statusValue.length() == 0) {
        statusValue = payload;
      }
    }

    if (statusValue == "waiting") {
      Serial.println("Status is still waiting. Max retries reached.");
      Serial.println("Checking health endpoint...");
      lcdShow("Still waiting", "Check health");
      blinkRed(6, 150);

      String healthUrl = String(API_BASE_URL) + HEALTH_PATH;
      bool healthOk = false;
      String healthPayload = httpGet(healthUrl, healthOk);
      if (!healthOk) {
        Serial.println("Error accessing health endpoint. Please ensure endpoint is accessible.");
        Serial.print("Details: ");
        Serial.println(healthPayload);
        lcdShow("Health error", healthPayload);
      } else {
        bool okValue = parseBool(jsonValue(healthPayload, "ok"));
        String errValue = jsonValue(healthPayload, "error");
        String detectorValue = jsonValue(healthPayload, "detector_loaded");
        String classesValue = jsonValue(healthPayload, "classes_loaded");
        String modelValue = jsonValue(healthPayload, "model_loaded");

        Serial.print("Health ok: ");
        Serial.println(okValue ? "true" : "false");
        Serial.print("detector_loaded: ");
        Serial.println(detectorValue);
        Serial.print("classes_loaded: ");
        Serial.println(classesValue);
        Serial.print("model_loaded: ");
        Serial.println(modelValue);
        if (!okValue) {
          Serial.print("error: ");
          Serial.println(errValue);
          lcdShow("Health error", errValue);
        } else {
          lcdShow("Health ok", "Try again");
        }
      }

      if (unrecognizedFace) {
        Serial.println("Not recognized. Please register your face first!");
        lcdShow("Not recognized", "Register face");
        enterRetryState(RETRY_WAITING);
      } else {
        Serial.println("Please try again by placing your hand 1-2cm from the sensor.");
        lcdShow("Try again", "Move close");
        enterRetryState(RETRY_WAITING);
      }
      lastResultMs = nowMs;
      return;
    }

    if (nameValue.length() == 0) {
      nameValue = "Unknown";
    }
    if (confidenceValue.length() == 0) {
      confidenceValue = "0";
    }

    Serial.print("Welcome back ");
    Serial.print(nameValue);
    Serial.print("! I am ");
    Serial.print(confidenceValue);
    Serial.println(" that I recognize you!");

    recognizedName = nameValue;
    recognizedConfidence = confidenceValue;
    lcdShow("Welcome back", recognizedName);
    flashVisible = true;
    lastFlashToggleMs = millis();

    delay(POST_RESULT_DELAY_MS);
    Serial.println("Hold close to try again.");
    enterRetryState(RETRY_RECOGNIZED);
    lastResultMs = nowMs;
  }

  delay(20);
}
