from django.db import router
from django.urls import path, include
from rest_framework_nested import routers as nested_routers
from rest_framework.routers import DefaultRouter
from rest_framework import routers
from .views import (
    # Auth
    SignupView, LoginView,
    # Profile (ViewSet)
    ProfileViewSet,
    # Student/Public Lists & ViewSets
    SubjectListView, TestViewSet, MaterialViewSet, LeaderboardView,
    MockTestViewSet, UniversityViewSet, CourseViewSet, ScheduleItemViewSet,
    NotificationViewSet,
    # Admin Dashboard
    AdminDashboardStatsView, AdminDashboardLatestListsView,
    # Admin Statistics (Separate Views)
    AdminUserStatisticsView, AdminTestStatisticsView, AdminPaymentStatisticsView,
    # Admin CRUD ViewSets
    AdminUserViewSet, AdminTestViewSet, AdminQuestionViewSet, AdminMaterialViewSet,
    AdminPaymentViewSet, AdminUniversityViewSet, AdminAchievementViewSet,
    AdminCourseViewSet, AdminLessonViewSet
)

# --- Student/Public Router ---
# (Bu qism o'zgarishsiz qoladi)
router = DefaultRouter()
router.register(r'tests', TestViewSet, basename='test')
router.register(r'materials', MaterialViewSet, basename='material')
router.register(r'mock-tests', MockTestViewSet, basename='mock-test')
router.register(r'universities', UniversityViewSet, basename='university')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'schedule', ScheduleItemViewSet, basename='schedule-item') # Student o'z jadvalini boshqaradi
router.register(r'notifications', NotificationViewSet, basename='notification') # Student o'z bildirishnomalarini ko'radi

# Profile uchun alohida router
# (Bu qism o'zgarishsiz qoladi)
profile_router = DefaultRouter()
profile_router.register(r'profile', ProfileViewSet, basename='profile')


# --- Admin Router ---
# (Bu qism o'zgarishsiz qoladi, FAQAT statistics olib tashlanadi)
admin_router = routers.DefaultRouter()
admin_router.register(r'users', AdminUserViewSet, basename='admin-user')
admin_router.register(r'tests', AdminTestViewSet, basename='admin-test')
# Savollar nested router orqali qo'shiladi, asosiy routerda kerak emas
# admin_router.register(r'questions', AdminQuestionViewSet, basename='admin-question')
admin_router.register(r'materials', AdminMaterialViewSet, basename='admin-material')
admin_router.register(r'payments', AdminPaymentViewSet, basename='admin-payment') # ReadOnly
admin_router.register(r'universities', AdminUniversityViewSet, basename='admin-university')
admin_router.register(r'achievements', AdminAchievementViewSet, basename='admin-achievement')
admin_router.register(r'courses', AdminCourseViewSet, basename='admin-course')
# Darslar nested router orqali qo'shiladi
# admin_router.register(r'lessons', AdminLessonViewSet, basename='admin-lesson')
# Subject uchun alohida ViewSet kerak bo'lsa:
# admin_router.register(r'subjects', AdminSubjectViewSet, basename='admin-subject')


# --- Nested Routers for Admin ---
# (Bu qism o'zgarishsiz qoladi)
tests_admin_router = nested_routers.NestedSimpleRouter(admin_router, r'tests', lookup='test')
tests_admin_router.register(r'questions', AdminQuestionViewSet, basename='admin-test-question') # basename o'zgardi

courses_admin_router = nested_routers.NestedSimpleRouter(admin_router, r'courses', lookup='course')
courses_admin_router.register(r'lessons', AdminLessonViewSet, basename='admin-course-lesson') # basename o'zgardi


urlpatterns = [
    # Authentication
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/login/', LoginView.as_view(), name='login'),

    # Student/Public Lists (non-ViewSet)
    path('subjects/', SubjectListView.as_view(), name='subject-list'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),

    # Student Profile Actions & Retrieve/Update (using its own router)
    path('', include(profile_router.urls)), # /api/profile/, /api/profile/change-password/, etc.

    # Other Student/Public ViewSets (using the main router)
    path('', include(router.urls)), # /api/tests/, /api/materials/, etc.

    # --- Admin Endpoints ---
    # Dashboard
    path('admin/dashboard/stats/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('admin/dashboard/latest/', AdminDashboardLatestListsView.as_view(), name='admin-dashboard-latest'),

    # Statistics (using separate GenericAPIViews)
    path('admin/statistics/users/', AdminUserStatisticsView.as_view(), name='admin-stats-users'),
    path('admin/statistics/tests/', AdminTestStatisticsView.as_view(), name='admin-stats-tests'),
    path('admin/statistics/payments/', AdminPaymentStatisticsView.as_view(), name='admin-stats-payments'),
    # path('admin/statistics/courses/', AdminCourseStatisticsView.as_view(), name='admin-stats-courses'), # Agar kerak bo'lsa

    # Admin CRUD ViewSets (using admin_router and nested routers)
    path('admin/', include(admin_router.urls)), # /api/admin/users/, /api/admin/tests/, etc.
    path('admin/', include(tests_admin_router.urls)), # /api/admin/tests/{test_pk}/questions/
    path('admin/', include(courses_admin_router.urls)), # /api/admin/courses/{course_pk}/lessons/
]