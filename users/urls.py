from django.urls import path
from .views import *

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/create/', UserCreateView.as_view(), name='user-create'),
    path('users/<int:pk>/update/', UserUpdateView.as_view(), name='user-update'),
    path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='user-delete'),


    path('tests/create/', TestCreateView.as_view(), name='test-create'),
    path('tests/<int:pk>/update/', TestUpdateView.as_view(), name='test-update'),


    path('admin/tests/<int:test_id>/questions/', SavolListView.as_view(), name='admin-savol-list'),
    path('admin/tests/<int:test_id>/questions/create/', SavolCreateView.as_view(), name='admin-savol-create'),
    path('admin/questions/<int:pk>/update/', SavolUpdateView.as_view(), name='admin-savol-update'),
    path('admin/questions/<int:pk>/delete/', SavolDeleteView.as_view(), name='admin-savol-delete'),

    path('admin/materials/', OquvMaterialListView.as_view(), name='admin-material-list'),
    path('admin/materials/<int:pk>/', OquvMaterialDetailView.as_view(), name='admin-material-detail'),
    path('admin/materials/create/', OquvMaterialCreateView.as_view(), name='admin-material-create'),
    path('admin/materials/<int:pk>/update/', OquvMaterialUpdateView.as_view(), name='admin-material-update'),
    path('admin/materials/<int:pk>/delete/', OquvMaterialDeleteView.as_view(), name='admin-material-delete'),

    path('admin/payments/', TolovListView.as_view(), name='admin-tolov-list'),
    path('admin/payments/create/', TolovCreateView.as_view(), name='admin-tolov-create'),

    path('admin/ratings/', ReytingListView.as_view(), name='admin-reyting-list'),  # Admin uchun barcha reytinglar
    path('reyting/<int:pk>/', ReytingDetailView.as_view(), name='reyting-detail'),  # Foydalanuvchi uchun o'z reytingi
    path('admin/ratings/<int:pk>/update/', ReytingUpdateView.as_view(), name='admin-reyting-update'),# Admin taxrirlashi uchun


    path('admin/ielts/umumiy/', IELTSUmumiyListView.as_view(), name='admin-ielts-umumiy-list'),
    path('admin/ielts/umumiy/<int:pk>/', IELTSUmumiyDetailView.as_view(), name='admin-ielts-umumiy-detail'),
    path('admin/ielts/umumiy/<int:pk>/update/', IELTSUmumiyUpdateView.as_view(), name='admin-ielts-umumiy-update'),

    path('admin/ielts/test/create/', IELTSTestCreateView.as_view(), name='admin-ielts-test-create'),
    path('admin/ielts/test/<int:pk>/delete/', IELTSTestDeleteView.as_view(), name='admin-ielts-test-delete'),

    path('admin/ielts/material/create/', IELTSMaterialCreateView.as_view(), name='admin-ielts-material-create'),
    path('admin/ielts/material/<int:pk>/delete/', IELTSMaterialDeleteView.as_view(),name='admin-ielts-material-delete'),

    path('universities/', UniversitetListView.as_view(), name='universitet-list'),  # Hammaga ochiq
    path('universities/<int:pk>/', UniversitetDetailView.as_view(), name='universitet-detail'),  # Hammaga ochiq
    path('admin/universities/create/', UniversitetCreateView.as_view(), name='admin-universitet-create'),
    path('admin/universities/<int:pk>/update/', UniversitetUpdateView.as_view(), name='admin-universitet-update'),
    path('admin/universities/<int:pk>/delete/', UniversitetDeleteView.as_view(), name='admin-universitet-delete'),

    path('admin/achievements/', YutuqListView.as_view(), name='admin-achievement-list'),
    path('admin/achievements/<int:pk>/', YutuqDetailView.as_view(), name='admin-achievement-detail'),
    path('admin/achievements/create/', YutuqCreateView.as_view(), name='admin-achievement-create'),
    path('admin/achievements/<int:pk>/update/', YutuqUpdateView.as_view(), name='admin-achievement-update'),
    path('admin/achievements/<int:pk>/delete/', YutuqDeleteView.as_view(), name='admin-achievement-delete'),
    path('achievements/', FoydalanuvchiYutugiListView.as_view(), name='user-achievement-list'),
]