from property_mail import InfraiEmailClient, ReceiptOrder, receipt_html, send_receipt


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"ok": true, "data": {"message_id": "msg-1"}}'


def test_receipt_decision_includes_property_context_and_message_id():
    order = ReceiptOrder("o-1", "tenant@example.com", "Lee", 4200, "Oak House")
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    result = send_receipt(order, InfraiEmailClient("test-key", opener))
    assert result["message_id"] == "msg-1"
    body = calls[0][0].data.decode()
    assert '"to": "tenant@example.com"' in body
    assert "Receipt for Oak House (o-1)" in body
    assert "Total paid: <b>$42.00</b>" in receipt_html(order)
    assert calls[0][0].get_method() == "POST"
