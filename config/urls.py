from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('sinf/<int:sinf>/', views.class_detail, name='class_detail'),
    path('nazorat/<str:turi>/', views.control_grade_select, name='control_grade_select'),
    path('nazorat/<str:turi>/<int:sinf>/', views.control_test_start, name='control_test_start'),
    path('sinf/<int:sinf>/test/', views.topic_test_start, name='topic_test_start'),
]