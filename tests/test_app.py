import pytest

import app as food


@pytest.fixture()
def client():
    return food.create_app().test_client()


def test_total_of_two_items():
    assert food.calculate_total([{"id": 1, "qty": 2}, {"id": 4, "qty": 1}]) == 1100


def test_unknown_item_rejected():
    with pytest.raises(ValueError):
        food.calculate_total([{"id": 99, "qty": 1}])


@pytest.mark.parametrize("qty", [0, -1, 1.5, "2", True])
def test_bad_quantity_rejected(qty):
    with pytest.raises(ValueError):
        food.calculate_total([{"id": 1, "qty": qty}])


def test_home_page_shows_banner_and_version(client):
    page = client.get("/").get_data(as_text=True)
    assert food.BANNER in page
    assert f"Version {food.VERSION}" in page


def test_health_endpoint(client):
    data = client.get("/health").get_json()
    assert data["status"] == "ok"
    assert data["version"] == food.VERSION


def test_menu_has_four_items(client):
    assert len(client.get("/api/menu").get_json()) == 5


def test_order_api_total(client):
    r = client.post("/api/order", json={"items": [{"id": 3, "qty": 2}]})
    assert r.status_code == 200
    assert r.get_json()["total"] == 1801


def test_order_api_rejects_empty_cart(client):
    assert client.post("/api/order", json={"items": []}).status_code == 400


def test_order_api_rejects_unknown_item(client):
    assert client.post("/api/order", json={"items": [{"id": 42, "qty": 1}]}).status_code == 400
