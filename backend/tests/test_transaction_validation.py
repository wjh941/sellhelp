import pytest


CUSTOMER_RETURN = "\u5ba2\u6237\u9000\u8d27"


def assert_validation_error(response):
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/purchase-orders", {"supplier_id": 1, "items": [{"product_id": 1, "batch_no": "B-1", "quantity": -1, "unit_price": 1}]}),
        ("/api/sales-orders", {"customer_id": 1, "items": [{"product_id": 1, "quantity": -1, "unit_price": 0}]}),
        ("/api/returns", {"return_type": CUSTOMER_RETURN, "product_id": 1, "quantity": -1, "refund_amount": 0}),
    ],
)
def test_rejects_negative_transaction_quantity(client, path, payload):
    assert_validation_error(client.post(path, json=payload))


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/purchase-orders", {"supplier_id": 1, "items": [{"product_id": 1, "batch_no": "B-1", "quantity": 1, "unit_price": 0}]}),
        ("/api/sales-orders", {"customer_id": 1, "items": [{"product_id": 1, "quantity": 1, "unit_price": -0.01}]}),
        ("/api/returns", {"return_type": CUSTOMER_RETURN, "product_id": 1, "quantity": 1, "refund_amount": -0.01}),
    ],
)
def test_rejects_invalid_transaction_amount(client, path, payload):
    assert_validation_error(client.post(path, json=payload))


@pytest.mark.parametrize(
    ("path", "payload"),
    [("/api/purchase-orders", {"supplier_id": 1, "items": []}), ("/api/sales-orders", {"customer_id": 1, "items": []})],
)
def test_rejects_empty_order_items(client, path, payload):
    assert_validation_error(client.post(path, json=payload))


def test_rejects_unsupported_return_type(client):
    assert_validation_error(client.post("/api/returns", json={"return_type": "unknown", "product_id": 1, "quantity": 1, "refund_amount": 0}))


@pytest.mark.parametrize("path", ["/api/sales-orders", "/api/sales-orders/1/pay"])
def test_rejects_unsupported_payment_type(client, path):
    payload = {"payment_type": "unknown", "paid_amount": 0}
    if path == "/api/sales-orders":
        payload.update({"customer_id": 1, "items": [{"product_id": 1, "quantity": 1, "unit_price": 0}]})
    assert_validation_error(client.post(path, json=payload))


def test_rejects_purchase_batch_with_expiry_before_production(client):
    response = client.post(
        "/api/purchase-orders",
        json={"supplier_id": 1, "items": [{"product_id": 1, "batch_no": "B-1", "production_date": "2026-08-14", "expiry_date": "2026-08-13", "quantity": 1, "unit_price": 1}]},
    )
    assert_validation_error(response)
