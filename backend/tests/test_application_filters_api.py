import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.dependencies.auth import get_current_user_id
from app.main import app
from app.models import User


@pytest.fixture
def context():
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    user = User(email=f"{uuid.uuid4()}@example.com")
    other_user = User(email=f"{uuid.uuid4()}@example.com")
    db.add_all([user, other_user])
    db.flush()
    app.dependency_overrides[get_db] = lambda: (yield db)
    app.dependency_overrides[get_current_user_id] = lambda: user.id
    try:
        yield TestClient(app), user, other_user
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()


def create_job(client, company, title):
    response = client.post(
        "/api/v1/applications",
        json={"company_name": company, "job_title": title},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_search_matches_company_and_title(context):
    client, _, _ = context
    create_job(client, "Oracle Technologies", "Developer")
    create_job(client, "Acme", "Oracle Consultant")
    create_job(client, "Acme", "Python Engineer")

    response = client.get("/api/v1/applications", params={"q": "oracle"})

    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_stage_filter(context):
    client, _, _ = context
    application_id = create_job(client, "Acme", "Developer")
    client.post(
        f"/api/v1/applications/{application_id}/events",
        json={
            "event_kind": "ASSESSMENT_INVITED",
            "occurred_at": "2026-10-20T12:00:00Z",
            "client_request_id": str(uuid.uuid4()),
        },
    )

    response = client.get("/api/v1/applications", params={"stage": "ASSESSMENT"})

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_next_action_owner_filter(context):
    client, _, _ = context
    create_job(client, "Acme", "Developer")

    response = client.get("/api/v1/applications", params={"next_action_owner": "EMPLOYER"})

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_pagination_reports_total_and_page_metadata(context):
    client, _, _ = context
    for index in range(3):
        create_job(client, f"Company {index}", "Developer")

    response = client.get("/api/v1/applications", params={"page": 2, "page_size": 2})

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 1
    assert response.json()["page"] == 2
    assert response.json()["page_size"] == 2


def test_page_beyond_results_is_empty(context):
    client, _, _ = context
    create_job(client, "Acme", "Developer")

    response = client.get("/api/v1/applications", params={"page": 2, "page_size": 1})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"] == []


def test_sort_order_desc_is_supported(context):
    client, _, _ = context
    create_job(client, "Alpha Technologies", "Developer")
    create_job(client, "Zeta Systems", "Developer")

    response = client.get(
        "/api/v1/applications", params={"sort_by": "company_name", "sort_order": "desc"}
    )

    assert response.status_code == 200
    assert [item["company_name"] for item in response.json()["items"]] == [
        "Zeta Systems",
        "Alpha Technologies",
    ]


def test_blank_search_returns_all_owned_applications(context):
    client, _, _ = context
    create_job(client, "Acme", "Developer")
    create_job(client, "Nova", "Engineer")

    response = client.get("/api/v1/applications", params={"q": "   "})

    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_list_does_not_return_other_users_applications(context):
    client, _, other_user = context
    app.dependency_overrides[get_current_user_id] = lambda: other_user.id
    create_job(client, "Other User Co", "Developer")
    app.dependency_overrides[get_current_user_id] = lambda: uuid.UUID(int=0)

    response = client.get("/api/v1/applications")

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_sort_by_company_name(context):
    client, _, _ = context
    create_job(client, "Zeta Systems", "Developer")
    create_job(client, "Alpha Technologies", "Developer")
    create_job(client, "Nova Systems", "Developer")

    response = client.get(
        "/api/v1/applications", params={"sort_by": "company_name", "sort_order": "asc"}
    )

    assert response.status_code == 200
    assert [item["company_name"] for item in response.json()["items"]] == [
        "Alpha Technologies",
        "Nova Systems",
        "Zeta Systems",
    ]


def test_search_wildcards_are_literal(context):
    client, _, _ = context
    create_job(client, "Company 100%", "Engineer")
    create_job(client, "Company 100X", "Engineer")

    response = client.get("/api/v1/applications", params={"q": "100%"})

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.parametrize(
    "params",
    [
        {"page": "0"},
        {"page_size": "0"},
        {"page_size": "101"},
        {"sort_by": "invalid"},
        {"sort_order": "invalid"},
        {"q": "x" * 201},
        {"stage": "INVALID"},
    ],
)
def test_invalid_query_parameters_use_standard_error(context, params):
    client, _, _ = context

    response = client.get("/api/v1/applications", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["message"] == "Request validation failed"


def test_unauthenticated_list_uses_standard_error(context):
    client, _, _ = context
    app.dependency_overrides.pop(get_current_user_id)

    response = client.get("/api/v1/applications", params={"q": "oracle"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_not_found_uses_standard_error(context):
    client, _, _ = context
    response = client.get(f"/api/v1/applications/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"