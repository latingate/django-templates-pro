from django.urls import path

from . import views

app_name = "templates_pro"

urlpatterns = [
    path("preview/", views.live_preview, name="preview"),
    path("preview/<int:pk>/<str:fmt>/", views.saved_preview, name="saved_preview"),
]
