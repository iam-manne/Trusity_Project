def test_order_lifecycle(client):
    payload = {"customer_id": "customer-1", "product_id": "product-7", "quantity": 2}
    created = client.post("/orders", json=payload)
    assert created.status_code == 201
    order_id = created.json()["order_id"]
    assert created.json()["status"] == "pending"

    fetched = client.get(f"/orders/{order_id}")
    assert fetched.status_code == 200
    assert fetched.json() | payload == fetched.json()

    listed = client.get("/orders")
    assert listed.status_code == 200
    assert [order["order_id"] for order in listed.json()] == [order_id]


def test_validation_not_found_and_health(client):
    invalid = client.post(
        "/orders", json={"customer_id": "c", "product_id": "p", "quantity": 0}
    )
    assert invalid.status_code == 422
    assert client.get("/orders/missing").status_code == 404
    assert client.get("/health").json() == {
        "status": "healthy",
        "database": "reachable",
    }
