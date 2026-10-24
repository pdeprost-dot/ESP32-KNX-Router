#include "knx_intersite_transport.h"

#include <esp_system.h>

namespace knx_intersite {

bool validConfig(const Config& config) {
    if (config.version != 2 || !config.configured || !config.localSiteId ||
        !config.localPort) return false;
    if (config.mode != Mode::MonitorOnly && config.mode != Mode::Bridge) return false;
    uint8_t enabled = 0;
    for (uint8_t i = 0; i < kMaxPeers; ++i) {
        const PeerConfig& peer = config.peers[i];
        if (!peer.enabled) continue;
        if (!peer.address || !peer.siteId || !peer.port ||
            peer.siteId == config.localSiteId) return false;
        for (uint8_t j = 0; j < i; ++j)
            if (config.peers[j].enabled &&
                (config.peers[j].siteId == peer.siteId ||
                 config.peers[j].address == peer.address)) return false;
        ++enabled;
    }
    return enabled != 0;
}

bool Transport::start(const Config& config) {
    if (task_ || !validConfig(config)) return false;
    config_ = config;
    requestedActive_ = false;  // Never restore an active transport after boot/OTA.
    bootId_ = esp_random();
    if (!bootId_) bootId_ = 1;
    sequence_ = esp_random();
    if (!sequence_) sequence_ = 1;
    txQueue_ = xQueueCreate(kQueueDepth, sizeof(TxEvent));
    rxQueue_ = xQueueCreate(kQueueDepth, sizeof(TpEvent));
    if (!txQueue_ || !rxQueue_) return false;
    return xTaskCreatePinnedToCore(taskThunk, "knxL3", 4096, this, 2, &task_, 0) == pdPASS;
}

void Transport::stop() {
    stopping_ = true;
    requestedActive_ = false;
}

bool Transport::enqueueLocal(const uint8_t* tp, uint16_t length) {
    bool extended = false; size_t expected = 0;
    if (!requestedActive_ || !tp ||
        !knx_frame_codec::parseTp(tp, length, true, extended, expected)) return false;
    bool queued = false;
    const uint8_t first = enqueueStart_++ % kMaxPeers;
    for (uint8_t offset = 0; offset < kMaxPeers; ++offset) {
        const uint8_t i = (first + offset) % kMaxPeers;
        if (!config_.peers[i].enabled) continue;
        TxEvent event; event.peer = i; event.length = length;
        memcpy(event.data, tp, length);
        if (xQueueSend(txQueue_, &event, 0) == pdTRUE) queued = true;
        else { portENTER_CRITICAL(&mux_); ++stats_.txQueueFull; portEXIT_CRITICAL(&mux_); }
    }
    return queued;
}

bool Transport::receiveRemote(TpEvent& event) {
    return rxQueue_ && xQueueReceive(rxQueue_, &event, 0) == pdTRUE;
}

Stats Transport::snapshot() const {
    portENTER_CRITICAL(&mux_); Stats copy = stats_; portEXIT_CRITICAL(&mux_);
    return copy;
}

int Transport::peerFor(uint32_t address, uint16_t port, uint32_t senderSite) const {
    for (uint8_t i = 0; i < kMaxPeers; ++i) {
        const PeerConfig& peer = config_.peers[i];
        if (peer.enabled && peer.address == address && peer.port == port &&
            peer.siteId == senderSite) return i;
    }
    return -1;
}

void Transport::sendAck(const PacketView& packet, uint8_t peerIndex,
                        IPAddress address, uint16_t port) {
    uint8_t out[kHeaderSize]; size_t length = 0;
    if (!encode(MessageType::Ack, config_.localSiteId, config_.localSiteId,
                bootId_, ++sequence_, packet.sequence, kDefaultTtl,
                nullptr, 0, out, sizeof(out), length)) return;
    const bool sent = socket_.beginPacket(address, port) &&
                      socket_.write(out, length) == length && socket_.endPacket() == 1;
    portENTER_CRITICAL(&mux_);
    if (sent) ++stats_.txAck; else ++stats_.txErrors;
    portEXIT_CRITICAL(&mux_);
    (void)peerIndex;
}

void Transport::expireAcks(uint32_t now) {
    uint16_t pending = 0;
    for (Pending& item : pending_) {
        if (!item.used) continue;
        if (uint32_t(now - item.sentMs) >= kAckTimeoutMs) {
            item.used = false;
            portENTER_CRITICAL(&mux_); ++stats_.ackTimeouts; portEXIT_CRITICAL(&mux_);
        } else ++pending;
    }
    portENTER_CRITICAL(&mux_); stats_.pendingAcks = pending; portEXIT_CRITICAL(&mux_);
}

void Transport::taskThunk(void* context) { static_cast<Transport*>(context)->task(); }

void Transport::task() {
    bool open = false, previouslyWanted = false;
    uint8_t packet[kMaxPacket];
    while (!stopping_) {
        const bool wanted = requestedActive_ && networkReady_;
        if (previouslyWanted && !wanted) {
            xQueueReset(txQueue_); xQueueReset(rxQueue_);
            memset(pending_, 0, sizeof(pending_));
            portENTER_CRITICAL(&mux_); stats_.pendingAcks = 0; portEXIT_CRITICAL(&mux_);
        }
        previouslyWanted = wanted;
        if (open && !wanted) {
            socket_.stop(); open = false; duplicates_.clear();
        }
        if (!open && wanted) open = socket_.begin(config_.localPort) == 1;
        portENTER_CRITICAL(&mux_); stats_.socketOpen = open; stats_.active = open && wanted; portEXIT_CRITICAL(&mux_);
        if (!open) { vTaskDelay(pdMS_TO_TICKS(20)); continue; }

        TxEvent tx;
        if (xQueueReceive(txQueue_, &tx, 0) == pdTRUE && tx.peer < kMaxPeers) {
            const PeerConfig& peer = config_.peers[tx.peer];
            Pending* tracking = nullptr;
            for (Pending& item : pending_) if (!item.used) { tracking = &item; break; }
            if (!tracking) {
                portENTER_CRITICAL(&mux_); ++stats_.pendingFull; portEXIT_CRITICAL(&mux_);
                expireAcks(millis());
                vTaskDelay(pdMS_TO_TICKS(2));
                continue;
            }
            size_t length = 0; const uint32_t sequence = ++sequence_;
            if (encode(MessageType::Data, config_.localSiteId, config_.localSiteId,
                       bootId_, sequence, 0, kDefaultTtl, tx.data, tx.length,
                       packet, sizeof(packet), length)) {
                IPAddress address(peer.address);
                const bool sent = socket_.beginPacket(address, peer.port) &&
                    socket_.write(packet, length) == length && socket_.endPacket() == 1;
                portENTER_CRITICAL(&mux_);
                if (sent) ++stats_.txData; else ++stats_.txErrors;
                portEXIT_CRITICAL(&mux_);
                if (sent) { tracking->used = true; tracking->sequence = sequence; tracking->sentMs = millis(); tracking->sentUs = micros(); tracking->peer = tx.peer; }
            }
        }

        const int available = socket_.parsePacket();
        if (available > 0) {
            const IPAddress remote = socket_.remoteIP(); const uint16_t remotePort = socket_.remotePort();
            if (size_t(available) > sizeof(packet) || socket_.read(packet, min(size_t(available), sizeof(packet))) != min(size_t(available), sizeof(packet))) {
                portENTER_CRITICAL(&mux_); ++stats_.rxMalformed; portEXIT_CRITICAL(&mux_);
            } else {
                PacketView view; DecodeStatus status = decode(packet, available, view);
                const int peer = status == DecodeStatus::Ok ? peerFor(uint32_t(remote), remotePort, view.senderSite) : -1;
                if (status != DecodeStatus::Ok) { portENTER_CRITICAL(&mux_); ++stats_.rxMalformed; portEXIT_CRITICAL(&mux_); }
                else if (peer < 0) { portENTER_CRITICAL(&mux_); ++stats_.rxWrongPeer; portEXIT_CRITICAL(&mux_); }
                else if (view.originSite == config_.localSiteId) { portENTER_CRITICAL(&mux_); ++stats_.rxSelf; portEXIT_CRITICAL(&mux_); }
                else if (view.type == MessageType::Ack) {
                    bool matched = false; uint32_t rtt = 0; for (Pending& item : pending_) if (item.used && item.peer == peer && item.sequence == view.acknowledgedSequence) { rtt = micros() - item.sentUs; item.used = false; matched = true; break; }
                    portENTER_CRITICAL(&mux_); if (matched) { ++stats_.rxAck; stats_.lastAckMs = millis(); ++stats_.ackRttSamples; stats_.ackRttTotalUs += rtt; if (!stats_.ackRttMinUs || rtt < stats_.ackRttMinUs) stats_.ackRttMinUs = rtt; if (rtt > stats_.ackRttMaxUs) stats_.ackRttMaxUs = rtt; } portEXIT_CRITICAL(&mux_);
                } else {
                    const bool duplicate = duplicates_.containsOrInsert(view.originSite, view.bootId, view.sequence);
                    sendAck(view, peer, remote, remotePort);
                    if (duplicate) { portENTER_CRITICAL(&mux_); ++stats_.rxDuplicate; portEXIT_CRITICAL(&mux_); }
                    else if (config_.mode == Mode::MonitorOnly) { portENTER_CRITICAL(&mux_); ++stats_.rxData; ++stats_.rxMonitorOnly; stats_.lastRxMs = millis(); stats_.lastOriginSite = view.originSite; stats_.lastBootId = view.bootId; stats_.lastSequence = view.sequence; portEXIT_CRITICAL(&mux_); }
                    else { TpEvent event; event.length = view.payloadLength; memcpy(event.data, view.payload, event.length); if (xQueueSend(rxQueue_, &event, 0) != pdTRUE) { portENTER_CRITICAL(&mux_); ++stats_.rxQueueFull; portEXIT_CRITICAL(&mux_); } else { portENTER_CRITICAL(&mux_); ++stats_.rxData; stats_.lastRxMs = millis(); stats_.lastOriginSite = view.originSite; stats_.lastBootId = view.bootId; stats_.lastSequence = view.sequence; portEXIT_CRITICAL(&mux_); } }
                }
            }
        }
        expireAcks(millis());
        vTaskDelay(pdMS_TO_TICKS(2));
    }
    if (open) socket_.stop();
    task_ = nullptr;
    vTaskDelete(nullptr);
}

}  // namespace knx_intersite
