from .models import Notification


def unread_notifications(request):
    """
    Makes unread notifications available in every template (via
    base.html) without every view needing to pass them in manually.
    Only queries the database for authenticated users.
    """
    if not request.user.is_authenticated:
        return {}

    unread = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).select_related("task")

    return {
        "unread_notification_count": unread.count(),
        "unread_notifications": unread[:5],
    }