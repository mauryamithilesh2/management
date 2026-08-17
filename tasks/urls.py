from django.urls import path

from . import views

urlpatterns = [
    path("", views.task_list, name="task_list"),
    path("create/", views.create_task, name="create_task"),
    path("<int:task_id>/", views.task_detail, name="task_detail"),
      path("<int:task_id>/", views.task_detail, name="task_detail"),
      path("<int:task_id>/", views.task_detail, name="task_detail"),
]
