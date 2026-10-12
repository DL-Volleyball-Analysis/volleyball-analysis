"""Checks run when the API or the worker starts."""

import logging

from vball import manifest

log = logging.getLogger(__name__)


def check_models() -> dict[str, str]:
    """Log every weight file that is missing or differs from models/manifest.json; the stages that need such a file
    report themselves unavailable. Returns the problems found."""
    problems = manifest.check()
    for name, problem in sorted(problems.items()):
        if problem == "changed":
            log.error("model %s differs from its checksum in models/manifest.json; it will not be used", name)
        else:
            log.warning("model %s is missing (scripts/fetch_models.py lists how to get it)", name)
    return problems
