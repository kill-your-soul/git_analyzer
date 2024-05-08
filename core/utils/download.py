import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def download_content(url: str, save_path: Path) -> None:
    # Создаем директорию, если она еще не существует
    if not os.path.exists(save_path):
        os.makedirs(save_path)

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
            download_content(full_url, local_path)
        else:
            # Это файл, скачиваем его
            download_file(full_url, local_path)

def download_file(url: str, save_path: Path) -> None:
    # Получаем файл и сохраняем его
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
    else:
        print(f"Failed to download {url}")
