from django.urls import path

from . import views

urlpatterns = [
    path("", views.task_list, name="task_list"),
    path("create/", views.create_task, name="create_task"),
    path("<int:task_id>/", views.task_detail, name="task_detail"),
    path("<int:task_id>/edit/", views.task_edit, name="task_edit"),
    path("<int:task_id>/delete/", views.task_delete, name="task_delete"),
    path("<int:task_id>/updates/add/", views.add_task_update, name="add_task_update"),
    path("notifications/", views.notification_list, name="notification_list"),
]
