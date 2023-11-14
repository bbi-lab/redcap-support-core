from fastapi.testclient import TestClient


class TestStatus:
    def test_ping_status(self, api_client: TestClient):
        response = api_client.get("/api/v1/ping")
        assert response.status_code == 200


class TestResponse:
    def test_ping_response(self, api_client: TestClient):
        response = api_client.get("/api/v1/ping")
        assert response.json() == {"ping": "pong"}
