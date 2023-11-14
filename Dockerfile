FROM python:3.11

RUN pip3 install poetry==1.7.0
WORKDIR  /code

ENV POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

COPY ./pyproject.toml /code/pyproject.toml
COPY ./poetry.lock /code/poetry.lock

RUN poetry config virtualenvs.create false
RUN poetry install --without dev --without test --no-root && rm -rf $POETRY_CACHE_DIR

COPY ./alembic /code/alembic
COPY ./alembic.ini /code/alembic.ini
COPY ./src /code/src

EXPOSE 8000

ENV PYTHONPATH "${PYTHONPATH}:/code/src"

CMD ["uvicorn", "rss.server_main:app", "--host", "0.0.0.0", "--port", "8000"]
