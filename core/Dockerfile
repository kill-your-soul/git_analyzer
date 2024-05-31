FROM golang:1.21 AS build
WORKDIR /go/src/github.com/zricethezav/gitleaks

RUN git clone https://github.com/gitleaks/gitleaks/ .
RUN VERSION=$(git describe --tags --abbrev=0) && \
CGO_ENABLED=0 go build -o bin/gitleaks -ldflags "-X="github.com/zricethezav/gitleaks/v8/cmd.Version=${VERSION}


FROM python:3.10.11

WORKDIR /app

COPY . .
RUN apt-get update && apt-get install bash git openssh-client -y
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

RUN poetry install --no-root
COPY --from=build /go/src/github.com/zricethezav/gitleaks/bin/* /usr/bin/

RUN git config --global --add safe.directory '*'

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]