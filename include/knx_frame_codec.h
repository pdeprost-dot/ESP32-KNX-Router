#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace knx_frame_codec {

constexpr size_t kMaxTpFrame = 263;       // NCN5130 extended frame, including FCS.
constexpr size_t kMaxApdu = 255;          // cEMI octet count 0..254 means 1..255 APDU bytes.
constexpr size_t kMaxCemiFrame = 264;     // Max extended TP without FCS, plus code/add-info.
constexpr size_t kMaxRoutingPacket = 6 + kMaxCemiFrame;
constexpr size_t kMaxTunnelingPacket = 10 + kMaxCemiFrame;
constexpr size_t kMaxAdditionalInfo = kMaxCemiFrame - 10;

struct CemiView {
    const uint8_t* data = nullptr;
    size_t length = 0;
    size_t controlOffset = 0;
    size_t apduOffset = 0;
    size_t apduLength = 0;
    bool extended = false;
    bool group = false;
    uint8_t hop = 0;
    uint16_t source = 0;
    uint16_t destination = 0;
};

inline uint8_t fcs(const uint8_t* data, size_t length) {
    uint8_t value = 0xff;
    for (size_t i = 0; i < length; ++i) value ^= data[i];
    return value;
}

inline bool needsDataOffset(size_t index) {
    return index != 0 && (index & 0x3f) == 0;
}

inline uint8_t dataOffsetCommand(size_t index) {
    return uint8_t(0x08 | ((index >> 6) & 0x07));
}

inline uint8_t dataServiceCommand(size_t index, size_t frameLength) {
    const uint8_t localIndex = uint8_t(index & 0x3f);
    return index + 1 == frameLength ? uint8_t(0x40 | localIndex)
                                    : uint8_t(0x80 | localIndex);
}

inline bool parseCemi(const uint8_t* data, size_t length, CemiView& out) {
    out = {};
    if (!data || length < 10 || length > kMaxCemiFrame) return false;
    const size_t additional = data[1];
    const size_t control = 2 + additional;
    if (additional > kMaxAdditionalInfo || control + 8 > length) return false;
    const uint8_t count = data[control + 6];
    if (count == 0xff) return false;
    const size_t expected = control + 8 + size_t(count);
    if (expected != length) return false;
    const bool extended = (data[control] & 0x80) == 0;
    if (!extended && count > 15) return false;
    if (data[control] & 0x40) return false;
    if (data[control + 1] & 0x0f) return false;
    out.data = data;
    out.length = length;
    out.controlOffset = control;
    out.apduOffset = control + 7;
    out.apduLength = size_t(count) + 1;
    out.extended = extended;
    out.group = (data[control + 1] & 0x80) != 0;
    out.hop = (data[control + 1] >> 4) & 7;
    out.source = uint16_t(data[control + 2]) << 8 | data[control + 3];
    out.destination = uint16_t(data[control + 4]) << 8 | data[control + 5];
    return out.apduOffset + out.apduLength == length;
}

inline bool cemiToTp(const uint8_t* cemi, size_t cemiLength, uint8_t* tp,
                     size_t capacity, size_t& tpLength, bool clearAck,
                     bool decrementHop) {
    tpLength = 0;
    CemiView view;
    if (!parseCemi(cemi, cemiLength, view)) return false;
    if (decrementHop && view.hop == 0) return false;
    const size_t length = view.extended ? cemiLength - 1 : cemiLength - 2;
    if (!tp || length > capacity || length > kMaxTpFrame) return false;
    const uint8_t* control = cemi + view.controlOffset;
    if (view.extended) {
        memcpy(tp, control, length - 1);
        if (clearAck) tp[0] &= uint8_t(~0x02);
        if (decrementHop) tp[1] = uint8_t((tp[1] & ~0x70) | ((view.hop - 1) << 4));
    } else {
        tp[0] = clearAck ? uint8_t(control[0] & ~0x02) : control[0];
        memcpy(tp + 1, control + 2, 4);
        uint8_t control2 = control[1];
        if (decrementHop) control2 = uint8_t((control2 & ~0x70) | ((view.hop - 1) << 4));
        tp[5] = uint8_t((control2 & 0xf0) | (control[6] & 0x0f));
        memcpy(tp + 6, control + 7, length - 7);
    }
    tp[length - 1] = fcs(tp, length - 1);
    tpLength = length;
    return true;
}

inline bool parseTp(const uint8_t* tp, size_t length, bool verifyFcs,
                    bool& extended, size_t& expected) {
    extended = false;
    expected = 0;
    if (!tp || length < 7 || length > kMaxTpFrame) return false;
    extended = (tp[0] & 0xd3) == 0x10;
    expected = extended ? size_t(9) + tp[6] : size_t(8) + (tp[5] & 0x0f);
    if (expected < 8 || expected > kMaxTpFrame || expected != length) return false;
    return !verifyFcs || fcs(tp, length - 1) == tp[length - 1];
}

inline bool tpToCemi(const uint8_t* tp, size_t tpLength, uint8_t messageCode,
                     uint8_t* cemi, size_t capacity, size_t& cemiLength) {
    cemiLength = 0;
    bool extended = false;
    size_t expected = 0;
    if (!parseTp(tp, tpLength, true, extended, expected)) return false;
    const size_t length = extended ? tpLength + 1 : tpLength + 2;
    if (!cemi || length > capacity || length > kMaxCemiFrame) return false;
    cemi[0] = messageCode;
    cemi[1] = 0;
    cemi[2] = tp[0];
    if (extended) {
        memcpy(cemi + 2, tp, tpLength - 1);
    } else {
        cemi[3] = tp[5] & 0xf0;
        memcpy(cemi + 4, tp + 1, 4);
        cemi[8] = tp[5] & 0x0f;
        memcpy(cemi + 9, tp + 6, size_t(cemi[8]) + 1);
    }
    cemiLength = length;
    CemiView check;
    return parseCemi(cemi, cemiLength, check);
}

inline bool setMessageCodeAndConfirm(uint8_t* cemi, size_t length,
                                     uint8_t messageCode, bool error) {
    CemiView view;
    if (!parseCemi(cemi, length, view)) return false;
    cemi[0] = messageCode;
    if (error) cemi[view.controlOffset] |= 0x01;
    else cemi[view.controlOffset] &= uint8_t(~0x01);
    return true;
}

inline bool decrementCemiHop(uint8_t* cemi, size_t length) {
    CemiView view;
    if (!parseCemi(cemi, length, view) || view.hop == 0) return false;
    uint8_t& control2 = cemi[view.controlOffset + 1];
    control2 = uint8_t((control2 & ~0x70) | ((view.hop - 1) << 4));
    return true;
}

}  // namespace knx_frame_codec
