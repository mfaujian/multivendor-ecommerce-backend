from app.utils import db
from app.models import Categories
from tests.helpers import make_user, make_category, make_product, login


def seed(app):
    with app.app_context():
        s1 = make_user("sup1@test.com", store_name="Supplier One")
        s2 = make_user("sup2@test.com", store_name="Supplier Two")
        make_user("admin@test.com", role="admin")
        make_user("buyer@test.com")
        cat = make_category("Electrical")
        make_product(s1, cat, "MCB 10A", price=50000, stock=10, sku="MCB-10", brand="Schneider")
        make_product(s1, cat, "Contactor 9A", price=285000, stock=0, sku="CTR-9", brand="Schneider")
        make_product(s2, cat, "NYM Cable", price=400000, stock=5, sku="NYM-3X25", brand="Supreme")
        make_product(s2, cat, "Made To Order Panel", price=9000000, stock=0, sku="PNL-1", brand="Supreme",
                     fulfillment_type="indent", lead_time_days=14)
        return {"s1": s1, "s2": s2, "cat": cat}


def product_payload(cat, **extra):
    payload = {"category_id": cat, "name": "MCCB 100A", "price": 1450000, "stock": 14, "sku": "mccb-100",
               "brand": "PanelPro", "unit": "pcs", "min_order_qty": 1}
    payload.update(extra)
    return payload


class TestCatalogSearch:
    def test_search_matches_name_sku_and_brand(self, client, app):
        seed(app)
        names = lambda q: sorted(p["name"] for p in client.get(f"/products?search={q}").get_json()["data"])
        assert names("mcb") == ["MCB 10A"]
        assert names("nym-3x25") == ["NYM Cable"]
        assert names("schneider") == ["Contactor 9A", "MCB 10A"]
        assert client.get("/products?name=cable").get_json()["meta"]["total_items"] == 1  # legacy param

    def test_brand_filter_sort_and_in_stock(self, client, app):
        seed(app)
        res = client.get("/products?brand=schneider&sort=price_desc").get_json()["data"]
        assert [p["name"] for p in res] == ["Contactor 9A", "MCB 10A"]
        cheap_first = client.get("/products?sort=price_asc").get_json()["data"]
        assert cheap_first[0]["name"] == "MCB 10A"
        in_stock = [p["name"] for p in client.get("/products?in_stock=true&sort=name").get_json()["data"]]
        assert in_stock == ["MCB 10A", "Made To Order Panel", "NYM Cable"]  # indent counts as orderable

    def test_brands_endpoint(self, client, app):
        seed(app)
        brands = client.get("/products/brands").get_json()["brands"]
        assert brands == [{"name": "Schneider", "count": 2}, {"name": "Supreme", "count": 2}]

    def test_lookup_by_sku_is_case_insensitive_and_by_id(self, client, app):
        ids = seed(app)
        found = client.get("/products/lookup?skus=mcb-10, nym-3x25,UNKNOWN").get_json()["data"]
        assert sorted(p["sku"] for p in found) == ["MCB-10", "NYM-3X25"]
        first_id = found[0]["id"]
        assert client.get(f"/products/lookup?ids={first_id}").get_json()["data"][0]["id"] == first_id
        assert client.get("/products/lookup").get_json()["data"] == []

    def test_limit_is_capped(self, client, app):
        seed(app)
        assert client.get("/products?limit=100000").get_json()["meta"]["items_per_page"] == 100


class TestProductWriteRules:
    def test_admin_creates_for_a_supplier_with_tiers(self, client, app):
        ids = seed(app)
        admin = login(client, "admin@test.com")
        res = client.post("/products", headers=admin, json=product_payload(
            ids["cat"], seller_id=ids["s2"],
            price_tiers=[{"min_qty": 10, "unit_price": 1400000}, {"min_qty": 50, "unit_price": 1300000}]))
        assert res.status_code == 201, res.get_json()
        product = res.get_json()["product"]
        assert product["seller_id"] == ids["s2"] and product["sku"] == "MCCB-100"  # normalised
        assert [t["min_qty"] for t in product["price_tiers"]] == [10, 50]

    def test_admin_without_supplier_gets_a_clear_error(self, client, app):
        ids = seed(app)
        res = client.post("/products", headers=login(client, "admin@test.com"), json=product_payload(ids["cat"]))
        assert res.status_code == 400 and "supplier" in res.get_json()["error"].lower()

    def test_seller_cannot_create_for_someone_else_but_can_for_self(self, client, app):
        ids = seed(app)
        seller = login(client, "sup1@test.com")
        assert client.post("/products", headers=seller, json=product_payload(ids["cat"], seller_id=ids["s2"])).status_code == 403
        assert client.post("/products", headers=seller, json=product_payload(ids["cat"])).status_code == 201

    def test_plain_user_cannot_create(self, client, app):
        ids = seed(app)
        assert client.post("/products", headers=login(client, "buyer@test.com"),
                           json=product_payload(ids["cat"])).status_code == 403

    def test_sku_must_be_unique(self, client, app):
        ids = seed(app)
        admin = login(client, "admin@test.com")
        res = client.post("/products", headers=admin, json=product_payload(ids["cat"], seller_id=ids["s1"], sku="mcb-10"))
        assert res.status_code == 409

    def test_tiers_must_get_cheaper(self, client, app):
        ids = seed(app)
        admin = login(client, "admin@test.com")
        res = client.post("/products", headers=admin, json=product_payload(
            ids["cat"], seller_id=ids["s1"], price_tiers=[{"min_qty": 10, "unit_price": 1500000}]))
        assert res.status_code == 400

    def test_indent_requires_lead_time(self, client, app):
        ids = seed(app)
        res = client.post("/products", headers=login(client, "admin@test.com"), json=product_payload(
            ids["cat"], seller_id=ids["s1"], fulfillment_type="indent"))
        assert res.status_code == 400 and "lead_time_days" in res.get_json()["details"]

    def test_admin_can_edit_any_product_and_replace_tiers(self, client, app):
        ids = seed(app)
        admin = login(client, "admin@test.com")
        product_id = client.get("/products?search=mcb").get_json()["data"][0]["id"]
        res = client.put(f"/products/{product_id}", headers=admin, json={
            "price": 55000, "price_tiers": [{"min_qty": 20, "unit_price": 50000}]})
        assert res.status_code == 200 and res.get_json()["product"]["price"] == 55000
        assert len(res.get_json()["product"]["price_tiers"]) == 1
        cleared = client.put(f"/products/{product_id}", headers=admin, json={"price_tiers": []})
        assert cleared.get_json()["product"]["price_tiers"] == []

    def test_seller_cannot_edit_a_competitors_product(self, client, app):
        seed(app)
        product_id = client.get("/products?search=nym").get_json()["data"][0]["id"]  # belongs to Supplier Two
        res = client.put(f"/products/{product_id}", headers=login(client, "sup1@test.com"), json={"price": 1})
        assert res.status_code == 403


