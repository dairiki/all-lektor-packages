import subprocess
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from urllib.parse import (
    urlparse,
    urlunparse,
)
from xmlrpc.client import ServerProxy

import requests
from packaging.version import Version


BAD_DISTS = {
    "lektor",
    "lektor-gitlab",
}


def latest_versions():
    """Use PyPI XML-RPC API to get all Lektor-tagged distributions.

    https://warehouse.pypa.io/api-reference/xml-rpc.html
    """
    client = ServerProxy("https://pypi.org/pypi")
    dist_versions = client.browse(["Framework :: Lektor"])
    for name, dist_versions in groupby(sorted(dist_versions), itemgetter(0)):
        if name.lower() in BAD_DISTS:
            continue
        max_version = max(map(Version, (dv[1] for dv in dist_versions)))
        yield name, max_version


def get_dist_json(name, version):
    """Use PyPI JSON API to get release info.

    https://warehouse.pypa.io/api-reference/json.html#release
    """
    r = requests.get(f"https://pypi.org/pypi/{name}/{version}/json")
    r.raise_for_status()
    return r.json()


def get_source(name, version):
    json = get_dist_json(name, version)
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


def git_clone(name, url):
    if not GITSRC_DIR.joinpath(name).is_dir():
        GITSRC_DIR.mkdir(exist_ok=True)
        subprocess.run(
            ('git', 'clone', '--depth=1', url, name),
            cwd=GITSRC_DIR,
            check=True,
        )


def get_sdist(name, url):
    dest = SDIST_DIR / name
    if not dest.is_dir():
        dest.mkdir(exist_ok=True, parents=True)
        r = requests.get(url)
        r.raise_for_status()
        subprocess.run(
            ('tar', '-xz', '--strip-components=1', '-f', '-'),
            input=r.content,
            check=True,
        )


def get_wheel(name, version):
    if not WHEELS_DIR.joinpath(name).is_dir():
        WHEELS_DIR.mkdir(exist_ok=True)
        subprocess.run(
            ('pip', 'install', '--target', WHEELS_DIR, f'{name}=={version}'),
            check=True,
        )


def main():
    for name, version in latest_versions():
        src = get_source(name, version)
        home_page = src.get("home_page")
        sdist = src.get("sdist")
        wheel = src.get("wheel")

        if home_page:
            url = urlparse(home_page)
            if url.scheme == "http":
                if url.netloc in ("github.com", "gitlab.com"):
                    url = url._replace(scheme="https")
            git_clone(name.lower(), urlunparse(url))
        elif sdist:
            get_sdist(name.lower(), sdist)
        elif wheel:
            get_wheel(name, version)
        else:
            print(f"CAN NOT FIND: {name}, {version}")


if __name__ == "__main__":
    main()
