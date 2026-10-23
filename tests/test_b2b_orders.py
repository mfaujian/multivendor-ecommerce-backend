from datetime import date, timedelta
from app.models import Products
from app.utils import db
from tests.helpers import make_user, make_category, make_product, login


def setup_market(app):
    """Two suppliers, one buyer, one admin, three products."""
    with app.app_context():
        s1 = make_user("sup1@test.com", store_name="Supplier One")
        s2 = make_user("sup2@test.com", store_name="Supplier Two")
        make_user("buyer@test.com", full_name="Budi Buyer")
        make_user("admin@test.com", role="admin", full_name="Admin Test")
        cat = make_category("Electrical")
        mcb = make_product(s1, cat, "MCB 10A", price=50000, stock=100, sku="MCB-10", min_order_qty=2,
                           tiers=[(10, 45000), (50, 40000)])
        cable = make_product(s2, cat, "NYM Cable", price=400000, stock=5, sku="NYM-3X25", unit="roll")
        panel = make_product(s2, cat, "Custom Panel", price=9000000, stock=0, sku="PNL-CUSTOM",
                             fulfillment_type="indent", lead_time_days=21)
        return {"mcb": mcb, "cable": cable, "panel": panel, "cat": cat, "s1": s1, "s2": s2}


ADDRESS = "Jl. Braga No. 1, Bandung"


class TestCreateOrder:
    def test_splits_by_supplier_and_decrements_stock(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["mcb"], "quantity": 5}, {"product_id": ids["cable"], "quantity": 2}],
            "shipping_address": ADDRESS,
        })
        assert res.status_code == 201, res.get_json()
        data = res.get_json()
        assert data["orders_created"] == 2
        with app.app_context():
            assert db.session.get(Products, ids["mcb"]).stock == 95
            assert db.session.get(Products, ids["cable"]).stock == 3

    def test_price_comes_from_the_server_not_the_client(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["mcb"], "quantity": 2, "unit_price": 1}],
            "shipping_address": ADDRESS,
        })
        assert res.status_code == 400  # unknown field is rejected
        ok = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["mcb"], "quantity": 2}], "shipping_address": ADDRESS,
        }).get_json()
        assert ok["orders"][0]["order_items"][0]["unit_price"] == 50000
        assert ok["orders"][0]["total_amount"] == 100000

    def test_volume_tier_price_is_applied(self, client, app):
        ids = setup_market(app)
        with app.app_context():
            db.session.get(Products, ids["mcb"]).stock = 1000  # enough for all four orders below
            db.session.commit()
        h = login(client, "buyer@test.com")
        for qty, expected in [(9, 50000), (10, 45000), (49, 45000), (50, 40000)]:
            order = client.post("/orders", headers=h, json={
                "items": [{"product_id": ids["mcb"], "quantity": qty}], "shipping_address": ADDRESS,
            }).get_json()["orders"][0]
            assert order["order_items"][0]["unit_price"] == expected
            assert order["total_amount"] == expected * qty

    def test_duplicate_lines_are_merged(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["mcb"], "quantity": 6}, {"product_id": ids["mcb"], "quantity": 4}],
            "shipping_address": ADDRESS,
        })
        assert res.status_code == 201
        item = res.get_json()["orders"][0]["order_items"][0]
        assert item["quantity"] == 10 and item["unit_price"] == 45000  # merged qty reaches the tier

    def test_minimum_order_quantity_is_enforced(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["mcb"], "quantity": 1}], "shipping_address": ADDRESS,
        })
        assert res.status_code == 422
        assert res.get_json()["details"][0]["product_id"] == ids["mcb"]
        assert "Minimum order" in res.get_json()["details"][0]["message"]

    def test_insufficient_stock_rolls_everything_back(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["mcb"], "quantity": 5}, {"product_id": ids["cable"], "quantity": 99}],
            "shipping_address": ADDRESS,
        })
        assert res.status_code == 422
        with app.app_context():
            assert db.session.get(Products, ids["mcb"]).stock == 100  # untouched

    def test_indent_product_ignores_stock(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["panel"], "quantity": 2}], "shipping_address": ADDRESS,
        })
        assert res.status_code == 201
        with app.app_context():
            assert db.session.get(Products, ids["panel"]).stock == 0  # not decremented, not negative

    def test_cannot_order_own_product(self, client, app):
        ids = setup_market(app)
        h = login(client, "sup1@test.com")
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["mcb"], "quantity": 2}], "shipping_address": ADDRESS,
        })
        assert res.status_code == 422

    def test_b2b_fields_and_payment_terms(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        tomorrow = (date.today() + timedelta(days=3)).isoformat()
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["cable"], "quantity": 1}], "shipping_address": ADDRESS,
            "po_number": "PO-2026-001", "notes": "Deliver before 10:00",
            "payment_method": "request_terms", "requested_delivery_date": tomorrow,
        })
        order = res.get_json()["orders"][0]
        assert order["po_number"] == "PO-2026-001"
        assert order["payment_method"] == "request_terms"
        assert order["payment_status"] == "terms_requested"
        assert order["requested_delivery_date"] == tomorrow
        assert order["order_items"][0]["sku"] == "NYM-3X25"

    def test_past_delivery_date_is_rejected(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["cable"], "quantity": 1}], "shipping_address": ADDRESS,
            "requested_delivery_date": "2020-01-01",
        })
        assert res.status_code == 400

    def test_address_is_required_and_saved_address_is_snapshotted(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        no_addr = client.post("/orders", headers=h, json={"items": [{"product_id": ids["cable"], "quantity": 1}]})
        assert no_addr.status_code == 400
        addr = client.post("/addresses", headers=h, json={
            "label": "Site A", "recipient_name": "Pak Joko", "phone": "08123456789",
            "address_line": "Jl. Industri No. 5", "city": "Bandung", "province": "Jawa Barat", "postal_code": "40111",
        }).get_json()["address"]
        res = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["cable"], "quantity": 1}], "shipping_address_id": addr["id"],
        })
        assert "Pak Joko" in res.get_json()["orders"][0]["shipping_address"]

    def test_requires_login_and_non_empty_items(self, client, app):
        setup_market(app)
        assert client.post("/orders", json={"items": []}).status_code == 401
        h = login(client, "buyer@test.com")
        assert client.post("/orders", headers=h, json={"items": [], "shipping_address": ADDRESS}).status_code == 400


