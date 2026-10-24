#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "knx_frame_codec.h"

namespace knx_intersite {

constexpr uint32_t kMagic = 0x4b584c33UL;  // "KXL3"
constexpr uint8_t kVersion = 1;
constexpr uint8_t kHeaderSize = 36;
constexpr uint8_t kDefaultTtl = 4;
constexpr uint16_t kDefaultPort = 3672;
constexpr size_t kMaxPacket = kHeaderSize + knx_frame_codec::kMaxTpFrame;
constexpr size_t kDuplicateEntries = 32;

enum class MessageType : uint8_t { Data = 1, Ack = 2 };
enum class DecodeStatus : uint8_t {
    Ok,
    TooShort,
    BadMagic,
    BadVersion,
    BadHeader,
    BadType,
    BadFlags,
    BadLength,
    BadCrc,
    BadTtl,
    BadIdentity,
    SelfPacket,
    Duplicate,
    InvalidTp,
};

struct PacketView {
    MessageType type = MessageType::Data;
    uint8_t ttl = 0;
    uint16_t flags = 0;
    uint32_t originSite = 0;
    uint32_t senderSite = 0;
    uint32_t bootId = 0;
    uint32_t sequence = 0;
    uint32_t acknowledgedSequence = 0;
    const uint8_t* payload = nullptr;
    uint16_t payloadLength = 0;
};

inline uint16_t read16(const uint8_t* p) {
    return uint16_t(p[0]) << 8 | p[1];
}

inline uint32_t read32(const uint8_t* p) {
    return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 |
           uint32_t(p[2]) << 8 | p[3];
}

inline void write16(uint8_t* p, uint16_t value) {
    p[0] = uint8_t(value >> 8);
    p[1] = uint8_t(value);
}

inline void write32(uint8_t* p, uint32_t value) {
    p[0] = uint8_t(value >> 24);
    p[1] = uint8_t(value >> 16);
    p[2] = uint8_t(value >> 8);
    p[3] = uint8_t(value);
}

inline uint32_t crc32(const uint8_t* data, size_t length) {
    uint32_t crc = 0xffffffffUL;
    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (uint8_t bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ (0xedb88320UL & uint32_t(-int32_t(crc & 1)));
    }
    return ~crc;
}

inline uint32_t packetCrc(const uint8_t* data, size_t length) {
    uint32_t crc = 0xffffffffUL;
    for (size_t i = 0; i < length; ++i) {
        crc ^= (i >= 32 && i < 36) ? 0 : data[i];
        for (uint8_t bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ (0xedb88320UL & uint32_t(-int32_t(crc & 1)));
    }
    return ~crc;
}

inline bool encode(MessageType type, uint32_t originSite, uint32_t senderSite,
                   uint32_t bootId, uint32_t sequence,
                   uint32_t acknowledgedSequence, uint8_t ttl,
                   const uint8_t* payload, uint16_t payloadLength,
                   uint8_t* output, size_t capacity, size_t& outputLength) {
    outputLength = 0;
    if (!output || !originSite || !senderSite || !bootId || !sequence || !ttl)
        return false;
    if (type == MessageType::Data) {
        bool extended = false;
        size_t expected = 0;
        if (!payload || !payloadLength ||
            !knx_frame_codec::parseTp(payload, payloadLength, true, extended, expected))
            return false;
    } else if (type == MessageType::Ack) {
        if (payloadLength || payload || !acknowledgedSequence) return false;
    } else return false;
    const size_t length = kHeaderSize + payloadLength;
    if (length > capacity || length > kMaxPacket) return false;
    memset(output, 0, kHeaderSize);
    write32(output, kMagic);
    output[4] = kVersion;
    output[5] = uint8_t(type);
    output[6] = kHeaderSize;
    output[7] = ttl;
    write32(output + 8, originSite);
    write32(output + 12, senderSite);
    write32(output + 16, bootId);
    write32(output + 20, sequence);
    write32(output + 24, acknowledgedSequence);
    write16(output + 28, payloadLength);
    write16(output + 30, 0);  // flags v1: all bits reserved, must remain zero.
    if (payloadLength) memcpy(output + kHeaderSize, payload, payloadLength);
    write32(output + 32, 0);
    write32(output + 32, packetCrc(output, length));
    outputLength = length;
    return true;
}

inline DecodeStatus decode(const uint8_t* packet, size_t length, PacketView& out) {
    out = {};
    if (!packet || length < kHeaderSize) return DecodeStatus::TooShort;
    if (read32(packet) != kMagic) return DecodeStatus::BadMagic;
    if (packet[4] != kVersion) return DecodeStatus::BadVersion;
    if (packet[6] != kHeaderSize) return DecodeStatus::BadHeader;
    if (packet[5] != uint8_t(MessageType::Data) &&
        packet[5] != uint8_t(MessageType::Ack)) return DecodeStatus::BadType;
    if (read16(packet + 30)) return DecodeStatus::BadFlags;
    const uint16_t payloadLength = read16(packet + 28);
    if (length != size_t(kHeaderSize) + payloadLength || length > kMaxPacket)
        return DecodeStatus::BadLength;
    if (packetCrc(packet, length) != read32(packet + 32)) return DecodeStatus::BadCrc;
    if (!packet[7]) return DecodeStatus::BadTtl;
    out.type = MessageType(packet[5]);
    out.ttl = packet[7];
    out.originSite = read32(packet + 8);
    out.senderSite = read32(packet + 12);
    out.bootId = read32(packet + 16);
    out.sequence = read32(packet + 20);
    out.acknowledgedSequence = read32(packet + 24);
    out.payloadLength = payloadLength;
    out.payload = payloadLength ? packet + kHeaderSize : nullptr;
    if (!out.originSite || !out.senderSite || !out.bootId || !out.sequence)
        return DecodeStatus::BadIdentity;
    if (out.type == MessageType::Ack)
        return (!payloadLength && out.acknowledgedSequence) ? DecodeStatus::Ok
                                                            : DecodeStatus::BadLength;
    if (out.acknowledgedSequence || !payloadLength) return DecodeStatus::BadLength;
    bool extended = false;
    size_t expected = 0;
    if (!knx_frame_codec::parseTp(out.payload, payloadLength, true, extended, expected))
        return DecodeStatus::InvalidTp;
    return DecodeStatus::Ok;
}

struct DuplicateKey {
    uint32_t originSite = 0;
    uint32_t bootId = 0;
    uint32_t sequence = 0;
};

class DuplicateCache {
 public:
    bool containsOrInsert(uint32_t originSite, uint32_t bootId, uint32_t sequence) {
        for (const DuplicateKey& item : entries_)
            if (item.originSite == originSite && item.bootId == bootId &&
                item.sequence == sequence) return true;
        DuplicateKey& inserted = entries_[next_++];
        inserted.originSite = originSite;
        inserted.bootId = bootId;
        inserted.sequence = sequence;
        if (next_ == kDuplicateEntries) next_ = 0;
        return false;
    }
    void clear() { memset(entries_, 0, sizeof(entries_)); next_ = 0; }
 private:
    DuplicateKey entries_[kDuplicateEntries]{};
    size_t next_ = 0;
};

inline DecodeStatus validatePeer(PacketView& packet, uint32_t localSite,
                                 uint32_t expectedSenderSite,
                                 DuplicateCache* duplicates) {
    if (packet.originSite == localSite) return DecodeStatus::SelfPacket;
    if (packet.senderSite != expectedSenderSite) return DecodeStatus::BadIdentity;
    if (packet.type == MessageType::Data && duplicates &&
        duplicates->containsOrInsert(packet.originSite, packet.bootId, packet.sequence))
        return DecodeStatus::Duplicate;
    return DecodeStatus::Ok;
}

}  // namespace knx_intersite
