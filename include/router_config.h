#pragma once

#define KNX_TRANSPORT_ETHERNET 1
#define KNX_TRANSPORT_WIFI 2
#ifndef KNX_NETWORK_TRANSPORT
#define KNX_NETWORK_TRANSPORT KNX_TRANSPORT_WIFI
#endif

#define TP1_MODE_PHYSICAL 1
#define TP1_MODE_SIMULATED 2
#ifndef TP1_INTERFACE_MODE
#define TP1_INTERFACE_MODE TP1_MODE_PHYSICAL
#endif
#if TP1_INTERFACE_MODE != TP1_MODE_PHYSICAL && TP1_INTERFACE_MODE != TP1_MODE_SIMULATED
#error "TP1_INTERFACE_MODE must be TP1_MODE_PHYSICAL or TP1_MODE_SIMULATED"
#endif
#ifndef TP1_SIM_CONFIRM_DELAY_MS
#define TP1_SIM_CONFIRM_DELAY_MS 20UL
#endif
#if KNX_NETWORK_TRANSPORT != KNX_TRANSPORT_ETHERNET && KNX_NETWORK_TRANSPORT != KNX_TRANSPORT_WIFI
#error "KNX_NETWORK_TRANSPORT must be KNX_TRANSPORT_ETHERNET or KNX_TRANSPORT_WIFI"
#endif

#define ROUTER_NAME "ESP32-KNX-WIFI-ROUTER"
#ifndef KNX_RX_PIN
#define KNX_RX_PIN 16
#endif
#ifndef KNX_TX_PIN
#define KNX_TX_PIN 17
#endif
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
// Outils de banc (commandes fixes, boucle UART, balayage et inversion).
// Ils ne sont ni affiches ni acceptes dans le firmware installateur.
#define KNX_DEVELOPMENT_TOOLS 0
#define NANOBCU_PROBE_INTERVAL_MS 5000UL
#define NANOBCU_FRAME_GAP_US 5000UL

