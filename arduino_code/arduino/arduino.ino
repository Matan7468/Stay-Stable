#include <ESP8266WiFi.h>
#include <DNSServer.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <WiFiManager.h>         
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <vector>
#include <Arduino_JSON.h>
#include <string.h>
#include "AdafruitIO_WiFi.h"

#define IO_USERNAME  "matanbakva"
#define IO_KEY       "aio_OgzQ40DJCO3WVskhYoiwi1imzQMK"

AdafruitIO_WiFi *io;

AdafruitIO_Feed *feed;


String ids = WiFi.macAddress();
const char* id = ids.c_str();

String server_ip = "3.216.251.208";

 const int MPU_addr = 0x68; // I2C address of the MPU-6050
 int16_t AcX, AcY, AcZ, Tmp, GyX, GyY, GyZ;
 float ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0;
 boolean fall = false; //stores if a fall has occurred
 boolean trigger1 = false; //stores if first trigger (lower threshold) has occurred
 boolean trigger2 = false; //stores if second trigger (upper threshold) has occurred
 boolean trigger3 = false; //stores if third trigger (orientation change) has occurred
 byte trigger1count = 0; //stores the counts past since trigger 1 was set true
 byte trigger2count = 0; //stores the counts past since trigger 2 was set true
 byte trigger3count = 0; //stores the counts past since trigger 3 was set true
 int angleChange = 0;
 unsigned long prevTime = 0;
float deltaTime;

class Movement{
  private:
      double x;
      double y;
      double z;
  public:
      Movement(double x, double y, double z) {this->x=x;this->y=y;this->z=z;}
      double getX(){return this->x;}
      double getY(){return this->y;}
      double getZ(){return this->z;}
};

class Movements{
  private:
      std::vector<Movement> moves;
      int size;
  
  public:
      Movements(int size=0) {this->size=size;}
      int getSize(){return moves.size();}
      std::vector<Movement> getMoves() {return this->moves;}
      void addMove(Movement& move) {this->moves.push_back(move);}
      void clear(){this->moves.clear();}
};

Movements* moves = new Movements();

String convertMoves(){
  std::vector<Movement> myMoves = moves->getMoves();
  String ret = "[";

  for(Movement move:myMoves){
    char arr[50];
    String temp;
    sprintf(arr, "[%f,%f,%f]", move.getX(), move.getY(), move.getZ());
    temp = arr;
    ret += temp + ',';
  }
  ret.remove(ret.length()-1);
  ret += "]";
  return ret;
}


Adafruit_MPU6050 mpu;
// Set web server port number to 80
WiFiServer server(80);
unsigned long lastTimeTimer = 0;
unsigned long lastTimeCheck = 0;
// Set timer to 1 minute (60000)
unsigned long timerDelay = 3000;
unsigned long checkDelay = 10000;
void mpu_read();
void setupMpu();
void checkSettings();
bool sendShakingsData();
void sendMpuStatus();

void setupMpu(){
  while (!Serial)
    delay(10); // will pause Zero, Leonardo, etc until serial console opens

  Serial.println("Adafruit MPU6050 test!");

  // Try to initialize!
  while (1) {
    if (mpu.begin()) { 
        break;
      }
      delay(10);
      Serial.println("Failed to find MPU6050 chip");

  }
  Serial.println("MPU6050 Found!");

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  Serial.print("Accelerometer range set to: ");
  switch (mpu.getAccelerometerRange()) {
  case MPU6050_RANGE_2_G:
    Serial.println("+-2G");
    break;
  case MPU6050_RANGE_4_G:
    Serial.println("+-4G");
    break;
  case MPU6050_RANGE_8_G:
    Serial.println("+-8G");
    break;
  case MPU6050_RANGE_16_G:
    Serial.println("+-16G");
    break;
  }
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  Serial.print("Gyro range set to: ");
  switch (mpu.getGyroRange()) {
  case MPU6050_RANGE_250_DEG:
    Serial.println("+- 250 deg/s");
    break;
  case MPU6050_RANGE_500_DEG:
    Serial.println("+- 500 deg/s");
    break;
  case MPU6050_RANGE_1000_DEG:
    Serial.println("+- 1000 deg/s");
    break;
  case MPU6050_RANGE_2000_DEG:
    Serial.println("+- 2000 deg/s");
    break;
  }

  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  Serial.print("Filter bandwidth set to: ");
  switch (mpu.getFilterBandwidth()) {
  case MPU6050_BAND_260_HZ:
    Serial.println("260 Hz");
    break;
  case MPU6050_BAND_184_HZ:
    Serial.println("184 Hz");
    break;
  case MPU6050_BAND_94_HZ:
    Serial.println("94 Hz");
    break;
  case MPU6050_BAND_44_HZ:
    Serial.println("44 Hz");
    break;
  case MPU6050_BAND_21_HZ:
    Serial.println("21 Hz");
    break;
  case MPU6050_BAND_10_HZ:
    Serial.println("10 Hz");
    break;
  case MPU6050_BAND_5_HZ:
    Serial.println("5 Hz");
    break;
  }

  Serial.println("");
  delay(100);  
}

