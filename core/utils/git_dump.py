#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import traceback
import urllib.parse
from contextlib import closing
from http import HTTPStatus
from pathlib import Path

import bs4
import dulwich.index
import dulwich.objects
import dulwich.pack
import requests
import requests.adapters
import socks
from requests_pkcs12 import Pkcs12Adapter

from .celery_worker import celery_app


def printf(fmt, *args, file=sys.stdout) -> None:  # noqa: ANN001, ANN002
    if args:
        fmt = fmt % args

    file.write(fmt)
    file.flush()


def is_html(response) -> bool:
    """Return True if the response is a HTML webpage"""
    return "Content-Type" in response.headers and "text/html" in response.headers["Content-Type"]


def is_safe_path(path):
    """Prevent directory traversal attacks"""
    if path.startswith("/"):
        return False

    safe_path = os.path.expanduser("~")
    return os.path.commonpath((os.path.realpath(os.path.join(safe_path, path)), safe_path)) == safe_path


def get_indexed_files(response):
    """Return all the files in the directory index webpage"""
    html = bs4.BeautifulSoup(response.text, "html.parser")
    files = []

    for link in html.find_all("a"):
        url = urllib.parse.urlparse(link.get("href"))

        if url.path and is_safe_path(url.path) and not url.scheme and not url.netloc:
            files.append(url.path)

    return files


def verify_response(response):
    if response.status_code != 200:
        return (
            False,
            f"[-] {response.url} responded with status code {response.status_code}\n",
        )
    elif "Content-Length" in response.headers and response.headers["Content-Length"] == 0:
        return False, f"[-] {response.url} responded with a zero-length body\n"
    elif "Content-Type" in response.headers and "text/html" in response.headers["Content-Type"]:
        return False, f"[-] {response.url} responded with HTML\n"
    else:
        return True, ""


def create_intermediate_dirs(path):
    """Create intermediate directories, if necessary"""
    dirname, basename = os.path.split(path)

    if dirname and not os.path.exists(dirname):
        try:
            os.makedirs(dirname)
        except FileExistsError:
            pass  # race condition


def get_referenced_sha1(obj_file):
    """Return all the referenced SHA1 in the given object file"""
    objs = []

    if isinstance(obj_file, dulwich.objects.Commit):
        objs.append(obj_file.tree.decode())

        for parent in obj_file.parents:
            objs.append(parent.decode())
    elif isinstance(obj_file, dulwich.objects.Tree):
        for item in obj_file.iteritems():
            objs.append(item.sha.decode())
    elif isinstance(obj_file, dulwich.objects.Blob):
        pass
    elif isinstance(obj_file, dulwich.objects.Tag):
        pass
    else:
        printf("error: unexpected object type: %r\n" % obj_file, file=sys.stderr)
        sys.exit(1)

    return objs


def download_file(session, filepath, url, directory, timeout):
    if os.path.isfile(os.path.join(directory, filepath)):
        printf("[-] Already downloaded %s/%s\n", url, filepath)
        return []

    with closing(
        session.get(
            f"{url}/{filepath}",
            allow_redirects=False,
            stream=True,
            timeout=timeout,
        )
    ) as response:
        printf(
            "[-] Fetching %s/%s [%d]\n",
            url,
            filepath,
            response.status_code,
        )

        valid, error_message = verify_response(response)
        if not valid:
            printf(error_message, file=sys.stderr)
            return []

        abspath = os.path.abspath(os.path.join(directory, filepath))
        create_intermediate_dirs(abspath)

        # write file
        with open(abspath, "wb") as f:
            for chunk in response.iter_content(4096):
                f.write(chunk)

    return []


def download_directory(session, filepath, url, directory, timeout):
    if os.path.isfile(os.path.join(directory, filepath)):
        printf("[-] Already downloaded %s/%s\n", url, filepath)
        return []

    with closing(
        session.get(
            f"{url}/{filepath}",
            allow_redirects=False,
            stream=True,
            timeout=timeout,
        )
    ) as response:
        printf(
            "[-] Fetching %s/%s [%d]\n",
            url,
            filepath,
            response.status_code,
        )

        if (
            response.status_code in (301, 302)
            and "Location" in response.headers
            and response.headers["Location"].endswith(filepath + "/")
        ):
            return [filepath + "/"]

        if filepath.endswith("/"):  # directory index
            assert is_html(response)

            return [filepath + filename for filename in get_indexed_files(response)]
        else:  # file
            valid, error_message = verify_response(response)
            if not valid:
                printf(error_message, file=sys.stderr)
                return []

            abspath = os.path.abspath(os.path.join(directory, filepath))
            create_intermediate_dirs(abspath)

            # write file
            with open(abspath, "wb") as f:
                for chunk in response.iter_content(4096):
                    f.write(chunk)

    return []


