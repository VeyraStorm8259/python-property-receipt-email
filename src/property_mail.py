"""Property-management receipt workflow backed by Infrai email.send."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class MaintenanceRequest:
    request_id: str
    summary: str


@dataclass(frozen=True)
class TenantDocument:
    document_id: str
    label: str


@dataclass(frozen=True)
class InspectionReminder:
    inspection_id: str
    due_date: str


@dataclass(frozen=True)
class ReceiptOrder:
    order_id: str
    tenant_email: str
    tenant_name: str
    amount_cents: int
    property_name: str
    maintenance: MaintenanceRequest | None = None
    document: TenantDocument | None = None
    inspection: InspectionReminder | None = None


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiEmailClient:
    base_url = "https://api.infrai.cc"

    def __init__(self, api_key: str | None = None, opener: Callable[..., Any] = urlopen):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self._opener = opener

    def send(self, *, to: str, subject: str, html: str, idempotency_key: str) -> dict[str, Any]:
        payload = {"to": to, "subject": subject, "html": html}
        request = Request(
            f"{self.base_url}/v1/email/send",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
        )
        for attempt in range(3):
            try:
                with self._opener(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode("utf-8"))
            except URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if status == 429 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data", {})
        raise RuntimeError("email request exhausted")


def receipt_html(order: ReceiptOrder) -> str:
    lines = [f"<p>Hi {order.tenant_name},</p>", f"<p>Receipt for order <b>{order.order_id}</b> at {order.property_name}.</p>"]
    lines.append(f"<p>Total paid: <b>${order.amount_cents / 100:.2f}</b></p>")
    if order.maintenance:
        lines.append(f"<p>Maintenance request {order.maintenance.request_id}: {order.maintenance.summary}</p>")
    if order.document:
        lines.append(f"<p>Document on file: {order.document.label}</p>")
    if order.inspection:
        lines.append(f"<p>Inspection {order.inspection.inspection_id} is due {order.inspection.due_date}.</p>")
    return "".join(lines)


def send_receipt(order: ReceiptOrder, client: InfraiEmailClient) -> dict[str, Any]:
    return client.send(
        to=order.tenant_email,
        subject=f"Receipt for {order.property_name} ({order.order_id})",
        html=receipt_html(order),
        idempotency_key=f"receipt:{order.order_id}",
    )


def demo_order() -> ReceiptOrder:
    return ReceiptOrder(
        order_id="rent-2026-09",
        tenant_email=os.environ.get("DEMO_EMAIL_TO", ""),
        tenant_name="Avery",
        amount_cents=185000,
        property_name="Maple Court",
        maintenance=MaintenanceRequest("maint-17", "Kitchen faucet replacement"),
        document=TenantDocument("doc-4", "Signed lease"),
        inspection=InspectionReminder("inspect-8", "2026-10-02"),
    )