class TestSellersAndErrors:
    def test_sellers_list_is_public(self, client, app):
        seed(app)
        stores = client.get("/sellers").get_json()["stores"]
        assert [s["store_name"] for s in stores] == ["Supplier One", "Supplier Two"]

    def test_all_auth_failures_share_one_json_shape(self, client, app):
        seed(app)
        missing = client.get("/orders")
        assert missing.status_code == 401 and missing.get_json()["code"] == "token_missing"
        bad = client.get("/orders", headers={"Authorization": "Bearer not-a-jwt"})
        assert bad.status_code == 401 and bad.get_json()["code"] == "token_invalid"

    def test_cors_origins_are_trimmed(self, client, app):
        from app import create_app
        custom = create_app({
            "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SQLALCHEMY_ENGINE_OPTIONS": {}, "RATELIMIT_ENABLED": False,
            "CORS_ORIGINS": "http://localhost:3000, https://mephub.vercel.app",
        })
        res = custom.test_client().get("/health", headers={"Origin": "https://mephub.vercel.app"})
        assert res.headers.get("Access-Control-Allow-Origin") == "https://mephub.vercel.app"


class TestCategoryGuards:
    def test_cannot_delete_category_with_products(self, client, app):
        ids = seed(app)
        res = client.delete(f"/categories/{ids['cat']}", headers=login(client, "admin@test.com"))
        assert res.status_code == 409 and "product" in res.get_json()["error"]

    def test_cannot_delete_category_with_subcategories(self, client, app):
        with app.app_context():
            make_user("admin@test.com", role="admin")
            parent = make_category("Parent")
            make_category("Child", parent_id=parent)
        admin = login(client, "admin@test.com")
        res = client.delete(f"/categories/{parent}", headers=admin)
        assert res.status_code == 409 and "subcategory" in res.get_json()["error"]
        with app.app_context():
            assert Categories.query.filter_by(name="Child").first().parent_id == parent  # not orphaned

    def test_empty_category_can_be_deleted(self, client, app):
        with app.app_context():
            make_user("admin@test.com", role="admin")
            empty = make_category("Empty")
        assert client.delete(f"/categories/{empty}", headers=login(client, "admin@test.com")).status_code == 200


class TestAddresses:
    PAYLOAD = {"label": "Head Office", "recipient_name": "Budi Santoso", "phone": "081234567890",
               "address_line": "Jl. Asia Afrika No. 10", "city": "Bandung", "province": "Jawa Barat", "postal_code": "40111"}

    def test_crud_and_default_switching(self, client, app):
        with app.app_context():
            make_user("buyer@test.com")
        h = login(client, "buyer@test.com")
        first = client.post("/addresses", headers=h, json=self.PAYLOAD).get_json()["address"]
        assert first["is_default"] is True  # first address becomes the default
        second = client.post("/addresses", headers=h, json={**self.PAYLOAD, "label": "Site B", "is_default": True}).get_json()["address"]
        listed = client.get("/addresses", headers=h).get_json()["addresses"]
        assert [a["label"] for a in listed] == ["Site B", "Head Office"] and listed[0]["is_default"] is True
        assert listed[1]["is_default"] is False
        assert client.put(f"/addresses/{second['id']}", headers=h, json={"city": "Cimahi"}).get_json()["address"]["city"] == "Cimahi"
        assert client.delete(f"/addresses/{second['id']}", headers=h).status_code == 200
        remaining = client.get("/addresses", headers=h).get_json()["addresses"]
        assert len(remaining) == 1 and remaining[0]["is_default"] is True  # default is re-assigned

    def test_addresses_are_private_and_validated(self, client, app):
        with app.app_context():
            make_user("buyer@test.com")
            make_user("other@test.com")
        h1, h2 = login(client, "buyer@test.com"), login(client, "other@test.com")
        mine = client.post("/addresses", headers=h1, json=self.PAYLOAD).get_json()["address"]
        assert client.get("/addresses", headers=h2).get_json()["addresses"] == []
        assert client.put(f"/addresses/{mine['id']}", headers=h2, json={"city": "X1"}).status_code == 404
        assert client.delete(f"/addresses/{mine['id']}", headers=h2).status_code == 404
        assert client.post("/addresses", headers=h1, json={"label": "x"}).status_code == 400
        assert client.get("/addresses").status_code == 401