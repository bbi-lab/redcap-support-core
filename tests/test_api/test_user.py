from fastapi.testclient import TestClient


class TestStatus:
    def test_user_status(self, authenticated_api_client: TestClient):
        response = authenticated_api_client.get("/api/v1/user/me")
        assert response.status_code == 200

    def test_user_roles_status(self, authorized_api_client: TestClient):
        response = authorized_api_client.get("/api/v1/user/me/roles")
        assert response.status_code == 200

    def test_non_authenticated_user_status(self, api_client: TestClient):
        response = api_client.get("/api/v1/user/me")
        assert response.status_code == 200

    def test_non_authorized_user_roles_status(self, api_client: TestClient):
        response = api_client.get("/api/v1/user/me/roles")
        assert response.status_code == 200


class TestResponse:
    pass
