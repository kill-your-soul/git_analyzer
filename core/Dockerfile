FROM python:3.10.11

WORKDIR /app

COPY . .
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

RUN poetry install --no-root

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]