void setup() {
  Serial.begin(115200);

  Wire.begin();
  Wire.beginTransmission(MPU_addr);
  Wire.write(0x6B);  // PWR_MGMT_1 register
  Wire.write(0);     // set to zero (wakes up the MPU-6050)
  Wire.endTransmission(true);
  Serial.println("Wrote to IMU");
  Serial.println("starting.....");

  WiFiManager wifiManager;
  wifiManager.autoConnect("AutoConnectAP");
  Serial.println("Connected.");

  server.begin();

  setupMpu();

  io = new AdafruitIO_WiFi(IO_USERNAME, IO_KEY, "", "");

  io->connect();

  feed = io->feed("stay stable");
  delay(10000);
}

bool checkStatus(){
  byte error, address;
  int nDevices;
 
  nDevices = 0;
  for(address = 1; address < 127; address++ )
  {
    // The i2c_scanner uses the return value of
    // the Write.endTransmisstion to see if
    // a device did acknowledge to the address.
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
 
    if (error == 0)
    {
      if (address<16)
        Serial.print("0");
      nDevices++;
    }
    else if (error==4)
    {
      if (address<16)
        Serial.print("0");
      nDevices--;
    }    
  }
  if (nDevices <= 0){
    Serial.println("not found");
    return false;    
  }
  
      
  return true;
}

void sendCheckStatus(bool check){
  WiFiClient client;
  HTTPClient http;
  String serverPath = "http://3.216.251.208:3306/check_connection";//aws server ip: 
  // Your Domain name with URL path or IP address with path
  http.begin(client, serverPath.c_str());

  // If you need Node-RED/server authentication, insert user and password below
  //http.setAuthorization("REPLACE_WITH_SERVER_USERNAME", "REPLACE_WITH_SERVER_PASSWORD");

  String payload = "{}"; 
  
  http.addHeader("Content-Type", "application/json");
  char  buffer[20];
  sprintf(buffer, "{\"mac\":\"%s\", \"status\":%d}", id, int(check));
  String httpRequestData = buffer;
  // Send HTTP POST request
  int httpResponseCode = http.PUT(httpRequestData);
  if (httpResponseCode>0) {
    payload = http.getString();
  }
  else {
    return;
  }
  JSONVar myObject = JSON.parse(payload);
  
  // JSON.typeof(jsonVar) can be used to get the type of the var
  if (JSON.typeof(myObject) == "undefined") {
    return;
  }
}

void sendFallRequest(){
  WiFiClient client;
  HTTPClient http;
  String serverPath = "http://3.216.251.208:3306/alert";
  // Your Domain name with URL path or IP address with path
  http.begin(client, serverPath.c_str());

  // If you need Node-RED/server authentication, insert user and password below
  //http.setAuthorization("REPLACE_WITH_SERVER_USERNAME", "REPLACE_WITH_SERVER_PASSWORD");

  String payload = "{}"; 
  
  http.addHeader("Content-Type", "application/json");
  char  buffer[1000];
  sprintf(buffer, "{\"mac\":\"%s\"}", id);
  String httpRequestData = buffer;
  // Send HTTP POST request
  int httpResponseCode = http.PUT(httpRequestData);
  if (httpResponseCode>0) {
    payload = http.getString();
  }
  else {
    return;
  }
  JSONVar myObject = JSON.parse(payload);
  
  // JSON.typeof(jsonVar) can be used to get the type of the var
  if (JSON.typeof(myObject) == "undefined") {
    return;
  }
}

bool sendShakingsData(){
  WiFiClient client;
  HTTPClient http;
  String serverPath = "http://3.216.251.208:3306/vibrations";
  // Your Domain name with URL path or IP address with path
  http.begin(client, serverPath.c_str());
  // If you need Node-RED/server authentication, insert user and password below
  //http.setAuthorization("REPLACE_WITH_SERVER_USERNAME", "REPLACE_WITH_SERVER_PASSWORD");
  String payload = "{}"; 
  
  http.addHeader("Content-Type", "application/json");
  
  char  buffer[10000];
  String s = convertMoves();
  sprintf(buffer, "{\"mac\":\"%s\", \"vibrations\":%s}", id, s.c_str());
  String httpRequestData = buffer;
  http.addHeader("Content-Length", String(httpRequestData.length()));
  // Send HTTP POST request
  int httpResponseCode = http.PUT(httpRequestData);
  if (httpResponseCode>0) {
    payload = http.getString();
  }
  else {
    return false;
  }
  JSONVar myObject = JSON.parse(payload);
  
  // JSON.typeof(jsonVar) can be used to get the type of the var
  if (JSON.typeof(myObject) == "undefined") {
    return false;
  }
  return true;
}



