from app.models import Users, Categories, Products, Sellers
from app.utils import db

# =========================================================================
# HELPER FUNCTION
# =========================================================================
def setup_checkout_scenario(client, app):
    """
    Prepare 2 Sellers, 1 Buyer, 2 Products with strict Relational Integrity.
    """
    with app.app_context():
        # 1. Create Users
        s1 = Users(email="split1@test.com", full_name="Seller One", role="user")
        s2 = Users(email="split2@test.com", full_name="Seller Two", role="user")
        b1 = Users(email="buyer@test.com", full_name="Buyer One", role="user")
        for u in [s1, s2, b1]:
            u.set_password("password123")
        db.session.add_all([s1, s2, b1])
        db.session.commit()

        # 2. Create Sellers Profile
        store1 = Sellers(id=s1.id, store_name="Store One", store_description="Desc")
        store2 = Sellers(id=s2.id, store_name="Store Two", store_description="Desc")
        db.session.add_all([store1, store2])
        db.session.commit()

        # 3. Create Category
        cat = Categories(name="General Category")
        db.session.add(cat)
        db.session.commit()

        # 4. Create Products linked strictly to Sellers.id (NOT Users.id)
        p1 = Products(seller_id=store1.id, category_id=cat.id, name="Item A", price=1000, stock=5, slug="item-a")
        p2 = Products(seller_id=store2.id, category_id=cat.id, name="Item B", price=2000, stock=5, slug="item-b")
        db.session.add_all([p1, p2])
        db.session.commit()
        
        p1_id = p1.id
        p2_id = p2.id

    # 5. Generate Tokens
    b1_token = client.post('/auth/login', json={"email": "buyer@test.com", "password": "password123"}).get_json()["token"]
    s1_token = client.post('/auth/login', json={"email": "split1@test.com", "password": "password123"}).get_json()["token"]
    
    # 6. Seed Cart via API
    headers = {"Authorization": f"Bearer {b1_token}"}
    client.post('/carts/items', json={"product_id": p1_id, "quantity": 2}, headers=headers)
    client.post('/carts/items', json={"product_id": p2_id, "quantity": 1}, headers=headers)

    return b1_token, s1_token, p1_id

