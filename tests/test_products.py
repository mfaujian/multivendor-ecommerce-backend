from app.models import Users, Categories, Sellers, Products, Orders, OrderItems
from app.utils import db

def setup_product_prerequisites(client, app):
    """Prepare Category and Seller Store, then return Token & Category ID"""
    with app.app_context():
        cat = Categories.query.filter_by(name="Tech").first()
        if not cat:
            cat = Categories(name="Tech")
            db.session.add(cat)
            db.session.commit()
        cat_id = cat.id

        user = Users.query.filter_by(email="prod_seller@test.com").first()
        if not user:
            user = Users(email="prod_seller@test.com", full_name="Product Seller", role="user")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            
    res_login = client.post('/auth/login', json={"email": "prod_seller@test.com", "password": "password123"})
    token = res_login.get_json()["token"]

    # Register a store to acquire @seller_required access
    client.post('/sellers', json={"store_name": "Gadget Store"}, headers={"Authorization": f"Bearer {token}"})
    
    return token, cat_id

# =========================================================================
# TEST CASES
# =========================================================================
class TestProductAPI:
    def test_create_product_success(self, client, app):
        """Scenario: Successfully create a product and generate a UUID slug (201)"""
        token, cat_id = setup_product_prerequisites(client, app)
        headers = {"Authorization": f"Bearer {token}"}
        
        payload = {
            "category_id": cat_id,
            "name": "Laptop Pro",
            "price": 15000000,
            "stock": 10
        }
        
        res = client.post('/products', json=payload, headers=headers)
        assert res.status_code == 201
        assert "laptop-pro" in res.get_json()["product"]["slug"] # Test auto slug generation

    def test_create_product_forbidden_non_seller(self, client, app):
        """Scenario: Regular user attempts to create a product (403)"""
        with app.app_context():
            user = Users(email="buyer@test.com", full_name="Buyer", role="user")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
        
        res_login = client.post('/auth/login', json={"email": "buyer@test.com", "password": "password123"})
        token = res_login.get_json()["token"]
        
        res = client.post('/products', json={"category_id": 1, "name": "Fake Product", "price": 10}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403

    def test_get_products_with_filters(self, client, app):
        """Scenario: Test dynamic search filters and price range"""
        token, cat_id = setup_product_prerequisites(client, app)
        client.post('/products', json={
            "category_id": cat_id,
            "name": "Laptop Pro",
            "price": 15000000,
            "stock": 10
        }, headers={"Authorization": f"Bearer {token}"})

        res = client.get('/products?name=Laptop&min_price=10000000&max_price=20000000')
        assert res.status_code == 200
        assert len(res.get_json()["data"]) >= 1

    def test_update_and_delete_product(self, client, app):
        """Scenario: Test ownership RBAC during update and delete operations"""
        token, cat_id = setup_product_prerequisites(client, app)
        headers = {"Authorization": f"Bearer {token}"}
        
        client.post('/products', json={
            "category_id": cat_id,
            "name": "Laptop",
            "price": 15000000,
            "stock": 10
        }, headers=headers)

        res_list = client.get('/products?name=Laptop')
        prod_id = res_list.get_json()["data"][0]["id"]

        res_put = client.put(f'/products/{prod_id}', json={"stock": 50}, headers=headers)
        assert res_put.status_code == 200
        assert res_put.get_json()["product"]["stock"] == 50

        res_del = client.delete(f'/products/{prod_id}', headers=headers)
        assert res_del.status_code == 200

    def test_create_product_negative_value(self, client, app):
        """Scenario: Reject product creation with negative price or stock (400)"""
        token, cat_id = setup_product_prerequisites(client, app)
        
        payload = {
            "category_id": cat_id,
            "name": "Minus Product",
            "price": -15000, # Data ilegal
            "stock": -5      # Data ilegal
        }
        
        res = client.post('/products', json=payload, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 400

    def test_delete_product_active_order_guard(self, client, app):
        """Ensure product tied to active order cannot be deleted (409)"""
        token, cat_id = setup_product_prerequisites(client, app)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create Product
        res_prod = client.post('/products', json={"category_id": cat_id, "name": "Guard Test Item", "price": 100, "stock": 5}, headers=headers)
        prod_id = res_prod.get_json()["product"]["id"]

        # Create Buyer & Setup Order
        with app.app_context():
            buyer = Users(email="guard_buyer@test.com", full_name="Buyer", role="user")
            buyer.set_password("pass")
            db.session.add(buyer)
            db.session.commit()
            
            # Inject an active order directly for the test
            seller = Users.query.filter_by(email="prod_seller@test.com").first()
            order = Orders(user_id=buyer.id, seller_id=seller.id, shipping_address="Test", total_amount=100, status="pending")
            db.session.add(order)
            db.session.flush()
            db.session.add(OrderItems(order_id=order.id, product_id=prod_id, quantity=1, unit_price=100))
            db.session.commit()

        # Attempt to delete the product
        res_delete = client.delete(f'/products/{prod_id}', headers=headers)
        assert res_delete.status_code == 409
        assert "tied to one or more active orders" in res_delete.get_json()["error"]

    def test_category_filter_includes_subcategories(self, client, app):
        """Scenario: Filtering by a parent category also returns products in its subcategories"""
        token, _ = setup_product_prerequisites(client, app)
        with app.app_context():
            parent = Categories(name="Industrial Parent")
            db.session.add(parent)
            db.session.flush()
            child = Categories(name="Industrial Child", parent_id=parent.id)
            db.session.add(child)
            db.session.commit()
            parent_id, child_id = parent.id, child.id

        headers = {"Authorization": f"Bearer {token}"}
        client.post('/products', json={"category_id": child_id, "name": "Child Product", "price": 1000, "stock": 5}, headers=headers)

        by_parent = client.get(f'/products?category_id={parent_id}').get_json()["data"]
        by_child = client.get(f'/products?category_id={child_id}').get_json()["data"]
        assert [p["name"] for p in by_parent] == ["Child Product"]
        assert [p["name"] for p in by_child] == ["Child Product"]

    def test_product_response_includes_category_and_seller_names(self, client, app):
        """Scenario: Product payloads embed category and store names (no extra lookups needed)"""
        token, cat_id = setup_product_prerequisites(client, app)
        client.post('/products', json={"category_id": cat_id, "name": "Named Product", "price": 500, "stock": 1},
                    headers={"Authorization": f"Bearer {token}"})
        product = client.get('/products?name=Named').get_json()["data"][0]
        assert product["category"]["name"] == "Tech"
        assert product["seller"]["store_name"] == "Gadget Store"

    def test_products_are_listed_newest_first(self, client, app):
        """Scenario: Listing order is deterministic (highest id first)"""
        token, cat_id = setup_product_prerequisites(client, app)
        headers = {"Authorization": f"Bearer {token}"}
        for name in ("First Item", "Second Item", "Third Item"):
            client.post('/products', json={"category_id": cat_id, "name": name, "price": 10, "stock": 1}, headers=headers)
        names = [p["name"] for p in client.get('/products').get_json()["data"]]
        assert names == ["Third Item", "Second Item", "First Item"]



