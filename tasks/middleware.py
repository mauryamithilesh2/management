import time

from django.core.cache import cache

from .views import release_due_scheduled_tasks

CHECK_INTERVAL_SECONDS = 300  # at most once every 5 minutes


class ScheduledTaskReleaseMiddleware:
    """
    Opportunistically releases any due ScheduledTask rows on incoming
    requests, throttled to at most once every CHECK_INTERVAL_SECONDS.

    This avoids needing Celery/Redis/a paid cron service - as long as the
    site gets occasional traffic (an admin or employee visiting any page),
    due tasks get released within CHECK_INTERVAL_SECONDS of becoming due.
    If the site gets zero traffic for a stretch, releases are simply
    delayed until the next visit - nothing is lost, just late.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        last_check = cache.get("scheduled_task_last_check", 0)
        now = time.time()

        if now - last_check >= CHECK_INTERVAL_SECONDS:
            cache.set("scheduled_task_last_check", now, timeout=None)
            try:
                release_due_scheduled_tasks()
            except Exception:
                pass  # never let a background check break the actual request

        return self.get_response(request)