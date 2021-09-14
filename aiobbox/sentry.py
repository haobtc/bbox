from typing import Optional
import os
import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

def setup_sentry() -> None:
    dsn = os.environ.get('BBOX_SENTRY_DSN', '')
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[AioHttpIntegration()],
            traces_sample_rate=1.0
        )

