// --- LED pins ---
#define LED_RED     25   // Red LED (left side, DAC1)
#define LED_GREEN   14   // Green LED (left side, HSPI_CLK)

// --- Ultrasonic sensor pins ---
#define TRIGGER_PIN 27   // Ultrasonic TRIG (left side)
#define ECHO_PIN    26   // Ultrasonic ECHO (left side, via voltage divider)

// --- I²C LCD pins ---
#define SDA_PIN     32   // I²C SDA (left side, ADC1_4)
#define SCL_PIN     33   // I²C SCL (left side, ADC1_5)

// --- Wi-Fi credentials (replace with your own) ---
#define WIFI_SSID   "YOUR_WIFI_SSID"
#define WIFI_PASS   "YOUR_WIFI_PASSWORD"

// --- Backend URL (replace with your FastAPI endpoint) ---
#define SERVER_URL  "http://192.168.1.100:8000/status"
