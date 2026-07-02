from types import SimpleNamespace
from unittest.mock import patch

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.celery.tasks import (
    clean_object_store_caches,
    cleanup_jwds,
)
from galaxy.exceptions import ObjectNotFound
from galaxy.objectstore import BaseObjectStore
from galaxy.objectstore.caching import CacheTarget


class MockObjectStore:
    def __init__(self, cache_targets: list[CacheTarget]):
        self._cache_targets = cache_targets

    def cache_targets(self) -> list[CacheTarget]:
        return self._cache_targets


def test_clean_object_store_caches(tmp_path):
    container = MockApp()
    cache_targets: list[CacheTarget] = []
    container[BaseObjectStore] = MockObjectStore(cache_targets)  # type: ignore[assignment]

    # similar code used in object store unit tests
    cache_dir = tmp_path
    path = cache_dir / "a_file_0"
    path.write_text("this is an example file")

    # works fine on an empty list of cache targets...
    clean_object_store_caches()

    assert path.exists()

    # place the file in mock object store's cache targets and
    # run the task again and the above file should be gone.
    cache_targets.append(CacheTarget(cache_dir, 1, 0.000000001))
    # works fine on an empty list of cache targets...
    clean_object_store_caches()

    assert not path.exists()


def test_cleanup_jwds_logs_deleted_jobs_once():
    job = SimpleNamespace(id=198)
    query = SimpleNamespace(filter=lambda *args, **kwargs: [job])
    sa_session = SimpleNamespace(query=lambda *args, **kwargs: query)
    config = SimpleNamespace(failed_jobs_working_directory_cleanup_days=5)
    object_store = SimpleNamespace(get_filename=lambda *args, **kwargs: "/tmp/job_work_198")

    with (
        patch("galaxy.celery.tasks.shutil.rmtree") as rmtree,
        patch("galaxy.celery.tasks.log") as log,
    ):
        cleanup_jwds(sa_session, object_store, config)

    rmtree.assert_called_once_with("/tmp/job_work_198")
    log.info.assert_called_once_with("Deleted job working directory for job %s", 198)


def test_cleanup_jwds_does_not_log_deleted_when_already_missing():
    job = SimpleNamespace(id=198)
    query = SimpleNamespace(filter=lambda *args, **kwargs: [job])
    sa_session = SimpleNamespace(query=lambda *args, **kwargs: query)
    config = SimpleNamespace(failed_jobs_working_directory_cleanup_days=5)
    object_store = SimpleNamespace(
        get_filename=lambda *args, **kwargs: (_ for _ in ()).throw(ObjectNotFound())
    )

    with (
        patch("galaxy.celery.tasks.shutil.rmtree") as rmtree,
        patch("galaxy.celery.tasks.log") as log,
    ):
        cleanup_jwds(sa_session, object_store, config)

    rmtree.assert_not_called()
    log.info.assert_not_called()
