#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// NOTE YOU MUST OPEN THE SERIAL MONITOR AND SET BAUD RATE TO 115200 in order to copy paste local ip
// NEEDS ACTUAL SSID OF WIFI AND PASSWORD TO CONNECT OT OTHER DEVICES IN THE NETWORK
// MAKE SURE ARDUINO IDE IS CONFIGURED FOR ESP32  BOARDS
// Wi-Fi credentials
const char* ssid = "ssid";
const char* password = "password";

// LCD setup (I²C address may be 0x27 or 0x3F)
#define SDA_PIN 32
#define SCL_PIN 33
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Create web server on port 80
WebServer server(80);

void handleRoot() {
  // Respond to browser
  server.send(200, "text/plain", "Hello ESP32");

  // Also print to LCD
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("Webserver hit!");
  lcd.setCursor(0,1);
  lcd.print("Hello ESP32");
}

void setup() {
  Serial.begin(115200);

  // LCD init
  Wire.begin(SDA_PIN, SCL_PIN);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0,0);
  lcd.print("Connecting WiFi");

  // Connect Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("WiFi Connected");
  lcd.setCursor(0,1);
  lcd.print(WiFi.localIP().toString());

  // Setup webserver route
  server.on("/", handleRoot);
  server.begin();
  Serial.println("Webserver started");
}

void loop() {
  // Handle incoming client requests
  server.handleClient();
}