def find_refs(session, filepath, url, directory, timeout):
    response = session.get(f"{url}/{filepath}", allow_redirects=False, timeout=timeout)
    printf("[-] Fetching %s/%s [%d]\n", url, filepath, response.status_code)

    valid, error_message = verify_response(response)
    if not valid:
        printf(error_message, file=sys.stderr)
        return []

    abspath = os.path.abspath(os.path.join(directory, filepath))
    create_intermediate_dirs(abspath)

    # write file
    with open(abspath, "w") as f:
        f.write(response.text)

    # find refs
    tasks = []

    for ref in re.findall(r"(refs(/[a-zA-Z0-9\-\.\_\*]+)+)", response.text):
        ref = ref[0]
        if not ref.endswith("*") and is_safe_path(ref):
            tasks.append(f".git/{ref}")
            tasks.append(f".git/logs/{ref}")

    return tasks


def find_objects(session, obj, url, directory, timeout):
    filepath = f".git/objects/{obj[:2]}/{obj[2:]}"

    if os.path.isfile(os.path.join(directory, filepath)):
        printf("[-] Already downloaded %s/%s\n", url, filepath)
    else:
        response = session.get(
            f"{url}/{filepath}",
            allow_redirects=False,
            timeout=timeout,
        )
        printf(
            "[-] Fetching %s/%s [%d]\n",
            url,
            filepath,
            response.status_code,
        )

        valid, error_message = verify_response(response)
        if not valid:
            printf(error_message, file=sys.stderr)
            return []

        abspath = os.path.abspath(os.path.join(directory, filepath))
        create_intermediate_dirs(abspath)

        # write file
        with open(abspath, "wb") as f:
            f.write(response.content)

    abspath = os.path.abspath(os.path.join(directory, filepath))
    # parse object file to find other objects
    obj_file = dulwich.objects.ShaFile.from_path(abspath)
    return get_referenced_sha1(obj_file)


def process_tasks(initial_tasks, process_task_func, session, url, directory, timeout):
    tasks_seen = set()
    pending_tasks = initial_tasks

    while pending_tasks:
        task = pending_tasks.pop(0)
        if task not in tasks_seen:
            tasks_seen.add(task)
            new_tasks = process_task_func(session, task, url, directory, timeout)
            pending_tasks.extend(new_tasks)


def sanitize_file(filepath):
    """Inplace comment out possibly unsafe lines based on regex"""
    assert os.path.isfile(filepath), f"{filepath} is not a file"

    UNSAFE = r"^\s*fsmonitor|sshcommand|askpass|editor|pager"

    with open(filepath, "r+") as f:
        content = f.read()
        modified_content = re.sub(UNSAFE, "# \g<0>", content, flags=re.IGNORECASE)
        if content != modified_content:
            printf(f"Warning: '{filepath}' file was altered\n")
            f.seek(0)
            f.write(modified_content)


