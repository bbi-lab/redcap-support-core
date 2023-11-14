from fastapi.testclient import TestClient


class TestStatus:
    def test_calculated_events_status(self, api_client: TestClient):
        response = api_client.get("/api/v1/calculated-fields/events")
        assert response.status_code == 200

    def test_calculated_instruments_status(self, api_client: TestClient):
        response = api_client.get("/api/v1/calculated-fields/instruments")
        assert response.status_code == 200


class TestResponse:
    pass
