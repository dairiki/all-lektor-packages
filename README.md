# Download source code for all known Lektor plugins

This is a quickie throwaway script designed to download the source
code for as many Lektor-related distributions — plugins and the like —
as can be found.

My motivation for hacking this together is to have generate a set
of source code that I can grep for references to various bits of
Lektor's API (documented and undocumented) in order to survey
what bits are used by externally.

Currently distributions of interest are located by searching
PyPI for distributions tagged with the `Framework :: Lektor`
Trove classifier.

## Usage

This script downloads distribution's source code to three
different subdirectories of the current working directory.

For those distributions for which a git repo can be found,
the repo is cloned into the `gitsrc` subdirectory.

If there is no git repo, but an _sdist_ is available on PyPI,
then the sdist is unpacked into the `sdists` subdirectory.

Finally, if neither a git repo nor an sdist can be found,
the distribution is installed in to the `wheels` subdirectory
(so named, because, presumably the installation will be from
a wheel.)

If any version of the distribution has already been downloaded,
it will not be downloaded again (even if a newer version exists.)
(Except, because it's hard not to, distributions that get installed
in the `wheels` subdirectory are reinstalled on every run.)

Here's how to run the script:

```sh
poetry run python -m all_lektor_packages.py
```

