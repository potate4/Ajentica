"""Shallow-clone (or fast-forward update) the target GitHub repo."""

from __future__ import annotations

import logging
from pathlib import Path

from git import GitCommandError, Repo

log = logging.getLogger(__name__)


def clone_or_update(url: str, ref: str, dest: Path) -> Path:
    """Ensure `dest` contains a checkout of `url` at `ref`.

    Uses a shallow clone (depth=1) to keep the local copy small. If the
    directory already contains a clone of the same URL, fetches and resets
    to the latest tip of `ref` instead of re-cloning.
    """
    dest = Path(dest)
    if (dest / ".git").exists():
        log.info("Repo exists at %s; fetching latest %s", dest, ref)
        repo = Repo(dest)
        try:
            repo.remotes.origin.fetch(ref, depth=1)
            repo.git.reset("--hard", f"origin/{ref}")
        except GitCommandError as e:
            log.warning("Fetch/reset failed (%s); leaving existing checkout in place", e)
        return dest

    log.info("Cloning %s @ %s into %s", url, ref, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    Repo.clone_from(url, dest, depth=1, branch=ref)
    return dest
