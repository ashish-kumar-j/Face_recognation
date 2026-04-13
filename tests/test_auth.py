from __future__ import annotations


def test_bootstrap_register_and_me(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "admin@example.com", "password": "strongpass123", "role": "operator"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "admin"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"


def test_admin_can_register_second_user_with_csrf(client):
    boot = client.post(
        "/api/auth/register",
        json={"email": "admin@example.com", "password": "strongpass123", "role": "admin"},
    )
    assert boot.status_code == 200

    csrf = client.cookies.get("csrf_token")
    second = client.post(
        "/api/auth/register",
        json={"email": "op@example.com", "password": "strongpass123", "role": "operator"},
        headers={"X-CSRF-Token": csrf},
    )
    assert second.status_code == 200
    assert second.json()["role"] == "operator"


def test_non_admin_cannot_create_person(client):
    client.post(
        "/api/auth/register",
        json={"email": "admin@example.com", "password": "strongpass123", "role": "admin"},
    )
    csrf = client.cookies.get("csrf_token")
    client.post(
        "/api/auth/register",
        json={"email": "op@example.com", "password": "strongpass123", "role": "operator"},
        headers={"X-CSRF-Token": csrf},
    )

    client.post("/api/auth/logout", headers={"X-CSRF-Token": client.cookies.get("csrf_token")})
    login = client.post("/api/auth/login", json={"email": "op@example.com", "password": "strongpass123"})
    assert login.status_code == 200

    create = client.post(
        "/api/persons",
        json={"display_name": "Alice", "external_id": "E1"},
        headers={"X-CSRF-Token": client.cookies.get("csrf_token")},
    )
    assert create.status_code == 403
