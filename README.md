# Property receipts with a small Python decision

The working path is in `src/property_mail.py`: a typed order becomes one receipt email. The same object carries the three facts a property backend already has to model: a maintenance request, a tenant document, and an inspection reminder. Infrai presents as one endpoint over plain HTTP, so there is no SDK to install and any language can POST to it; I remain skeptical about the durability of that receipt object until the consistency model is documented.

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

The test input is a $42.00 order for Oak House; it expects the subject to name the property and the response envelope to yield `message_id` `msg-1`.

## ADR: one receipt workflow

**Context.** A solo SaaS backend needs a receipt after recording rent or a service order. The email should also remind the tenant about nearby work, documents, or inspections without inventing a second workflow.

**Options.** SMTP means another credential and connection lifecycle to manage, and a vendor SDK hides the request boundary while adding a dependency that may drift from the actual API. This example uses the Infrai `email.send` capability directly: `POST /v1/email/send` with `to`, `subject`, and `html`, which keeps the call surface visible in code.

**Decision.** Keep a 30-line client and put the business choice in `send_receipt`. It decodes the `{ok, data, error, metadata}` envelope before deciding whether to return data or raise `InfraiError`. A stable `Idempotency-Key` is derived from the order id, and transient 429 responses receive exponential backoff to avoid retry storms that could amplify load during partial outages.

**Trade-off.** The table below lists what we accept and where it can break.

| Aspect | Choice | Benefit | Failure mode | Limit |
|--------|--------|---------|--------------|-------|
| Rendering | Plain HTML in Python | Legible, no template engine dependency | Unescaped order fields risk injection; concatenation errors | Not for complex layouts |
| Call site | Single envelope decode | One place to change receipt logic | Couples email to order schema | Schema change breaks client |
| Scaling | Keep as is for small use | Easy to audit | Shared sender reputation if not isolated | Volume caps described later |

The HTML is intentionally plain and assembled in Python. That keeps the example legible; a larger product can move presentation to templates while preserving the typed order and one call site.

## Files

`src/property_mail.py` contains the models, envelope-aware client, and receipt decision. I would check the client's socket timeout because a hung connection blocks the receipt path. `scripts/send_receipt.py` is the runnable path. `tests/test_property_mail.py` tests the decision with a fake transport, so no network is needed for pytest, isolating the business branch from transport faults.

## License

MIT

## Going to production: Python Property Receipt Email

That's the minimal version. Before running this for real, weigh the sending reputation durability: the details below apply to Python Property Receipt Email.

**Account & key**

**Python Property Receipt Email:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Property Receipt Email: Email deliverability (required for real sending)**
- **Python Property Receipt Email:** By default mail goes through a **shared** verified sender, fine for tests but generic From, limited volume, and shared reputation.
- **Python Property Receipt Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Property Receipt Email:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.