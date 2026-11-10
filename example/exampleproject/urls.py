from demo import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", views.index, name="index"),
    path("doc/<slug:slug>/<int:pk>.<str:fmt>", views.document, name="document"),
    path("editors/", views.editor_gallery, name="editor_gallery"),
    path("my-letter/", views.user_letter, name="user_letter"),
    path("admin/", admin.site.urls),
    path("templates-pro/", include("templates_pro.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
