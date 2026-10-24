#pragma once

#include <Arduino.h>
#include <WiFiUdp.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>

#include "knx_intersite_l3.h"

namespace knx_intersite {

constexpr uint8_t kMaxPeers = 4;
constexpr uint8_t kQueueDepth = 8;
constexpr uint32_t kAckTimeoutMs = 3000;

enum class Mode : uint8_t { MonitorOnly = 1, Bridge = 2 };

struct PeerConfig {
    uint32_t address = 0;  // IPv4 in Arduino IPAddress host representation.
    uint32_t siteId = 0;
    uint16_t port = kDefaultPort;
    bool enabled = false;
};

struct Config {
    uint16_t version = 2;
    bool configured = false;
    bool requestedEnabled = false;
    Mode mode = Mode::MonitorOnly;
    uint32_t localSiteId = 0;
    uint16_t localPort = kDefaultPort;
    PeerConfig peers[kMaxPeers]{};
};

struct Stats {
    uint32_t txData = 0, txAck = 0, txErrors = 0, txQueueFull = 0;
    uint32_t rxData = 0, rxAck = 0, rxMalformed = 0, rxWrongPeer = 0;
    uint32_t rxDuplicate = 0, rxSelf = 0, rxQueueFull = 0;
    uint32_t rxMonitorOnly = 0;
    uint32_t ackTimeouts = 0, pendingFull = 0, lastRxMs = 0, lastAckMs = 0;
    uint32_t lastOriginSite = 0, lastBootId = 0, lastSequence = 0;
    uint32_t ackRttMinUs = 0, ackRttMaxUs = 0, ackRttTotalUs = 0, ackRttSamples = 0;
    uint16_t pendingAcks = 0;
    bool socketOpen = false, active = false;
};

struct TpEvent { uint16_t length = 0; uint8_t data[knx_frame_codec::kMaxTpFrame]{}; };

class Transport {
 public:
    bool start(const Config& config);
    void stop();
    void setNetworkReady(bool ready) { networkReady_ = ready; }
    void activate(bool enabled) { requestedActive_ = enabled; }
    bool requestedActive() const { return requestedActive_; }
    bool enqueueLocal(const uint8_t* tp, uint16_t length);
    bool receiveRemote(TpEvent& event);
    Stats snapshot() const;
    const Config& config() const { return config_; }

 private:
    struct TxEvent { uint8_t peer = 0; uint16_t length = 0; uint8_t data[knx_frame_codec::kMaxTpFrame]{}; };
    struct Pending { bool used = false; uint32_t sequence = 0, sentMs = 0, sentUs = 0; uint8_t peer = 0; };
    static void taskThunk(void* context);
    void task();
    int peerFor(uint32_t address, uint16_t port, uint32_t senderSite) const;
    void sendAck(const PacketView& packet, uint8_t peerIndex, IPAddress address, uint16_t port);
    void expireAcks(uint32_t now);

    Config config_{};
    WiFiUDP socket_;
    QueueHandle_t txQueue_ = nullptr, rxQueue_ = nullptr;
    TaskHandle_t task_ = nullptr;
    mutable portMUX_TYPE mux_ = portMUX_INITIALIZER_UNLOCKED;
    Stats stats_{};
    DuplicateCache duplicates_;
    Pending pending_[kQueueDepth]{};
    volatile bool requestedActive_ = false, networkReady_ = false, stopping_ = false;
    uint8_t enqueueStart_ = 0;
    uint32_t bootId_ = 0, sequence_ = 0;
};

bool validConfig(const Config& config);

}  // namespace knx_intersite
