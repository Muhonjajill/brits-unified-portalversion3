from django.urls import path
from . import views

urlpatterns = [
    path('claims/', views.claim_list, name='claim_list'),
    path('claims/new/', views.claim_create, name='claim_create'),
    path('claims/<int:pk>/', views.claim_detail, name='claim_detail'),
    path('claims/<int:pk>/edit/', views.claim_edit, name='claim_edit'),
    path('claims/<int:pk>/approve/', views.claim_approve, name='claim_approve'),
    path('claims/<int:pk>/reject/', views.claim_reject, name='claim_reject'),
    path('claims/<int:pk>/export/pdf/', views.claim_export_pdf, name='claim_export_pdf'),
    path('claims/<int:pk>/export/excel/', views.claim_export_excel, name='claim_export_excel'),
]