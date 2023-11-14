from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from tests.utils import TEST_USER


class TestStatus:
    def test_auth_verify_status(self, authenticated_api_client: TestClient):
        response = authenticated_api_client.get("/auth/verify")
        assert response.status_code == 200


class TestResponse:
    def test_auth_verify_response(self, authenticated_api_client: TestClient):
        response = authenticated_api_client.get("/auth/verify")
        assert response.json() == jsonable_encoder(TEST_USER)
