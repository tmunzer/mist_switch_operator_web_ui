from django.urls import path

from . import views

urlpatterns = [
    path('devices/', views.get_devices, name='get_devices'),
    path('devices/settings/', views.get_device_settings, name='get_device_settings'),
    path('devices/update/', views.update_device_settings, name='update_device_settings'),
    path('login/', views.login, name='login'),
    path('sites/', views.get_sites, name='get_sites'),    
    #path('sites/derived/', views.get_site_derived, name='get_site_derived'),
    path('script', views.script, name="googlemaps"),
    path('gap', views.gap, name="gap")
]
