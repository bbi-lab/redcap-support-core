from datetime import datetime
from rss.models.user import User
from rss.models.authorized_user import AuthorizedUser


TEST_USER = User(
    user_id="123456789",
    first_name="test",
    last_name="user",
    email="testuser@uw.edu",
    created=datetime.now(),
    last_login=datetime.now(),
)


TEST_AUTHORIZED_USER = AuthorizedUser(
    user_id="123456789",
    viewer=False,
    editor=False,
    admin=False,
    created=datetime.now(),
    modified=datetime.now(),
)


TEST_AUTHORIZED_VIEWER = AuthorizedUser(
    user_id="123456789",
    viewer=True,
    editor=False,
    admin=False,
    created=datetime.now(),
    modified=datetime.now(),
)


TEST_AUTHORIZED_EDITOR = AuthorizedUser(
    user_id="123456789",
    viewer=True,
    editor=True,
    admin=False,
    created=datetime.now(),
    modified=datetime.now(),
)


TEST_AUTHORIZED_ADMIN = AuthorizedUser(
    user_id="123456789",
    viewer=True,
    editor=True,
    admin=True,
    created=datetime.now(),
    modified=datetime.now(),
)


def override_authenticated_user():
    return TEST_USER


def override_authorized_user():
    return TEST_AUTHORIZED_USER


def override_authorized_viewer():
    return TEST_AUTHORIZED_VIEWER


def override_authorized_editor():
    return TEST_AUTHORIZED_EDITOR


def override_authorized_admin():
    return TEST_AUTHORIZED_EDITOR
