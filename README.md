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

### Endpoints

#### GIT

<details>
<summary><code>POST</code> <code><b>/api/v1/git/</b></code></summary>

Endpoint для добавления новых объектов NVD в базу данных
#### Parameters

| name | required | data type     | description        | example                                                                                              |
|:---- |:-------- |:------------- |:------------------ |:---------------------------------------------------------------------------------------------------- |
| body | true | object (JSON) | json of nvd object | `{"cve_id": "string","json": {},"vendors": {},"cwes": {},"summary": "string","cvss2": 0,"cvss3": 0}` |

#### Responses

| http code     | content-type     |  response    |
|:-----|:-----|:-----|
| `200`     |   application/json   |   `{"count": 0,"nvds": [{"id": "string","created_at": "2024-04-27T11:06:46.627Z","updated_at": "2024-04-27T11:06:46.627Z","hash_sum": "string","cve_id": "string","json": {},"vendors": {},"cwes": {},"summary": "string","cvss2": 0,"cvss3": 0}]}`   |
|  `422`    |   application/json   |  `{"detail": [{"loc": ["string",0],"msg": "string","type": "string"}]}`    |

#### Example cUrl
```bash
curl -X 'POST' \
  'http://127.0.0.1/api/v1/nvd/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "cve_id": "string",
  "json": {},
  "vendors": {},
  "cwes": {},
  "summary": "string",
  "cvss2": 0,
  "cvss3": 0
}'
```
</details>