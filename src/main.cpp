#include <Arduino.h>
#include <WiFi.h>
#include <knx.h>
#include <knx/bau091A.h>

#include "router_config.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#define WIFI_SSID "example-wifi"
#define WIFI_PASSWORD ""
#warning "include/secrets.h absent: le firmware compilera mais ne tentera pas de connexion Wi-Fi"
#endif

HardwareSerial knxSerial(2);
Esp32Platform knxPlatform(&knxSerial);
Bau091A knxBau(knxPlatform);
KnxFacade<Esp32Platform, Bau091A> knx(knxBau);

struct Counters {
  volatile uint32_t ipRx = 0;
  volatile uint32_t ipTx = 0;
  volatile uint32_t tpRx = 0;
  volatile uint32_t tpTx = 0;
  uint32_t wifiReconnects = 0;
  uint32_t wifiDisconnects = 0;
} counters;

static bool knxStarted = false;
static wl_status_t previousWifiStatus = WL_NO_SHIELD;
static uint32_t lastWifiAttempt = 0;
static uint32_t lastStatus = 0;

static String physicalAddress(uint16_t address) {
  return String((address >> 12) & 0x0F) + "." +
         String((address >> 8) & 0x0F) + "." + String(address & 0xFF);
}

static void onKnxActivity(uint8_t info) {
  const bool secondaryTp = (info & 0x10U) != 0;
  const bool sending = (info & 0x01U) != 0;
  if (secondaryTp) {
    sending ? ++counters.tpTx : ++counters.tpRx;
  } else {
    sending ? ++counters.ipTx : ++counters.ipRx;
  }
}

static void startKnxOnce() {
  if (knxStarted || WiFi.status() != WL_CONNECTED) return;

  knxPlatform.knxUartPins(KNX_RX_PIN, KNX_TX_PIN);
  knx.readMemory();
  knx.bau().setActivityCallback(onKnxActivity);
  knx.start();
  knxStarted = true;

  Serial.printf("[KNX] pile demarree; adresse=%s; configure=%s\n",
                physicalAddress(knx.individualAddress()).c_str(),
                knx.configured() ? "oui" : "non");
  Serial.println("[SECURITE] Ne raccorder le TP qu'apres validation de la topologie et isolement du routeur existant.");
}

static void beginWifi() {
  if (strlen(WIFI_PASSWORD) == 0 || strcmp(WIFI_PASSWORD, "REMPLACER_PAR_LE_MOT_DE_PASSE") == 0) {
    Serial.println("[WIFI] secret absent: creer include/secrets.h; aucune connexion tentee");
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.setHostname(ROUTER_NAME);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiAttempt = millis();
  Serial.printf("[WIFI] connexion a %s...\n", WIFI_SSID);
}

static void serviceWifi() {
  const wl_status_t status = WiFi.status();
  if (status != previousWifiStatus) {
    if (status == WL_CONNECTED) {
      ++counters.wifiReconnects;
      Serial.printf("[WIFI] connecte IP=%s RSSI=%d dBm\n",
                    WiFi.localIP().toString().c_str(), WiFi.RSSI());
      startKnxOnce();
    } else if (previousWifiStatus == WL_CONNECTED) {
      ++counters.wifiDisconnects;
      Serial.printf("[WIFI] deconnecte (etat=%d)\n", static_cast<int>(status));
    }
    previousWifiStatus = status;
  }

  if (strlen(WIFI_PASSWORD) != 0 && status != WL_CONNECTED &&
      millis() - lastWifiAttempt >= WIFI_RETRY_INTERVAL_MS) {
    lastWifiAttempt = millis();
    WiFi.reconnect();
  }
}

static void printStatus() {
  Serial.printf("[ETAT] wifi=%s ip=%s knx=%s configure=%s PA=%s IP(rx=%lu tx=%lu) TP(rx=%lu tx=%lu) wifi(reco=%lu pertes=%lu) heap=%u\n",
                WiFi.status() == WL_CONNECTED ? "ok" : "non",
                WiFi.localIP().toString().c_str(), knxStarted ? "actif" : "attente",
                (knxStarted && knx.configured()) ? "oui" : "non",
                knxStarted ? physicalAddress(knx.individualAddress()).c_str() : "-",
                counters.ipRx, counters.ipTx, counters.tpRx, counters.tpTx,
                counters.wifiReconnects, counters.wifiDisconnects, ESP.getFreeHeap());
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(300);
  ArduinoPlatform::SerialDebug = &Serial;
  Serial.printf("\n[%s] demarrage; ESP32 rev=%d flash=%u octets\n",
                ROUTER_NAME, ESP.getChipRevision(), ESP.getFlashChipSize());
  Serial.printf("[KNX] NanoBCU UART2 RX=GPIO%d TX=GPIO%d %d 8E1\n",
                KNX_RX_PIN, KNX_TX_PIN, KNX_UART_BAUD);
  beginWifi();
}

void loop() {
  serviceWifi();
  if (knxStarted) knx.loop();

  if (millis() - lastStatus >= STATUS_INTERVAL_MS) {
    lastStatus = millis();
    printStatus();
  }
  yield();
}

