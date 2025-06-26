#include <WiFi.h>
#include <HTTPClient.h>
#include <math.h>
#include <WiFiUdp.h>

#include <TinyGPSPlus.h>
#include <HardwareSerial.h>

HardwareSerial mySerial(1);
TinyGPSPlus gps;

const char* ssid = "redeR";
const char* password = "--($_$)--";
const char* endpoint_url = "http://192.168.202.104:81/leituras";

const int trigPin = 14;
const int echoPin = 27;
const int rx2pin = 16;
const int tx2pin = 17;

const int ledPin = 33;

const int numReadings = 10;

//define sound speed in cm/uS
#define SOUND_SPEED 0.034
#define GPS_BAUD 9600
String macString = "";

float latitude = -16.671244161185665;
float longitude = -49.23883199075531;

void setup() {
  Serial.begin(115200); // Starts the serial communication
  mySerial.begin(GPS_BAUD, SERIAL_8N1, rx2pin, tx2pin);
  pinMode(trigPin, OUTPUT); // Sets the trigPin as an Output
  pinMode(echoPin, INPUT); // Sets the echoPin as an Input

  pinMode(ledPin, OUTPUT);

  wifi_connect();

  uint8_t mac[6];
  WiFi.macAddress(mac);
  for (int i = 0; i < 6; i++) {
    if (mac[i] < 0x10) {
      macString += "0";
    }
    macString += String(mac[i], HEX);
  }
}

void wifi_connect(){
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(ledPin, HIGH);
    delay(250);
    Serial.print(".");
    digitalWrite(ledPin, LOW);
    delay(250);
  }
  digitalWrite(ledPin, LOW);

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}


void loop() {
  update_loc();
  float distanceCm = calculate_distance();
  
  if(latitude == 1000 || longitude == 1000)
  {
    delay(500);
    return;
  }
  Serial.print("Distance (cm): ");
  Serial.println(distanceCm);  
  Serial.println("");
  if (WiFi.status() == WL_CONNECTED) {
    send_message(distanceCm);
  }else {
    Serial.println("Erro na conexão WiFi");
  }
  delay(5000);
}

void update_loc(){
  while (mySerial.available() > 0) {
    char c = mySerial.read();
    Serial.print(c);
    gps.encode(c);
  }
  Serial.println("");
  if (gps.location.isUpdated()) {
    Serial.print("GPS: ");
    Serial.print("Latitude: ");
    Serial.print(gps.location.lat(), 6);
    Serial.print(" Longitude: ");
    Serial.println(gps.location.lng(), 6);
    latitude = gps.location.lat();
    longitude = gps.location.lng();
  }
  else {
    Serial.println("Dados GPS não atualizados - erro em obter dados");
  }
}

float calculate_distance(){
  long durations[numReadings];
  float total = 0.0;
  digitalWrite(ledPin, HIGH);

  for (int i = 0; i < numReadings; i++) {
    durations[i] = get_reading();
    total += durations[i];
    delay(1000);
  }
  float mean = total / numReadings;

  // Compute standard deviation
  float variance = 0.0;
  for (int i = 0; i < numReadings; i++) {
      variance += pow(durations[i] - mean, 2);
  }
  float stddev = sqrt(variance / numReadings);

  // Filter out values beyond 2 standard deviations
  float filteredTotal = 0.0;
  int count = 0;
  for (int i = 0; i < numReadings; i++) {
      if (fabs(durations[i] - mean) <= 2 * stddev) { // Within 2 standard deviations
          filteredTotal += durations[i];
          count++;
      }
  }

  // Compute the final average distance
  float average_duration = (count > 0) ? (filteredTotal / count) : mean; // Avoid division by zero
  digitalWrite(ledPin, LOW);
  return average_duration * SOUND_SPEED / 2; // Convert duration to distance
}


long get_reading(){
  // Clears the trigPin
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  // Sets the trigPin on HIGH state for 10 micro seconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Reads the echoPin, returns the sound wave travel time in microseconds
  long duration = pulseIn(echoPin, HIGH);
  return duration;
}


void send_message(float distancia){
  HTTPClient http;
  http.begin(endpoint_url);
  http.addHeader("Content-Type", "application/json");
 
  String payload = "{\"distancia\": " + String(distancia) + 
                 ", \"latitude\": "+String(latitude, 8)+", \"longitude\": "+String(longitude, 8)+", \"mac\": \"" + 
                 macString + "\"}";

  Serial.println(payload);

  int httpResponseCode = http.POST(payload);

  if (httpResponseCode > 0) {
      Serial.print("Código de resposta HTTP: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Erro na requisição: ");
      Serial.println(httpResponseCode);
    }

    // Fecha a conexão HTTP
    http.end();
  
}



