@celery_app.task(bind=True, name="utils.git_dump.fetch_git")
def fetch_git(self, url: str, directory, jobs, retry, timeout, http_headers, client_cert_p12=None, client_cert_p12_password=None):
    """Dump a git repository into the output directory"""
    try:
        save_path = Path(directory.replace(":", "_"))
        url = str(url)
        os.makedirs(save_path, exist_ok=True)

        session = requests.Session()
        session.verify = False
        session.headers = http_headers
        if client_cert_p12:
            session.mount(url, Pkcs12Adapter(pkcs12_filename=client_cert_p12, pkcs12_password=client_cert_p12_password))
        else:
            session.mount(url, requests.adapters.HTTPAdapter(max_retries=retry))

        if os.listdir(save_path):
            printf("Warning: Destination '%s' is not empty\n", directory)

        if url.endswith("HEAD"):
            url = url[:-4]
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        url = url.rstrip("/")

        printf("[-] Testing %s/.git/HEAD ", url)
        response = session.get(
            f"{url}/.git/HEAD",
            timeout=timeout,
            allow_redirects=False,
        )
        printf("[%d]\n", response.status_code)

        valid, error_message = verify_response(response)
        if not valid:
            printf(error_message, file=sys.stderr)
            return {"status": "error", "path": error_message, "url": str(url)}
        elif not re.match(r"^(ref:.*|[0-9a-f]{40}$)", response.text.strip()):
            printf(
                "error: %s/.git/HEAD is not a git HEAD file\n",
                url,
                file=sys.stderr,
            )
            return {"status": "error", "path": f"error: {url}/.git/HEAD is not a git HEAD file", "url": str(url)}

        # set up environment to ensure proxy usage
        environment = os.environ.copy()
        configured_proxy = socks.getdefaultproxy()
        if configured_proxy is not None:
            proxy_types = ["http", "socks4h", "socks5h"]
            environment["ALL_PROXY"] = (
                f"http.proxy={proxy_types[configured_proxy[0]]}://{configured_proxy[1]}:{configured_proxy[2]}"
            )

        # check for directory listing
        printf("[-] Testing %s/.git/ ", url)
        response = session.get(f"{url}/.git/", allow_redirects=False)
        printf("[%d]\n", response.status_code)

        if response.status_code == 200 and is_html(response) and "HEAD" in get_indexed_files(response):
            printf("[-] Fetching .git recursively\n")
            process_tasks(
                [".git/", ".gitignore"],
                download_directory,
                session,
                url,
                directory,
                timeout,
            )

            os.chdir(directory)

            printf("[-] Sanitizing .git/config\n")
            sanitize_file(".git/config")

            printf("[-] Running git checkout .\n")
            subprocess.check_call(["git", "checkout", "."], env=environment)
            return {"status": "success", "path": directory, "url": str(url)}

        # no directory listing
        printf("[-] Fetching common files\n")
        tasks = [
            ".gitignore",
            ".git/COMMIT_EDITMSG",
            ".git/description",
            ".git/hooks/applypatch-msg.sample",
            ".git/hooks/commit-msg.sample",
            ".git/hooks/post-commit.sample",
            ".git/hooks/post-receive.sample",
            ".git/hooks/post-update.sample",
            ".git/hooks/pre-applypatch.sample",
            ".git/hooks/pre-commit.sample",
            ".git/hooks/pre-push.sample",
            ".git/hooks/pre-rebase.sample",
            ".git/hooks/pre-receive.sample",
            ".git/hooks/prepare-commit-msg.sample",
            ".git/hooks/update.sample",
            ".git/index",
            ".git/info/exclude",
            ".git/objects/info/packs",
        ]
        process_tasks(
            tasks,
            download_file,
            session,
            url,
            directory,
            timeout,
        )

        # find refs
        printf("[-] Finding refs/\n")
        tasks = [
            ".git/FETCH_HEAD",
            ".git/HEAD",
            ".git/ORIG_HEAD",
            ".git/config",
            ".git/info/refs",
            ".git/logs/HEAD",
            ".git/logs/refs/heads/main",
            ".git/logs/refs/heads/master",
            ".git/logs/refs/heads/staging",
            ".git/logs/refs/heads/production",
            ".git/logs/refs/heads/development",
            ".git/logs/refs/remotes/origin/HEAD",
            ".git/logs/refs/remotes/origin/main",
            ".git/logs/refs/remotes/origin/master",
            ".git/logs/refs/remotes/origin/staging",
            ".git/logs/refs/remotes/origin/production",
            ".git/logs/refs/remotes/origin/development",
            ".git/logs/refs/stash",
            ".git/packed-refs",
            ".git/refs/heads/main",
            ".git/refs/heads/master",
            ".git/refs/heads/staging",
            ".git/refs/heads/production",
            ".git/refs/heads/development",
            ".git/refs/remotes/origin/HEAD",
            ".git/refs/remotes/origin/main",
            ".git/refs/remotes/origin/master",
            ".git/refs/remotes/origin/staging",
            ".git/refs/remotes/origin/production",
            ".git/refs/remotes/origin/development",
            ".git/refs/stash",
            ".git/refs/wip/wtree/refs/heads/main",
            ".git/refs/wip/wtree/refs/heads/master",
            ".git/refs/wip/wtree/refs/heads/staging",
            ".git/refs/wip/wtree/refs/heads/production",
            ".git/refs/wip/wtree/refs/heads/development",
            ".git/refs/wip/index/refs/heads/main",
            ".git/refs/wip/index/refs/heads/master",
            ".git/refs/wip/index/refs/heads/staging",
            ".git/refs/wip/index/refs/heads/production",
            ".git/refs/wip/index/refs/heads/development",
        ]
        process_tasks(
            tasks,
            find_refs,
            session,
            url,
            directory,
            timeout,
        )

        # find packs
        printf("[-] Finding packs\n")
        tasks = []

        # use .git/objects/info/packs to find packs
        info_packs_path = os.path.join(directory, ".git", "objects", "info", "packs")
        if os.path.exists(info_packs_path):
            with open(info_packs_path, "r") as f:
                info_packs = f.read()

            for sha1 in re.findall(r"pack-([a-f0-9]{40})\.pack", info_packs):
                tasks.append(f".git/objects/pack/pack-{sha1}.idx")
                tasks.append(f".git/objects/pack/pack-{sha1}.pack")

        process_tasks(
            tasks,
            download_file,
            session,
            url,
            directory,
            timeout,
        )

        # find objects
        printf("[-] Finding objects\n")
        objs = set()
        packed_objs = set()

        # .git/packed-refs, .git/info/refs, .git/refs/*, .git/logs/*
        files = [
            os.path.join(directory, ".git", "packed-refs"),
            os.path.join(directory, ".git", "info", "refs"),
            os.path.join(directory, ".git", "FETCH_HEAD"),
            os.path.join(directory, ".git", "ORIG_HEAD"),
        ]
        for dirpath, _, filenames in os.walk(os.path.join(directory, ".git", "refs")):
            for filename in filenames:
                files.append(os.path.join(dirpath, filename))
        for dirpath, _, filenames in os.walk(os.path.join(directory, ".git", "logs")):
            for filename in filenames:
                files.append(os.path.join(dirpath, filename))

        for filepath in files:
            if not os.path.exists(filepath):
                continue

            with open(filepath, "r") as f:
                content = f.read()

            for obj in re.findall(r"(^|\s)([a-f0-9]{40})($|\s)", content):
                obj = obj[1]
                objs.add(obj)

        # use .git/index to find objects
        index_path = os.path.join(directory, ".git", "index")
        if os.path.exists(index_path):
            index = dulwich.index.Index(index_path)

            for entry in index.iterobjects():
                objs.add(entry[1].decode())

        # use packs to find more objects to fetch, and objects that are packed
        pack_file_dir = os.path.join(directory, ".git", "objects", "pack")
        if os.path.isdir(pack_file_dir):
            for filename in os.listdir(pack_file_dir):
                if filename.startswith("pack-") and filename.endswith(".pack"):
                    pack_data_path = os.path.join(pack_file_dir, filename)
                    pack_idx_path = os.path.join(pack_file_dir, filename[:-5] + ".idx")
                    pack_data = dulwich.pack.PackData(pack_data_path)
                    pack_idx = dulwich.pack.load_pack_index(pack_idx_path)
                    pack = dulwich.pack.Pack.from_objects(pack_data, pack_idx)

                    for obj_file in pack.iterobjects():
                        packed_objs.add(obj_file.sha().hexdigest())
                        objs |= set(get_referenced_sha1(obj_file))

        # fetch all objects
        printf("[-] Fetching objects\n")
        process_tasks(
            list(objs),
            find_objects,
            session,
            url,
            directory,
            timeout,
        )

        # git checkout
        printf("[-] Running git checkout .\n")
        os.chdir(directory)
        sanitize_file(".git/config")

        # ignore errors
        subprocess.call(["git", "checkout", "."], stderr=open(os.devnull, "wb"), env=environment)

        return {"status": "success", "path": directory, "url": str(url)}
    except Exception as e:
        print(e)
        return {"status": "error", "path": str(e), "url": ""}
