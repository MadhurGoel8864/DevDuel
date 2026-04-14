import unittest

from app.api.bidding.services import event_bus


class TestBiddingEventBus(unittest.TestCase):
    def test_build_channel(self) -> None:
        self.assertEqual(
            event_bus.build_channel("contest-123"),
            "contest:contest-123:bidding",
        )

    def test_extract_contest_id(self) -> None:
        self.assertEqual(
            event_bus._extract_contest_id("contest:abc:bidding"),
            "abc",
        )
        self.assertIsNone(event_bus._extract_contest_id("contest:abc:other"))
        self.assertIsNone(event_bus._extract_contest_id("bad-format"))

    def test_build_envelope_shape(self) -> None:
        envelope = event_bus._build_envelope(
            contest_id="contest-1",
            payload={"type": "NEW_HIGHEST_BID", "amount": 10},
        )
        self.assertEqual(envelope["contest_id"], "contest-1")
        self.assertEqual(envelope["event_type"], "NEW_HIGHEST_BID")
        self.assertEqual(envelope["payload"]["amount"], 10)
        self.assertIn("event_id", envelope)
        self.assertIn("server_time", envelope)
        self.assertIn("producer_instance", envelope)


if __name__ == "__main__":
    unittest.main()
