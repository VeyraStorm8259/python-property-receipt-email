from property_mail import InfraiEmailClient, demo_order, send_receipt


if __name__ == "__main__":
    order = demo_order()
    if not order.tenant_email:
        raise SystemExit("DEMO_EMAIL_TO is required")
    result = send_receipt(order, InfraiEmailClient())
    print(f"sent receipt: {result.get('message_id', 'accepted')}")
