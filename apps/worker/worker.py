"""RQ worker entrypoint. Reuses the API package on PYTHONPATH."""

from redis import Redis
from rq import Worker

from opengero.config import get_settings
from opengero.docking import publish_engine


def main() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    publish_engine()
    Worker(["opengero"], connection=redis).work(with_scheduler=True)


if __name__ == "__main__":
    main()