# =========================================================================
# TEST CASES
# =========================================================================
class TestOrderAPI:
    def test_checkout_split_order(self, client, app):
        """Scenario: Ensure 1 cart is split into 2 independent Orders based on seller_id (201)"""
        b1_token, _, p1_id = setup_checkout_scenario(client, app)
        headers = {"Authorization": f"Bearer {b1_token}"}
        
        # 1. Execute Checkout
        res = client.post('/orders/checkout', json={"shipping_address": "Bandung, West Java"}, headers=headers)
        data = res.get_json()

        assert res.status_code == 201
        assert data["orders_created"] == 2 # Proof that Split-Order logic works
        
        # 2. Proof of automatic stock deduction
        with app.app_context():
            p1 = db.session.get(Products, p1_id)
            assert p1.stock == 3 # Initial 5 - 2 purchased

    def test_buyer_cancel_order(self, client, app):
        """Scenario: Buyer successfully cancels an order (200)"""
        b1_token, _, _ = setup_checkout_scenario(client, app)
        headers = {"Authorization": f"Bearer {b1_token}"}

        # Execute checkout first to generate orders
        client.post('/orders/checkout', json={"shipping_address": "Bandung, West Java"}, headers=headers)

        # Retrieve order_id from the buyer's order list
        res_orders = client.get('/orders', headers=headers)
        order_id = res_orders.get_json()["orders"][0]["id"]

        # Cancel the order
        res_cancel = client.put(f'/orders/{order_id}/status', json={"status": "cancelled"}, headers=headers)
        assert res_cancel.status_code == 200
        assert res_cancel.get_json()["order"]["status"] == "cancelled"

    def test_seller_forbidden_to_cancel(self, client, app):
        """Scenario: Sellers are forbidden from cancelling orders; they can only process/ship (403)"""
        b1_token, s1_token, _ = setup_checkout_scenario(client, app)
        
        b1_headers = {"Authorization": f"Bearer {b1_token}"}
        s1_headers = {"Authorization": f"Bearer {s1_token}"}

        # Execute checkout first via Buyer
        client.post('/orders/checkout', json={"shipping_address": "Bandung, West Java"}, headers=b1_headers)

        # PERBAIKAN: Retrieve order_id from the BUYER's dashboard (b1_headers), not the seller's
        res_orders = client.get('/orders', headers=b1_headers)
        order_id = res_orders.get_json()["orders"][0]["id"]

        # Seller attempts to cancel the order using their own token (s1_headers)
        res_cancel = client.put(f'/orders/{order_id}/status', json={"status": "cancelled"}, headers=s1_headers)
        
        assert res_cancel.status_code == 403

    def test_checkout_empty_cart(self, client, app):
        """Scenario: Reject checkout execution when user's cart is empty (400)"""
        with app.app_context():
            from app.models import Users
            b2 = Users(email="empty_buyer@test.com", full_name="Empty Buyer", role="user")
            b2.set_password("pass")
            db.session.add(b2)
            db.session.commit()
        
        b2_token = client.post('/auth/login', json={"email": "empty_buyer@test.com", "password": "pass"}).get_json()["token"]
        
        res = client.post('/orders/checkout', json={"shipping_address": "Jakarta"}, headers={"Authorization": f"Bearer {b2_token}"})
        
        assert res.status_code == 404
        assert "error" in res.get_json()

    def test_idor_prevent_buyer_accessing_others_order(self, client, app):
        """Scenario: Prevent Horizontal Privilege Escalation (IDOR) (403 or 404)"""
        b1_token, _, _ = setup_checkout_scenario(client, app)
        
        # Buyer 1 executes checkout
        client.post('/orders/checkout', json={"shipping_address": "Bandung, West Java"}, headers={"Authorization": f"Bearer {b1_token}"})
        res_b1_orders = client.get('/orders', headers={"Authorization": f"Bearer {b1_token}"})
        order_id = res_b1_orders.get_json()["orders"][0]["id"]

        # Create a completely new Buyer 2
        with app.app_context():
            from app.models import Users
            b2 = Users(email="hacker@test.com", full_name="Malicious Buyer", role="user")
            b2.set_password("pass")
            db.session.add(b2)
            db.session.commit()
        
        b2_token = client.post('/auth/login', json={"email": "hacker@test.com", "password": "pass"}).get_json()["token"]

        # Buyer 2 attempts to cancel Buyer 1's order
        res_hack = client.put(f'/orders/{order_id}/status', json={"status": "cancelled"}, headers={"Authorization": f"Bearer {b2_token}"})
        
        # System must reject with 403 (Forbidden) or 404 (Not Found to obscure order existence)
        assert res_hack.status_code in [403, 404]

    def test_checkout_ghost_product(self, client, app):
        """Scenario: Reject checkout if a product in the cart was soft-deleted by the seller (400)"""
        b1_token, s1_token, p1_id = setup_checkout_scenario(client, app)
        
        # Seller deletes the product (soft-delete) AFTER the buyer added it to the cart
        res_delete = client.delete(f'/products/{p1_id}', headers={"Authorization": f"Bearer {s1_token}"})
        assert res_delete.status_code == 200

        # Buyer attempts to checkout the cart containing the inactive product
        res_checkout = client.post('/orders/checkout', json={"shipping_address": "Bandung, West Java"}, headers={"Authorization": f"Bearer {b1_token}"})
        
        # System must detect state changes and reject the transaction
        assert res_checkout.status_code == 400
        assert "error" in res_checkout.get_json()

    def test_delete_order_immutable_constraint(self, client, app):
        """Attempt to delete order. Success only if cancelled."""
        b1_token, _, _ = setup_checkout_scenario(client, app)
        headers = {"Authorization": f"Bearer {b1_token}"}
        
        client.post('/orders/checkout', json={"shipping_address": "Bandung, West Java"}, headers=headers)
        res_orders = client.get('/orders', headers=headers)
        order_id = res_orders.get_json()["orders"][0]["id"]

        # Attempt to delete a 'pending' order (Should fail 400)
        res_del_fail = client.delete(f'/orders/{order_id}', headers=headers)
        assert res_del_fail.status_code == 400
        
        # Cancel it first
        client.put(f'/orders/{order_id}/status', json={"status": "cancelled"}, headers=headers)
        
        # Attempt to delete a 'cancelled' order (Should succeed 200)
        res_del_success = client.delete(f'/orders/{order_id}', headers=headers)
        assert res_del_success.status_code == 200

    def test_order_items_include_product_name_and_subtotal(self, client, app):
        """Scenario: Order items expose product_name and a computed subtotal (not just product_id)"""
        b1_token, _, _ = setup_checkout_scenario(client, app)
        headers = {"Authorization": f"Bearer {b1_token}"}
        client.post('/orders/checkout', json={"shipping_address": "Jl. Test No. 1"}, headers=headers)

        orders = client.get('/orders', headers=headers).get_json()["orders"]
        items = [item for order in orders for item in order["order_items"]]
        item_a = next(i for i in items if i["product_name"] == "Item A")
        assert item_a["quantity"] == 2
        assert item_a["subtotal"] == 2000.0