class TestAdminOrders:
    def _order(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["mcb"], "quantity": 2}, {"product_id": ids["cable"], "quantity": 1}],
            "shipping_address": ADDRESS, "po_number": "PO-777",
        })
        return ids

    def test_all_orders_is_admin_only(self, client, app):
        self._order(client, app)
        assert client.get("/orders/all").status_code == 401
        assert client.get("/orders/all", headers=login(client, "buyer@test.com")).status_code == 403

    def test_all_orders_lists_every_buyer_with_names(self, client, app):
        self._order(client, app)
        res = client.get("/orders/all", headers=login(client, "admin@test.com"))
        body = res.get_json()
        assert res.status_code == 200 and body["meta"]["total_items"] == 2
        assert body["orders"][0]["buyer"]["full_name"] == "Budi Buyer"
        assert body["orders"][0]["seller"]["store_name"].startswith("Supplier")

    def test_all_orders_filters_and_search(self, client, app):
        self._order(client, app)
        admin = login(client, "admin@test.com")
        assert client.get("/orders/all?status=cancelled", headers=admin).get_json()["meta"]["total_items"] == 0
        assert client.get("/orders/all?search=PO-777", headers=admin).get_json()["meta"]["total_items"] == 2
        assert client.get("/orders/all?search=budi", headers=admin).get_json()["meta"]["total_items"] == 2
        assert client.get("/orders/all?search=nobody", headers=admin).get_json()["meta"]["total_items"] == 0
        assert client.get("/orders/all?limit=1", headers=admin).get_json()["meta"]["total_pages"] == 2

    def test_admin_can_mark_paid_but_buyer_cannot(self, client, app):
        self._order(client, app)
        admin = login(client, "admin@test.com")
        order_id = client.get("/orders/all", headers=admin).get_json()["orders"][0]["id"]
        buyer = login(client, "buyer@test.com")
        assert client.put(f"/orders/{order_id}/payment", headers=buyer, json={"payment_status": "paid"}).status_code == 403
        res = client.put(f"/orders/{order_id}/payment", headers=admin, json={"payment_status": "paid"})
        assert res.status_code == 200 and res.get_json()["order"]["payment_status"] == "paid"
        # terms statuses make no sense for a bank-transfer order
        assert client.put(f"/orders/{order_id}/payment", headers=admin,
                          json={"payment_status": "terms_approved"}).status_code == 400

    def test_admin_can_open_any_order_detail(self, client, app):
        self._order(client, app)
        admin = login(client, "admin@test.com")
        order_id = client.get("/orders/all", headers=admin).get_json()["orders"][0]["id"]
        assert client.get(f"/orders/{order_id}", headers=admin).status_code == 200


class TestCancellation:
    def test_cancel_restores_stock_only_for_stock_products(self, client, app):
        ids = setup_market(app)
        h = login(client, "buyer@test.com")
        order = client.post("/orders", headers=h, json={
            "items": [{"product_id": ids["cable"], "quantity": 2}, {"product_id": ids["panel"], "quantity": 1}],
            "shipping_address": ADDRESS,
        }).get_json()["orders"][0]
        # the order is split by supplier; both products belong to supplier two, so it is a single order
        res = client.put(f"/orders/{order['id']}/status", headers=h, json={"status": "cancelled"})
        assert res.status_code == 200
        with app.app_context():
            assert db.session.get(Products, ids["cable"]).stock == 5   # 5 - 2 + 2
            assert db.session.get(Products, ids["panel"]).stock == 0   # indent: unchanged, not 1