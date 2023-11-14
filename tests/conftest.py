from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.postgres import PostgresContainer

from rss.deps import get_project, get_db
from rss.lib.authentication import authenticate_current_user
from rss.lib.authorization import (
    authorize_current_user,
    require_authorized_admin,
    require_authorized_editor,
    require_authorized_viewer,
)
from rss.server_main import app
from rss.db.base import Base

from tests.utils import (
    override_authenticated_user,
    override_authorized_user,
    override_authorized_viewer,
    override_authorized_editor,
    override_authorized_admin,
)


POSTGRES_IMAGE = "postgres:15"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "test_password"
POSTGRES_DATABASE = "test_database"
POSTGRES_CONTAINER_PORT = 5432


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """
    Setup postgres container
    """
    postgres = PostgresContainer(
        image=POSTGRES_IMAGE,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DATABASE,
        port=POSTGRES_CONTAINER_PORT,
    )
    with postgres:
        wait_for_logs(
            postgres,
            r"UTC \[1\] LOG:  database system is ready to accept connections",
            10,
        )
        yield postgres


@pytest.fixture(scope="session")
def db(postgres_container: PostgresContainer) -> Generator[Session, None, None]:
    url = postgres_container.get_connection_url()
    engine = create_engine(url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture()
def api_client(db) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def authenticated_api_client(db) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[authenticate_current_user] = override_authenticated_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def authorized_api_client(db) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[authenticate_current_user] = override_authenticated_user
    app.dependency_overrides[authorize_current_user] = override_authorized_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def authorized_viewer_api_client(db) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[authenticate_current_user] = override_authenticated_user
    app.dependency_overrides[authorize_current_user] = override_authorized_user
    app.dependency_overrides[require_authorized_viewer] = override_authorized_viewer
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def authorized_editor_api_client(db) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[authenticate_current_user] = override_authenticated_user
    app.dependency_overrides[authorize_current_user] = override_authorized_user
    app.dependency_overrides[require_authorized_viewer] = override_authorized_viewer
    app.dependency_overrides[require_authorized_editor] = override_authorized_editor
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def authorized_admin_api_client(db) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[authenticate_current_user] = override_authenticated_user
    app.dependency_overrides[authorize_current_user] = override_authorized_user
    app.dependency_overrides[require_authorized_viewer] = override_authorized_viewer
    app.dependency_overrides[require_authorized_editor] = override_authorized_editor
    app.dependency_overrides[require_authorized_admin] = override_authorized_admin
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def redcap_connection():
    project = get_project()
    yield project
