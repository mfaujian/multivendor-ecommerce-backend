"""Small factories shared by the B2B test files."""
from app.models import Users, Sellers, Categories, Products, PriceTiers
from app.utils import db

PASSWORD = "password123"


def make_user(email, role="user", store_name=None, full_name=None):
    user = Users(email=email, full_name=full_name or email.split("@")[0].title() + " Test", role=role)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    if store_name:
        db.session.add(Sellers(id=user.id, store_name=store_name))
        db.session.commit()
    return user.id


def make_category(name="Electrical", parent_id=None):
    category = Categories(name=name, parent_id=parent_id)
    db.session.add(category)
    db.session.commit()
    return category.id


def make_product(seller_id, category_id, name="MCB 10A", price=50000, stock=100, tiers=None, **extra):
    product = Products(
        seller_id=seller_id, category_id=category_id, name=name, price=price, stock=stock,
        slug=f"{name.lower().replace(' ', '-')}-{seller_id}-{category_id}-{Products.query.count()}", **extra
    )
    db.session.add(product)
    db.session.commit()
    for min_qty, unit_price in (tiers or []):
        db.session.add(PriceTiers(product_id=product.id, min_qty=min_qty, unit_price=unit_price))
    db.session.commit()
    return product.id


def login(client, email):
    res = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": f"Bearer {res.get_json()['token']}"}