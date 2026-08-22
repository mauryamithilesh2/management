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
    path("employees/", views.employee_overview, name="employee_overview"),
    path("employees/<int:employee_id>/", views.employee_task_detail, name="employee_task_detail"),
    path("<int:task_id>/notify/",views.notify_task_employee, name="notify_task_employee",),
    path("scheduled/", views.scheduled_task_list, name="scheduled_task_list"),
    path("scheduled/<int:scheduled_id>/toggle-hold/", views.toggle_task_hold, name="toggle_task_hold"),
    path("scheduled/create/", views.create_scheduled_task, name="create_scheduled_task"),
    path("scheduled/<int:scheduled_id>/edit/", views.edit_scheduled_task, name="edit_scheduled_task"),
]