void checkFalling(){
       mpu_read();
   ax = (AcX - 2050) / 16384.00;
   ay = (AcY - 77) / 16384.00;
   az = (AcZ - 1947) / 16384.00;
   gx = (GyX + 270) / 131.07;
   gy = (GyY - 351) / 131.07;
   gz = (GyZ + 136) / 131.07;
   // calculating Amplitute vactor for 3 axis
   float Raw_Amp = pow(pow(ax, 2) + pow(ay, 2) + pow(az, 2), 0.5);
   int Amp = Raw_Amp * 10;  // Mulitiplied by 10 bcz values are between 0 to 1
if (Amp <= 2 && trigger2 == false) { //if AM breaks lower threshold (0.4g)     
trigger1 = true;     
}   
if (trigger1 == true) {     
trigger1count++;     
if (Amp >= 12) { //if AM breaks upper threshold (3g)
       trigger2 = true;
       trigger1 = false; trigger1count = 0;
     }
   }
   if (trigger2 == true) {
     trigger2count++;
     angleChange = pow(pow(gx, 2) + pow(gy, 2) + pow(gz, 2), 0.5); 
     if (angleChange >= 30 && angleChange <= 400) { //if orientation changes by between 80-100 degrees       
trigger3 = true; trigger2 = false; trigger2count = 0;       
}   
}   
if (trigger3 == true) {     
trigger3count++;     
if (trigger3count >= 10) {
       angleChange = pow(pow(gx, 2) + pow(gy, 2) + pow(gz, 2), 0.5);
       //delay(10);
       if ((angleChange >= 0) && (angleChange <= 10)) { //if orientation changes remains between 0-10 degrees         
fall = true; trigger3 = false; trigger3count = 0;         
}       
else { //user regained normal orientation         
trigger3 = false; trigger3count = 0;         
}     
}   
}   
if (fall == true) { //in event of a fall detection     
Serial.println("FALL DETECTED"); 
sendFallRequest();
fall = false;   
}   
if (trigger2count >= 6) { //allow 0.5s for orientation change
     trigger2 = false; trigger2count = 0;
   }
   if (trigger1count >= 6) { //allow 0.5s for AM to break upper threshold
     trigger1 = false; trigger1count = 0;
   }
 }


void receiveMovement(){
    float posX = 0.0, posY = 0.0, posZ = 0.0;
    float velX = 0.0, velY = 0.0, velZ = 0.0;
    float orientationX = 0.0, orientationY = 0.0, orientationZ = 0.0;
    checkFalling();
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    float accelX = a.acceleration.x;
    float accelY = a.acceleration.y;
    float accelZ = a.acceleration.z;
  
    float gyroX = g.gyro.x;
    float gyroY = g.gyro.y;
    float gyroZ = g.gyro.z;

    deltaTime = 0.333;

    // Update velocity using accelerometer data
    velX += accelX * deltaTime;
    velY += accelY * deltaTime;
    velZ += accelZ * deltaTime;
    
    // Update position using velocity
    posX += velX;
    posY += velY;
    posZ += velZ;

    // Update orientation using gyroscope data
    orientationX += gyroX * deltaTime;
    orientationY += gyroY * deltaTime;
    orientationZ += gyroZ * deltaTime;

    Movement m(posX, posY, posZ);
    moves->addMove(m);
}

void mpu_read() {
   Wire.beginTransmission(MPU_addr);
   Wire.write(0x3B);  // starting with register 0x3B (ACCEL_XOUT_H)
   Wire.endTransmission(false);
   Wire.requestFrom(MPU_addr, 14, true); // request a total of 14 registers
   AcX = Wire.read() << 8 | Wire.read(); // 0x3B (ACCEL_XOUT_H) & 0x3C (ACCEL_XOUT_L)
   AcY = Wire.read() << 8 | Wire.read(); // 0x3D (ACCEL_YOUT_H) & 0x3E (ACCEL_YOUT_L)
   AcZ = Wire.read() << 8 | Wire.read(); // 0x3F (ACCEL_ZOUT_H) & 0x40 (ACCEL_ZOUT_L)
   Tmp = Wire.read() << 8 | Wire.read(); // 0x41 (TEMP_OUT_H) & 0x42 (TEMP_OUT_L)
   GyX = Wire.read() << 8 | Wire.read(); // 0x43 (GYRO_XOUT_H) & 0x44 (GYRO_XOUT_L)
   GyY = Wire.read() << 8 | Wire.read(); // 0x45 (GYRO_YOUT_H) & 0x46 (GYRO_YOUT_L)
   GyZ = Wire.read() << 8 | Wire.read(); // 0x47 (GYRO_ZOUT_H) & 0x48 (GYRO_ZOUT_L)
}

bool start = true;

void loop() {
  io->run();
  if(start){
    feed->save(String(id)); 
    start = false;  
  }
  bool sent = false;
  bool check = checkStatus();
  if ((millis() - lastTimeCheck) > checkDelay) {
    sendCheckStatus(check);
    lastTimeCheck = millis();
  }
  if(check){
    receiveMovement();
    if ((millis() - lastTimeTimer) > timerDelay) {
      sent = sendShakingsData();
      if(sent){
        moves->clear();   
        lastTimeTimer = millis();      
      }
    }    
  }
}

