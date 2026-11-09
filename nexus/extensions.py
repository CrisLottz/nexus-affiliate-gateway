"""Flask extensions shared across blueprints."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect

csrf = CSRFProtect()

# In-memory storage: limits are per instance. Good enough to slow down brute force on a small
# deployment; with several Cloud Run instances, point RATELIMIT_STORAGE_URI at Redis instead.
limiter = Limiter(key_func=get_remote_address, default_limits=[], storage_uri="memory://")
