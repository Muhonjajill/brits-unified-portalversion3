from django.urls import path
from . import views

urlpatterns = [
    path('leaves/',                        views.leave_list,          name='leave_list'),
    path('leaves/new/',                    views.leave_create,        name='leave_create'),
    path('leaves/export/excel/',           views.leave_export_excel,  name='leave_export_excel'),
    path('leaves/<int:pk>/',               views.leave_detail,        name='leave_detail'),
    path('leaves/<int:pk>/edit/',          views.leave_edit,          name='leave_edit'),
    path('leaves/<int:pk>/approve/',       views.leave_approve,       name='leave_approve'),
    path('leaves/<int:pk>/reject/',        views.leave_reject,        name='leave_reject'),
    path('leaves/<int:pk>/withdraw/',      views.leave_withdraw,      name='leave_withdraw'),
    path('leaves/<int:pk>/delete/',        views.leave_delete,        name='leave_delete'),
    path('leaves/<int:pk>/export/pdf/',    views.leave_export_pdf,    name='leave_export_pdf'),
]
