import os
import re
import shutil
import subprocess
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from urllib.parse import (
    urlparse,
    urlunparse,
)
from xmlrpc.client import ServerProxy

from pkg_resources import find_distributions
import requests
from packaging.version import Version


def search_by_name():
    """Use legacy PyPI API to get all distributions with "lektor" in their name.

    https://warehouse.pypa.io/api-reference/legacy.html
    """
    r = requests.get("https://pypi.org/simple/")
    r.raise_for_status()
    for m in re.finditer(r'<a [^>]*>([^<]*lektor.+?)</a>', r.text, re.I):
        yield m.group(1)


def search_by_classifier():
    """Use PyPI XML-RPC API to get all Lektor-tagged distributions.

    https://warehouse.pypa.io/api-reference/xml-rpc.html
    """
    client = ServerProxy("https://pypi.org/pypi")
    return set(name for name, version in client.browse(["Framework :: Lektor"]))


def iter_json_info(distnames):
    """Use PyPI JSON API to get release info.

    https://warehouse.pypa.io/api-reference/json.html#release
    """
    for name in set(distnames):
        r = requests.get(f"https://pypi.org/pypi/{name}/json")
        r.raise_for_status()
        yield r.json()


def get_source(json):
    rv = {}
    info = json.get("info", {})
    home_page = info.get("home_page")
    if home_page:
        rv["home_page"] = home_page

    urls = json.get("urls", [])
    for url in urls:
        if url.get("filename").endswith(".tar.gz"):
            rv.setdefault("sdist", url["url"])
        elif url.get("filename").endswith("-none-any.whl"):
            rv.setdefault("wheel", url["url"])
    return rv


GITSRC_DIR = Path(__file__).parent / "gitsrc"
SDIST_DIR = Path(__file__).parent / "sdists"
WHEELS_DIR = Path(__file__).parent / "wheels"


def find_already_have():
    for dir in (GITSRC_DIR, SDIST_DIR):
        if dir.exists():
            for subdir in dir.iterdir():
                if subdir.is_dir():
                    yield subdir.name
    for dist in find_distributions(WHEELS_DIR.__fspath__(), only=True):
        yield dist.key


def git_clone(name, url):
    print(f"git-cloning {name}")
    GITSRC_DIR.mkdir(exist_ok=True)
    try:
        subprocess.run(
            ('git', 'clone', '--depth=1', url, name),
            cwd=GITSRC_DIR,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            check=True,
        )
    except Exception:
        shutil.rmtree(GITSRC_DIR.joinpath(name))
        raise


def get_sdist(name, url):
    dest = SDIST_DIR / name
    print(f"getting sdist {name}")
    dest.mkdir(exist_ok=True, parents=True)
    r = requests.get(url)
    r.raise_for_status()
    subprocess.run(
        ('tar', '-xz', '--strip-components=1', '-f', '-'),
        cwd=dest,
        input=r.content,
        check=True,
    )


def get_wheel(name):
    print(f"installing (wheel) {name}")
    WHEELS_DIR.mkdir(exist_ok=True)
    subprocess.run(
        ('pip', 'install', '--target', WHEELS_DIR, name),
        check=True,
    )


def main():
    distnames = set(search_by_name())
    distnames.update(search_by_classifier())

    distnames = set(name.lower() for name in distnames)
    already_have = set(name.lower() for name in find_already_have())

    for json in iter_json_info(distnames - already_have):
        name = json["info"]["name"]
        src = get_source(json)
        home_page = src.get("home_page")
        sdist = src.get("sdist")
        wheel = src.get("wheel")

        if home_page:
            url = urlparse(home_page)
            if url.scheme == "http":
                if url.netloc in ("github.com", "gitlab.com"):
                    url = url._replace(scheme="https")
            try:
                git_clone(name.lower(), urlunparse(url))
                continue
            except Exception as exc:
                print(f"git clone failed: {exc}")
        if sdist:
            get_sdist(name.lower(), sdist)
        else:
            get_wheel(name)


if __name__ == "__main__":
    main()
