#pragma once

#define ROUTER_NAME "ESP32-KNX-WIFI-ROUTER"
#define KNX_RX_PIN 16
#define KNX_TX_PIN 17
#define KNX_UART_BAUD 19200
#define SERIAL_BAUD 115200
#define WIFI_CONNECT_TIMEOUT_MS 30000UL
#define WIFI_RETRY_INTERVAL_MS 10000UL
#define STATUS_INTERVAL_MS 30000UL

// Verrou de mise en service. Ne passer à 1 qu'après validation de l'adresse
// physique et de l'absence de chemin Siemens parallèle sur la même ligne.
#define ROUTING_ARMED 0
#define NANObcu_PROBE_INTERVAL_MS 5000UL

