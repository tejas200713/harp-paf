"""Approved workload whitelist built from examples/manifest.json.

Only source files whose SHA-256 matches a file listed in the manifest may
be compiled and executed. Hashes are computed from the files on disk, so
editing an example only requires updating its expected output.
"""

from functools import lru_cache
import hashlib
import json

from backend import config

MANIFEST = config.EXAMPLES_DIR / "manifest.json"


@lru_cache(maxsize=1)
def _load():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    approved = {}

    for item in manifest["workloads"]:
        path = config.EXAMPLES_DIR / item["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        language = "cpp" if path.suffix == ".cpp" else "c"
        approved.setdefault(language, {})[digest] = {
            **item,
            "sha256": digest,
            "language": language,
        }

    return approved


def approved_hashes(language):
    return set(_load().get(language, {}))


def get_workload(language, source_hash):
    return _load().get(language, {}).get(source_hash)


def get_expected_output(language, source_hash):
    workload = get_workload(language, source_hash)
    return workload["expectedOutput"] if workload else None


def list_workloads():
    return [
        dict(item)
        for language in _load().values()
        for item in language.values()
    ]
