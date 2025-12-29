import logging
import os

try:
    from . import _version

    __version__ = _version.__version__
except:  # noqa: E722
    __version__ = "0.0.0-dev"

# Configure logging on package import
log_level = os.environ.get("APP_LOG_LEVEL", os.environ.get("LOG_LEVEL", "WARNING")).upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.WARNING),
    format="%(levelname)s:%(name)s:%(message)s",
    force=True,
)
