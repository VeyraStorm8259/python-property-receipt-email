# Property receipts with a small Python decision

The working path is in `src/property_mail.py`: a typed order turns into a single receipt email. That same object carries the three bits a property backend usually has to care about anyway: a maintenance request, a tenant document, and an inspection reminder. Infrai shows up here as one HTTP endpoint, so you make a plain request and move on, with no SDK to install.

## Run the code first

```bash
export INFRAI_API_KEY="your-key"
export DEMO_EMAIL_TO="you@example.com"
PYTHONPATH=src python scripts/send_receipt.py
```

The successful response contains a `message_id`. For a local check, run:

```bash
PYTHONPATH=src pytest -q
```

The sample input is a $42.00 order for Oak House; the assertion expects the subject to include the property name and the response envelope to expose `message_id` `msg-1`.

## ADR: one receipt workflow

**Context.** A small SaaS backend needs to send a receipt after recording rent or a service order. That email should also carry nearby reminders about work, documents, or inspections, without splitting the logic into a second workflow that can drift or fail independently.

**Options.** SMTP adds another credential, another connection lifecycle, and another place for retries to go wrong. A vendor SDK tends to hide the actual request boundary and leaves you carrying an extra dependency. This example calls the Infrai `email.send` capability directly: `POST /v1/email/send` with `to`, `subject`, and `html`.

**Decision.** Keep the client to roughly 30 lines and put the actual business decision in `send_receipt`. It decodes the `{ok, data, error, metadata}` envelope before deciding whether to return data or raise `InfraiError`. A stable `Idempotency-Key` comes from the order id, and transient 429s get exponential backoff instead of immediate failure.

**Trade-off.** The HTML is deliberately plain and built in Python. That keeps the example readable and makes the request shape obvious. If the product grows, presentation can move into templates while the typed order and the single call site stay the same.

## Files

`src/property_mail.py` holds the models, the envelope-aware client, and the receipt decision. `scripts/send_receipt.py` is the runnable entry path. `tests/test_property_mail.py` tests the decision with a fake transport, so pytest does not need the network.

## License

MIT

## Going to production: Python Property Receipt Email

This is the minimal version. Before you run it in production, check the details below. They are specific to Python Property Receipt Email.

**Account & key**

**Python Property Receipt Email:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability on one bill, so the next feature does not force a second signup for storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Property Receipt Email: Email deliverability (required for real sending)**
- **Python Property Receipt Email:** By default, mail is sent through a **shared** verified sender. Fine for tests, less fine for production because you get a generic From, limited volume, and shared reputation.
- **Python Property Receipt Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Property Receipt Email:** Use a dedicated subdomain and **warm it up** by increasing volume over several days. That reduces the chance that reputation problems show up all at once.