import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .celery_worker import celery_app


@celery_app.task(bind=True, name="utils.download.download_content")
def download_content(self, url: str, save_path: str) -> None:  # noqa: ANN001, ARG001

    # Создаем директорию, если она еще не существует
    try:
        save_path = Path(save_path.replace(":", "_"))
        # Создаем директорию, если она еще не существует
        os.makedirs(save_path, exist_ok=True)

        # Загружаем содержимое страницы
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Перебираем все ссылки
        for link in soup.find_all('a'):
            href = link.get('href')
            if not href:
                continue

            # Полный URL для файла или директории
            full_url = requests.compat.urljoin(url, href)
            local_path = os.path.join(save_path, href)

            if href.endswith('/'):
                # Если ссылка оканчивается на '/', это директория
                # download_content(str(full_url), local_path)
                download_content.apply_async(args=[str(full_url), str(local_path)])
            else:
                # Это файл, скачиваем его
                download_file(str(full_url), str(local_path))
        return {"status": "success", "url": str(url), "path": str(save_path)}
    except Exception as e:
        return {"status": "error", "url": str(url), "error": str(e)}


def download_file(url: str, save_path: str) -> None:
    # Получаем файл и сохраняем его
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            file.write(response.content)
    else:
        print(f"Failed to download {url}")
