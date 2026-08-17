from app.models.all_models import Role, SystemConfig


def seed_builtin_roles(db):
    db.add_all(
        [
            Role(code="owner", name="Owner"),
            Role(code="warehouse_operator", name="Warehouse operator"),
            Role(code="sales_clerk", name="Sales clerk"),
        ]
    )
    db.commit()


def set_standalone_mode(db, enabled):
    config = db.query(SystemConfig).filter_by(key="standalone_mode").first()
    if config is None:
        config = SystemConfig(key="standalone_mode", value="true" if enabled else "false")
        db.add(config)
    else:
        config.value = "true" if enabled else "false"
    db.commit()


def create_account(client, username, role):
    response = client.post(
        "/api/auth/users",
        json={
            "username": username,
            "display_name": username.title(),
            "password": "phase2-password",
            "role_codes": [role],
        },
    )
    assert response.status_code == 201
    return response.json()


def login_headers(client, username):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "phase2-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_standalone_mode_exposes_virtual_owner_without_login(client):
    """Removing the compatibility path would force legacy single-machine use through login."""
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": None,
        "username": "standalone",
        "display_name": "Standalone operator",
        "role_codes": ["owner"],
        "standalone_mode": True,
    }


def test_disabled_standalone_mode_rejects_unauthenticated_business_write(client, db_session):
    """Removing the global guard would let an unauthenticated caller create inventory master data."""
    set_standalone_mode(db_session, False)

    response = client.post("/api/products", json={"name": "Unprotected", "unit": "box"})

    assert response.status_code == 401


def test_role_rules_protect_owner_actions_allow_assigned_workflow_and_revoke_logout_token(client, db_session, monkeypatch):
    """Changing a role rule, logout version, or audit protection must expose a real access-control failure."""
    monkeypatch.setenv("SELLHELP_JWT_SECRET", "test-only-jwt-secret-must-be-32-chars")
    seed_builtin_roles(db_session)
    create_account(client, "owner", "owner")
    create_account(client, "warehouse", "warehouse_operator")
    create_account(client, "sales", "sales_clerk")
    set_standalone_mode(db_session, False)

    owner_headers = login_headers(client, "owner")
    warehouse_headers = login_headers(client, "warehouse")
    sales_headers = login_headers(client, "sales")

    assert client.post("/api/products", json={"name": "Blocked", "unit": "box"}, headers=sales_headers).status_code == 403
    assert client.post("/api/system/backup", headers=warehouse_headers).status_code == 403
    assert client.post("/api/products", json={"name": "Blocked", "unit": "box"}, headers=warehouse_headers).status_code == 403
    assert client.post("/api/purchase-orders", json={}, headers=warehouse_headers).status_code == 422
    assert client.post("/api/sales-orders", json={}, headers=sales_headers).status_code == 422

    audit_response = client.get("/api/audit-logs", headers=owner_headers)
    assert audit_response.status_code == 200
    assert audit_response.json()["total"] >= 3
    assert client.delete("/api/audit-logs/1", headers=owner_headers).status_code == 404

    assert client.post("/api/auth/logout", headers=sales_headers).status_code == 200
    assert client.get("/api/products", headers=sales_headers).status_code == 401
