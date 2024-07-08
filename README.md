# Git downloader

### Prerequisites 
1. Docker
2. python

### Run
1. Run server
```shell
docker compose up --build -d
```

2. Run migrations
```shell
docker compose exec core alembic upgrade head
```
