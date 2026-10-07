import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


def signup(c, email, name="Fulano"):
    c.post("/auth/register", json={"name": name, "email": email, "password": "123456"})
    r = c.post("/auth/login", data={"username": email, "password": "123456"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_full_flow(client):
    admin = signup(client, "admin@x.com", "Admin")      # 1º usuário = admin
    user = signup(client, "cliente@x.com", "Cliente")

    assert client.post("/products", json={"name": "Mouse", "price": "50.00", "stock": 5},
                       headers=user).status_code == 403
    cat = client.post("/categories", json={"name": "Periféricos"}, headers=admin).json()
    p = client.post("/products", headers=admin, json={
        "name": "Mouse Gamer", "price": "99.90", "stock": 5, "category_id": cat["id"]}).json()

    assert client.get("/products", params={"q": "mouse"}).json()["total"] == 1

    r = client.post("/cart/items", json={"product_id": p["id"], "quantity": 2}, headers=user)
    assert r.status_code == 201 and float(r.json()["total"]) == 199.80
    assert client.post("/cart/items", json={"product_id": p["id"], "quantity": 4},
                       headers=user).status_code == 409   # estoque

    order = client.post("/orders", headers=user).json()
    assert order["status"] == "pending" and float(order["total"]) == 199.80
    assert client.get(f"/products/{p['id']}").json()["stock"] == 3
    assert client.post("/orders", headers=user).status_code == 400  # carrinho vazio

    assert client.post(f"/orders/{order['id']}/cancel", headers=user).json()["status"] == "cancelled"
    assert client.get(f"/products/{p['id']}").json()["stock"] == 5   # estoque devolvido
    assert client.patch(f"/orders/{order['id']}/status", json={"status": "paid"},
                        headers=admin).status_code == 409


def test_auth_required(client):
    assert client.get("/cart").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer lixo"}).status_code == 401
