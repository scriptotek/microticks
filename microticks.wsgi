import os

# Optional: to log errors to Sentry, set the DSN here:
os.environ['MICROTICKS_SENTRY_DSN'] = None

from microticks import app as application
