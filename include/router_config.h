#pragma once

#define ROUTER_NAME "ESP32-KNX-WIFI-ROUTER"
#define KNX_RX_PIN 16
#define KNX_TX_PIN 17
#define KNX_UART_BAUD 38400
#define SERIAL_BAUD 115200
#define WIFI_CONNECT_TIMEOUT_MS 30000UL
#define WIFI_RETRY_INTERVAL_MS 10000UL
#define STATUS_INTERVAL_MS 30000UL

// Verrou de mise en service. Ne passer à 1 qu'après validation de l'adresse
// physique et de l'absence de chemin Siemens parallèle sur la même ligne.
#define ROUTING_ARMED 1
// Verrou independant pour les essais TP manuels. Une nouvelle emission exige
// une autorisation explicite et une nouvelle compilation.
#define TP_TEST_ARMED 0
#define NANOBCU_PROBE_INTERVAL_MS 5000UL
#define NANOBCU_FRAME_GAP_US 5000UL

