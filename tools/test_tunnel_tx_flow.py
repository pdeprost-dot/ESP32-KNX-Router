#!/usr/bin/env python3
"""Independent model checks for KNXnet/IP server outbound stop-and-wait flow."""

from collections import deque


class Flow:
    def __init__(self, depth=8, timeout_ms=1000, max_retries=2):
        self.queue = deque(maxlen=depth)
        self.depth = depth
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self.next_sequence = 0
        self.outstanding = None
        self.sent_ms = 0
        self.retries = self.timeouts = self.drops = self.acks = 0

    def enqueue(self, value):
        if len(self.queue) == self.depth:
            self.drops += 1
            return False
        self.queue.append(value)
        return True

    def service(self, now):
        if not self.queue:
            return None
        if self.outstanding is None:
            self.outstanding = self.next_sequence
            self.next_sequence = (self.next_sequence + 1) & 0xFF
            self.sent_ms = now
            return self.outstanding, self.queue[0], False
        if now - self.sent_ms < self.timeout_ms:
            return None
        if self.retries < self.max_retries:
            self.retries += 1
            self.sent_ms = now
            return self.outstanding, self.queue[0], True
        self.timeouts += 1
        self.outstanding = None
        self.queue.popleft()
        return None

    def ack(self, sequence):
        if sequence != self.outstanding:
            return False
        self.acks += 1
        self.outstanding = None
        self.queue.popleft()
        return True


def test_stop_and_wait():
    flow = Flow()
    assert flow.enqueue(b"first") and flow.enqueue(b"second")
    assert flow.service(0) == (0, b"first", False)
    assert flow.service(1) is None
    assert flow.ack(0)
    assert flow.service(2) == (1, b"second", False)
    assert flow.ack(1)
    assert not flow.queue and flow.acks == 2


def test_retry_keeps_sequence_and_payload():
    flow = Flow()
    flow.enqueue(b"one")
    assert flow.service(0) == (0, b"one", False)
    assert flow.service(1000) == (0, b"one", True)
    assert flow.service(2000) == (0, b"one", True)
    assert flow.service(3000) is None
    assert flow.timeouts == 1 and not flow.queue


def test_bounded_queue_and_wrap():
    flow = Flow(depth=2)
    assert flow.enqueue(1) and flow.enqueue(2) and not flow.enqueue(3)
    flow.next_sequence = 255
    assert flow.service(0)[0] == 255
    assert flow.ack(255)
    assert flow.service(1)[0] == 0
    assert flow.drops == 1


if __name__ == "__main__":
    test_stop_and_wait()
    test_retry_keeps_sequence_and_payload()
    test_bounded_queue_and_wrap()
    print("tunnel TX flow tests: OK")
