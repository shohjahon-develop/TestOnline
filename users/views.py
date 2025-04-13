

import decimal
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Count, Avg, Sum, F, ExpressionWrapper, DurationField, Q, Max
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _ # <<<--- _ uchun import
from rest_framework import generics, permissions, status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
# V----- IsAuthenticatedOrReadOnly ni import qilish
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models.functions import TruncDate # Grafik uchun
from .utils import get_date_ranges # Yordamchi funksiyani import qilamiz

from .models import (
    User, Subject, Test, Question, UserTestResult, UserAnswer, Material, Payment,
    UserRating, MockTest, MockTestResult, MockTestMaterial, University,
    Achievement, UserAchievement, Course, Lesson, UserCourseEnrollment,
    CourseReview, ScheduleItem, Notification, UserSettings
)
from .serializers import * # Barcha serializerlarni import qilamiz
from .permissions import IsOwnerOrAdmin, IsAdminOrReadOnly


def _calculate_percentage_change(current_value, previous_value):
    """Foiz o'zgarishini hisoblash uchun yordamchi funksiya."""
    if previous_value is None:
        return None # Oldingi davr bo'lmasa, foiz hisoblanmaydi
    try:
        # Hisoblashdan oldin Decimal ga o'tkazamiz
        current = decimal.Decimal(current_value) if current_value is not None else decimal.Decimal(0)
        previous = decimal.Decimal(previous_value) if previous_value is not None else decimal.Decimal(0)

        if previous == 0:
            return 100.0 if current > 0 else 0.0 # Agar oldingisi 0 bo'lsa
        change = ((current - previous) / previous) * 100
        return round(float(change), 1) # Bir o'nlik xonagacha
    except (TypeError, decimal.InvalidOperation, decimal.DivisionByZero, ValueError):
         return 0.0 # Xatolik bo'lsa 0

# --- Authentication Views ---

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignupSerializer
    permission_classes = (AllowAny,)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # `validated_data` dan tokenlarni olish
        token = serializer.validated_data['token']
        refresh_token = serializer.validated_data['refresh_token']

        # `user` maydonini olish uchun serializer.data dan foydalanamiz
        # `serializer.data` ni chaqirish `get_user` metodini ishga tushiradi
        user_data = serializer.data['user']

        response_data = {
            'token': token,
            'refresh_token': refresh_token,
            'user': user_data
        }
        return Response(response_data, status=status.HTTP_200_OK)

# --- User Profile & Settings Views ---

class ProfileViewSet(mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    """
    Foydalanuvchi profilini ko'rish, tahrirlash va bog'liq amallar uchun ViewSet.
    URL Conf: profile_router = DefaultRouter(); profile_router.register(r'profile', ProfileViewSet)
    Endpoints: /api/profile/, /api/profile/change-password/, /api/profile/settings/, etc.
    """
    # permission_classes = [IsAuthenticated]
    queryset = User.objects.all()

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        action_serializer_map = {
            'retrieve': UserSerializer,
            'update': ProfileUpdateSerializer,
            'partial_update': ProfileUpdateSerializer,
            'change_password': ChangePasswordSerializer,
            'manage_settings': ProfileSettingsUpdateSerializer,  # <<< O'ZGARTIRILDI (PUT/PATCH uchun)
            'my_test_history': UserTestResultSerializer,
            'my_payment_history': PaymentSerializer,
            'my_achievements': UserAchievementSerializer,
            'my_rating': UserRatingSerializer,
            'my_schedule': ScheduleItemSerializer,
            'add_funds': AddFundsSerializer,
        }
        # `manage_settings` GET uchun alohida serializer
        if self.action == 'manage_settings' and self.request.method == 'GET':  # <<< O'ZGARTIRILDI
            return UserSettingsSerializer
        return action_serializer_map.get(self.action, UserSerializer)

    # Retrieve (GET /api/profile/) - mixin orqali
    # Update (PUT /api/profile/) - mixin orqali
    # Partial Update (PATCH /api/profile/) - mixin orqali

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": _("Parol muvaffaqiyatli o'zgartirildi.")})

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='settings')  # URL path o'zgarishsiz qolishi mumkin
    def manage_settings(self, request, *args, **kwargs):  # <<< NOM O'ZGARTIRILDI
        user_settings = get_object_or_404(UserSettings, user=self.get_object())
        if request.method == 'GET':
            # GET uchun UserSettingsSerializer ishlatiladi
            serializer = UserSettingsSerializer(user_settings)
            return Response(serializer.data)
        else:
            # PUT/PATCH uchun ProfileSettingsUpdateSerializer ishlatiladi
            serializer = ProfileSettingsUpdateSerializer(user_settings, data=request.data,
                                                         partial=request.method == 'PATCH')
            serializer.is_valid(raise_exception=True)
            serializer.save()
            # Yangilangan ma'lumotni ham UserSettingsSerializer bilan qaytaramiz
            return Response(UserSettingsSerializer(user_settings).data)

    @action(detail=False, methods=['get'], url_path='test-history')
    def my_test_history(self, request):
        queryset = UserTestResult.objects.filter(user=request.user).select_related('test', 'test__subject').order_by('-start_time')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='payment-history')
    def my_payment_history(self, request):
        queryset = Payment.objects.filter(user=request.user).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='achievements')
    def my_achievements(self, request):
        queryset = UserAchievement.objects.filter(user=request.user).select_related('achievement').order_by('-earned_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='rating')
    def my_rating(self, request):
        rating, created = UserRating.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(rating)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='schedule')
    def my_schedule(self, request):

        # lekin qulaylik uchun qoldirish mumkin.
        queryset = ScheduleItem.objects.filter(user=request.user).order_by('day_of_week', 'start_time')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='add-funds')
    def add_funds(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']
        payment_method = serializer.validated_data['payment_method']
        user = request.user
        # ... (To'lov tizimi integratsiyasi) ...
        payment = Payment.objects.create(
            user=user, amount=amount, payment_type='deposit', status='pending',
            payment_method=payment_method,
            description=f"Hisobni {amount:,.0f} so'mga to'ldirish".replace(',', ' ')
        )
        redirect_url = f"/payment-gateway/pay?id={payment.id}" # Misol
        return Response({
            "message": _("To'lovni amalga oshirish uchun yo'naltirilmoqda..."),
            "payment_id": payment.id, "redirect_url": redirect_url,
        }, status=status.HTTP_201_CREATED)


# --- Student/Public Views (Non-Profile) ---

class SubjectListView(generics.ListAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [AllowAny]

class TestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly] # <- Import qilingan
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['subject', 'difficulty', 'test_type']
    search_fields = ['title', 'subject__name', 'description']
    queryset = Test.objects.filter(status='active').select_related('subject').prefetch_related('questions') # Savollarni ham oldindan olish

    def get_serializer_class(self):
        action_serializer_map = {
            'list': TestListSerializer,
            'retrieve': TestDetailSerializer,
            'submit_test': SubmitAnswerSerializer,
            'results': UserTestResultSerializer,
        }
        return action_serializer_map.get(self.action, TestListSerializer)

    @action(detail=True, methods=['post'], url_path='submit', permission_classes=[IsAuthenticated])
    def submit_test(self, request, pk=None):
        test = self.get_object()
        user = request.user
        # Bir foydalanuvchi bir testni qayta-qayta topshirmasligi uchun tekshiruv (agar kerak bo'lsa)
        # if UserTestResult.objects.filter(user=user, test=test, status='completed').exists():
        #     return Response({"detail": _("Siz bu testni allaqachon topshirgansiz.")}, status=status.HTTP_400_BAD_REQUEST)

        # To'lov tekshiruvi...
        if test.test_type == 'premium' and test.price > 0:
             if not Payment.objects.filter(user=user, test=test, status='successful').exists():
                 if user.balance < test.price:
                     raise ValidationError(_("Testni topshirish uchun hisobingizda yetarli mablag' yo'q."))
                 Payment.objects.create(
                     user=user, amount=-test.price, payment_type='test_purchase',
                     description=f"'{test.title}' testi uchun to'lov", status='successful',
                     payment_method='internal', test=test
                 )
                 user.refresh_from_db() # Yangilangan balansni olish uchun

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_answers = serializer.validated_data.get('answers', {})

        # Natijani yaratish va hisoblash
        result = UserTestResult.objects.create(
            user=user, test=test, status='in_progress',
            total_questions=test.questions.count() # Savollar sonini boshida saqlash
        )
        result.calculate_result(user_answers) # Javoblarni saqlab, hisoblaydi

        result_serializer = UserTestResultSerializer(result, context=self.get_serializer_context())
        return Response(result_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def results(self, request, pk=None):
        test = self.get_object()
        user = request.user
        try:
            # Oxirgi tugallangan natijani olish
            latest_result = UserTestResult.objects.filter(user=user, test=test, status='completed').latest('end_time')
            serializer = self.get_serializer(latest_result, context={'request': request})
            return Response(serializer.data)
        except UserTestResult.DoesNotExist:
            raise NotFound(_("Siz bu testni hali topshirmagansiz."))

class MaterialViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly] # <- Import qilingan
    serializer_class = MaterialSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['subject', 'material_type', 'file_format', 'is_free']
    search_fields = ['title', 'subject__name', 'description']
    queryset = Material.objects.filter(status='active').select_related('subject')

    @action(detail=True, methods=['get'], url_path='download', permission_classes=[IsAuthenticated])
    def download_material(self, request, pk=None):
        material = self.get_object()
        user = request.user
        # ... (To'lov tekshiruvi va download count logikasi avvalgidek) ...
        if not material.is_free:
            if not Payment.objects.filter(user=user, material=material, status='successful').exists():
                 # Agar material uchun alohida sotib olish logikasi bo'lsa:
                 # if user.balance < material.price:
                 #    raise ValidationError(...)
                 # Payment.objects.create(...)
                 # user.refresh_from_db()
                 raise PermissionDenied(_("Bu materialni yuklab olish uchun avval sotib olishingiz kerak."))

        material.increment_download_count()
        serializer = self.get_serializer(material, context={'request': request}) # Contextni uzatish muhim (URL uchun)
        # Javob sifatida faqat serializer data qaytariladi, frontend URLni olib yuklaydi
        return Response(serializer.data)

class LeaderboardView(generics.ListAPIView):
    serializer_class = UserRatingSerializer
    permission_classes = [AllowAny] # Reyting hamma uchun ochiq
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__full_name', 'user__study_place', 'user__region']
    filterset_fields = ['user__region']
    # ordering_fields = ['rank', 'total_score', 'math_score', 'physics_score', 'english_score']
    # ordering = ['rank'] # Default saralash

    def get_queryset(self):
        # Rankni har doim yangilab turish samarasiz, background task orqali qilish kerak
        # UserRating.update_ranks() # <<<--- BU YERDA QILMASLIK KERAK!
        queryset = UserRating.objects.filter(user__is_active=True, user__is_blocked=False).select_related('user').order_by('rank') # Oldindan hisoblangan rank bo'yicha
        subject = self.request.query_params.get('subject')
        # Region filteri filter_backends orqali avtomatik ishlaydi

        # Fan bo'yicha saralash (agar rank o'rniga ball bo'yicha kerak bo'lsa)
        subject_order_map = {
            'matematika': '-math_score',
            'fizika': '-physics_score',
            'ingliz_tili': '-english_score',
            # Boshqa fanlar...
        }
        order_field = subject_order_map.get(subject)
        if order_field:
             # Agar fan bo'yicha saralansa, rankni e'tiborsiz qoldiramiz
             return UserRating.objects.filter(user__is_active=True, user__is_blocked=False).select_related('user').order_by(order_field, '-total_score')

        return queryset

class MockTestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly] # <- Import qilingan
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['mock_type', 'language']
    search_fields = ['title', 'description']

    def get_queryset(self):
        # Faqat aktiv va vaqti kelgan mock testlar
        return MockTest.objects.filter(status='active', available_from__lte=timezone.now().date())

    def get_serializer_class(self):
        action_serializer_map = {
            'list': MockTestListSerializer,
            'retrieve': MockTestDetailSerializer,
            'start_exam': serializers.Serializer, # Ma'lumot kiritilmaydi
            'results': MockTestResultSerializer,
            'my_results': MockTestResultSerializer,
            'related_materials': MockTestMaterialSerializer,
        }
        return action_serializer_map.get(self.action, MockTestListSerializer)

    @action(detail=True, methods=['post'], url_path='start', permission_classes=[IsAuthenticated])
    def start_exam(self, request, pk=None):
         mock_test = self.get_object()
         user = request.user
         # ... (To'lov tekshiruvi va natija yaratish logikasi avvalgidek) ...
         if mock_test.price > 0:
            if not Payment.objects.filter(user=user, mock_test=mock_test, status='successful').exists():
                if user.balance < mock_test.price:
                    raise ValidationError(_("Mock testni boshlash uchun hisobingizda yetarli mablag' yo'q."))
                Payment.objects.create(
                     user=user, amount=-mock_test.price, payment_type='mock_test_purchase',
                     description=f"'{mock_test.title}' uchun to'lov", status='successful',
                     payment_method='internal', mock_test=mock_test
                )
                user.refresh_from_db()
         result, created = MockTestResult.objects.get_or_create(
            user=user, mock_test=mock_test, status='in_progress'
            # Agar qayta topshirish mumkin bo'lsa, bu yerda boshqacha logika kerak
         )
         # Bu yerda imtihonni boshlash uchun kerakli ma'lumotlarni qaytarish mumkin
         # Masalan, birinchi bo'lim ma'lumotlari yoki savollari
         return Response({ "detail": _("Imtihon boshlandi."), "result_id": result.id }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='results', permission_classes=[IsAuthenticated])
    def results(self, request, pk=None):
        mock_test = self.get_object()
        user = request.user
        try:
            latest_result = MockTestResult.objects.filter(user=user, mock_test=mock_test, status='completed').latest('end_time')
            serializer = self.get_serializer(latest_result, context={'request': request})
            return Response(serializer.data)
        except MockTestResult.DoesNotExist:
            raise NotFound(_("Siz bu mock testni hali topshirmagansiz."))

    @action(detail=False, methods=['get'], url_path='my-results', permission_classes=[IsAuthenticated])
    def my_results(self, request):
        user = request.user
        results = MockTestResult.objects.filter(user=user).select_related('mock_test').order_by('-start_time')
        page = self.paginate_queryset(results)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(results, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='materials', permission_classes=[IsAuthenticated])
    def related_materials(self, request):
        # Filter by user preferences or common materials
        queryset = MockTestMaterial.objects.all() # Filterlash logikasi qo'shilishi mumkin
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

class UniversityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = University.objects.all().order_by('region', 'name')
    serializer_class = UniversitySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['region']
    search_fields = ['name', 'short_name']

class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly] # <- Import qilingan
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['subject', 'difficulty', 'language', 'has_certificate', 'price']
    search_fields = ['title', 'subject__name', 'teacher__full_name', 'description']
    queryset = Course.objects.filter(status='active').select_related('subject', 'teacher').prefetch_related('lessons', 'reviews') # Oldindan olish

    def get_serializer_class(self):
        action_serializer_map = {
            'list': CourseListSerializer,
            'retrieve': CourseDetailSerializer,
            'my_courses': CourseEnrollmentSerializer,
            'enroll': serializers.Serializer, # Data kerak emas
            'leave_review': LeaveReviewSerializer,
        }
        return action_serializer_map.get(self.action, CourseListSerializer)

    @action(detail=False, methods=['get'], url_path='my-courses', permission_classes=[IsAuthenticated])
    def my_courses(self, request):
        enrollments = UserCourseEnrollment.objects.filter(user=request.user).select_related('course', 'course__subject').order_by('-enrolled_at')
        page = self.paginate_queryset(enrollments)
        if page is not None:
            # CourseEnrollmentSerializer ishlatish kerak
            serializer = CourseEnrollmentSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = CourseEnrollmentSerializer(enrollments, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        course = self.get_object()
        user = request.user
        # ... (To'lov tekshiruvi va enrollment yaratish logikasi avvalgidek) ...
        if UserCourseEnrollment.objects.filter(user=user, course=course).exists():
            return Response({"detail": _("Siz bu kursga allaqachon yozilgansiz.")}, status=status.HTTP_400_BAD_REQUEST)
        if course.price > 0:
             if user.balance < course.price:
                 raise ValidationError(_("Kursni sotib olish uchun hisobingizda yetarli mablag' yo'q."))
             Payment.objects.create(
                 user=user, amount=-course.price, payment_type='course_purchase',
                 description=f"'{course.title}' kursini sotib olish", status='successful',
                 payment_method='internal' # course=course
             )
             user.refresh_from_db()
        enrollment = UserCourseEnrollment.objects.create(user=user, course=course)
        course.enrolled_students_count = F('enrolled_students_count') + 1
        course.save(update_fields=['enrolled_students_count'])
        serializer = CourseEnrollmentSerializer(enrollment, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['post'], url_path='leave-review', permission_classes=[IsAuthenticated])
    def leave_review(self, request, pk=None):
        course = self.get_object()
        user = request.user
        # ... (Sharh qoldirish logikasi avvalgidek) ...
        if not UserCourseEnrollment.objects.filter(user=user, course=course).exists():
             raise PermissionDenied(_("Sharh qoldirish uchun avval kursga yozilishingiz kerak."))
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review, created = CourseReview.objects.update_or_create(
            user=user, course=course, defaults=serializer.validated_data
        )
        # Kurs reytingi Review.save() da avtomatik yangilanadi
        review_serializer = CourseReviewSerializer(review, context={'request': request})
        return Response(review_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ScheduleItemViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleItemSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    queryset = ScheduleItem.objects.all()

    def get_queryset(self):
        # Swagger schema generatsiyasi vaqtida xatolikni oldini olish
        if getattr(self, 'swagger_fake_view', False):
            return ScheduleItem.objects.none()  # Bo'sh queryset qaytarish
        return ScheduleItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()

    def get_queryset(self):
        # Swagger schema generatsiyasi vaqtida xatolikni oldini olish
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()  # Bo'sh queryset qaytarish
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_as_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'detail': _("Barcha bildirishnomalar o'qildi deb belgilandi.")})


# ==============================================
#               ADMIN PANEL VIEWS
# ==============================================
# IsAdminUser permission class yuqorida import qilingan

# --- Admin Dashboard Views ---


class AdminDashboardStatsView(generics.GenericAPIView):
    """Admin Dashboardidagi asosiy statistika kartalari uchun."""
    permission_classes = [IsAdminUser]
    serializer_class = AdminDashboardStatsSerializer

    def get(self, request, *args, **kwargs):
        period = request.query_params.get('period', 'month')
        try:
            start_current, end_current, start_previous, end_previous = get_date_ranges(period)
        except ValueError:
            return Response({"detail": "Invalid period parameter"}, status=status.HTTP_400_BAD_REQUEST)

        # --- Joriy Qiymatlar ---
        total_users_current = User.objects.count()
        active_students_current = User.objects.filter(role='student', is_active=True, is_blocked=False).count()
        tests_taken_current = UserTestResult.objects.filter(
            status='completed', start_time__gte=start_current, start_time__lte=end_current
        ).count() # Joriy davrda topshirilganlar
        revenue_current_agg = Payment.objects.filter(
            status='successful', amount__gt=0, created_at__gte=start_current, created_at__lte=end_current
        ).aggregate(total=Sum('amount'))
        revenue_current = revenue_current_agg['total'] or decimal.Decimal(0)

        # --- Oldingi Davr Qiymatlari (Foiz uchun) ---
        total_users_previous = User.objects.filter(date_joined__lt=start_current).count() # Davr boshigacha bo'lganlar
        # active_students_previous = ... # Bu metrika uchun aniqroq logika kerak
        active_students_previous = None
        tests_taken_previous = UserTestResult.objects.filter(
            status='completed', start_time__gte=start_previous, start_time__lt=end_previous
        ).count() # Oldingi davrda topshirilganlar
        revenue_previous_agg = Payment.objects.filter(
            status='successful', amount__gt=0, created_at__gte=start_previous, created_at__lt=end_previous
        ).aggregate(total=Sum('amount'))
        revenue_previous = revenue_previous_agg['total'] or decimal.Decimal(0)

        # --- Foizlar ---
        total_users_change = _calculate_percentage_change(total_users_current, total_users_previous)
        active_students_change = _calculate_percentage_change(active_students_current, active_students_previous)
        tests_taken_change = _calculate_percentage_change(tests_taken_current, tests_taken_previous) # <<< QO'SHILDI
        revenue_change = _calculate_percentage_change(revenue_current, revenue_previous)

        # --- Maqsadlar ---
        target_users = 8000
        target_active_students = 6000
        target_tests_taken = 1500 # Misol uchun maqsad
        target_revenue = decimal.Decimal('35000000.00')

        # --- Serializer uchun Data ---
        data = {
            'total_users': {'value': total_users_current, 'change_percentage': total_users_change, 'target': target_users},
            'active_students': {'value': active_students_current, 'change_percentage': active_students_change, 'target': target_active_students},
            'total_tests_taken': {'value': tests_taken_current, 'change_percentage': tests_taken_change, 'target': target_tests_taken}, # <<< QO'SHILDI
            'total_revenue': {'value': revenue_current, 'change_percentage': revenue_change, 'target': target_revenue},
        }
        serializer = self.get_serializer(data) # Endi AdminDashboardStatsSerializer
        # Serializerga ma'lumot to'g'ri formatda uzatilayotganini tekshirish uchun:
        # print(serializer.initial_data)
        return Response(serializer.data)

class AdminDashboardLatestListsView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminDashboardLatestListsSerializer  # Serializer qo'shildi

    def get(self, request, *args, **kwargs):
        latest_users = User.objects.order_by('-date_joined')[:5]
        latest_tests = Test.objects.select_related('subject').order_by('-created_at')[:5]
        latest_payments = Payment.objects.select_related('user').order_by('-created_at')[:5]
        data = {
            'latest_users': AdminLastRegisteredUserSerializer(latest_users, many=True).data,
            'latest_tests': AdminLatestTestSerializer(latest_tests, many=True).data,
            'latest_payments': AdminLatestPaymentSerializer(latest_payments, many=True, context={'request': request}).data,
        }
        serializer = self.get_serializer(data)
        return Response(serializer.data)

# --- Admin Statistics Views (Separate) ---
# BU VIEWLAR UCHUN SERIALIZERLARNI TO'G'RI YARATISH VA DATA NI O'SHALARGA MOSLASH KERAK


class AdminCombinedStatisticsView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminCombinedStatisticsSerializer

    def get(self, request, *args, **kwargs):
        # ... (period va sanalarni olish avvalgidek) ...
        period = request.query_params.get('period', 'month')
        try:
            start_current, end_current, start_previous, end_previous = get_date_ranges(period)
        except ValueError:
            return Response({"detail": "Invalid period parameter"}, status=status.HTTP_400_BAD_REQUEST)

        # ... (user_stats hisoblash qismi) ...
        users = User.objects.all()
        new_users_current = users.filter(date_joined__gte=start_current, date_joined__lte=end_current).count()
        new_users_prev = users.filter(date_joined__gte=start_previous, date_joined__lt=end_previous).count()
        new_users_change = _calculate_percentage_change(new_users_current, new_users_prev)

        active_users_current_snapshot = users.filter(is_active=True, is_blocked=False).count()
        active_users_in_current_period = users.filter(is_blocked=False, last_login__gte=start_current, last_login__lte=end_current).count()
        active_users_in_previous_period = users.filter(is_blocked=False, last_login__gte=start_previous, last_login__lt=end_previous).count()
        active_users_change = _calculate_percentage_change(active_users_in_current_period, active_users_in_previous_period)

        # O'rtacha faollik (placeholder - haqiqiy hisoblash kerak)
        average_activity_minutes = 24
        average_activity_previous_minutes = 22 # Oldingi davr uchun ham hisoblash kerak
        average_activity_change = _calculate_percentage_change(average_activity_minutes, average_activity_previous_minutes)

        users_graph_qs = (
            users.filter(date_joined__gte=start_current, date_joined__lte=end_current)
            .annotate(date=TruncDate('date_joined'))
            .values('date').annotate(value=Count('id')).order_by('date')
        )

        # User ma'lumotlarini TO'G'RI formatda yig'ish
        user_stats = {
            'users_graph': list(users_graph_qs),
            'new_users': {'value': new_users_current, 'change_percentage': new_users_change},
            'active_users': {'value': active_users_current_snapshot, 'change_percentage': active_users_change},
            # average_activity ni DetailedCharStatSerializer kutadigan formatga keltiramiz:
            'average_activity': {
                'value': f"{average_activity_minutes} min",
                'change_percentage': average_activity_change
            },
        }

        # ... (test_stats, payment_stats, course_stats hisoblash avvalgidek) ...
        # Faqat qiymatlarni to'g'ri formatda (lug'at) berishga e'tibor bering

        # --- 2. Testlar Statistikasi ---
        tests = Test.objects.all()
        results = UserTestResult.objects.filter(status='completed')
        tests_taken_current = results.filter(start_time__gte=start_current, start_time__lte=end_current).count()
        avg_score_current = results.filter(start_time__gte=start_current, start_time__lte=end_current).aggregate(avg=Avg('percentage'))['avg'] or 0
        tests_taken_prev = results.filter(start_time__gte=start_previous, start_time__lt=end_previous).count()
        avg_score_prev = results.filter(start_time__gte=start_previous, start_time__lt=end_previous).aggregate(avg=Avg('percentage'))['avg'] or 0
        tests_taken_change = _calculate_percentage_change(tests_taken_current, tests_taken_prev)
        avg_score_change = _calculate_percentage_change(avg_score_current, avg_score_prev)
        tests_graph_qs = (results.filter(start_time__gte=start_current, start_time__lte=end_current)
                          .annotate(date=TruncDate('start_time')).values('date')
                          .annotate(value=Count('id')).order_by('date'))
        test_stats = {
            'tests_graph': list(tests_graph_qs),
            'total_tests': {'value': tests.count(), 'change_percentage': None},
            'tests_taken': {'value': tests_taken_current, 'change_percentage': tests_taken_change},
            'average_score': {'value': round(avg_score_current), 'change_percentage': avg_score_change}, # Round to int for DetailedStatSerializer
        }

        # --- 3. To'lovlar Statistikasi ---
        payments_success = Payment.objects.filter(status='successful')
        income_current = payments_success.filter(amount__gt=0, created_at__gte=start_current, created_at__lte=end_current).aggregate(total=Sum('amount'))['total'] or decimal.Decimal(0)
        expenses_current = abs(payments_success.filter(amount__lt=0, created_at__gte=start_current, created_at__lte=end_current).aggregate(total=Sum('amount'))['total'] or decimal.Decimal(0))
        avg_payment_current = payments_success.filter(amount__gt=0, created_at__gte=start_current, created_at__lte=end_current).aggregate(avg=Avg('amount'))['avg'] or decimal.Decimal(0)
        income_prev = payments_success.filter(amount__gt=0, created_at__gte=start_previous, created_at__lt=end_previous).aggregate(total=Sum('amount'))['total'] or decimal.Decimal(0)
        expenses_prev = abs(payments_success.filter(amount__lt=0, created_at__gte=start_previous, created_at__lt=end_previous).aggregate(total=Sum('amount'))['total'] or decimal.Decimal(0))
        avg_payment_prev = payments_success.filter(amount__gt=0, created_at__gte=start_previous, created_at__lt=end_previous).aggregate(avg=Avg('amount'))['avg'] or decimal.Decimal(0)
        income_change = _calculate_percentage_change(income_current, income_prev)
        expenses_change = _calculate_percentage_change(expenses_current, expenses_prev)
        avg_payment_change = _calculate_percentage_change(avg_payment_current, avg_payment_prev)
        payments_graph_qs = (payments_success.filter(created_at__gte=start_current, created_at__lte=end_current)
                             .annotate(date=TruncDate('created_at')).values('date')
                             .annotate(value=Count('id')).order_by('date'))
        payment_stats = {
            'payments_graph': list(payments_graph_qs),
            'total_income': {'value': income_current, 'change_percentage': income_change},
            'total_expenses': {'value': expenses_current, 'change_percentage': expenses_change},
            'average_payment': {'value': avg_payment_current, 'change_percentage': avg_payment_change},
        }

        # --- 4. Kurslar Statistikasi ---
        courses = Course.objects.filter(status='active')
        enrollments = UserCourseEnrollment.objects.all()
        total_courses_current = courses.count()
        enrollments_current = enrollments.filter(enrolled_at__gte=start_current, enrolled_at__lte=end_current).count()
        enrollments_prev = enrollments.filter(enrolled_at__gte=start_previous, enrolled_at__lt=end_previous).count()
        enrollments_change = _calculate_percentage_change(enrollments_current, enrollments_prev)
        completions_current = enrollments.filter(completed_at__gte=start_current, completed_at__lte=end_current).count()
        completions_prev = enrollments.filter(completed_at__gte=start_previous, completed_at__lt=end_previous).count()
        completions_change = _calculate_percentage_change(completions_current, completions_prev)
        courses_graph_qs = (enrollments.filter(enrolled_at__gte=start_current, enrolled_at__lte=end_current)
                           .annotate(date=TruncDate('enrolled_at')).values('date')
                           .annotate(value=Count('id')).order_by('date'))
        course_stats = {
            'courses_graph': list(courses_graph_qs),
            'total_courses': {'value': total_courses_current, 'change_percentage': None},
            'enrollments': {'value': enrollments_current, 'change_percentage': enrollments_change},
            'completions': {'value': completions_current, 'change_percentage': completions_change},
        }


        # --- Yakuniy Data ---
        final_data = {
            "users": user_stats,
            "tests": test_stats,
            "payments": payment_stats,
            "courses": course_stats
        }

        serializer = self.get_serializer(final_data)
        # Debug uchun:
        # print("Serializer Initial Data:", serializer.initial_data)
        return Response(serializer.data)



# --- Admin CRUD ViewSets ---
# (AdminUserViewSet, AdminTestViewSet, AdminQuestionViewSet, AdminMaterialViewSet, AdminPaymentViewSet,
#  AdminUniversityViewSet, AdminAchievementViewSet, AdminCourseViewSet, AdminLessonViewSet
#  avvalgi kodimdagi kabi qoladi, chunki ular urls.py ga mos edi)


class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().prefetch_related('settings', 'rating', 'groups')
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_blocked', 'gender', 'region']
    search_fields = ['email', 'full_name', 'phone_number']
    ordering_fields = ['date_joined', 'full_name', 'email', 'balance']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        # FAQAT standart actionlar uchun serializer qaytaramiz
        if self.action == 'list':
            return AdminUserListSerializer
        elif self.action == 'create':
            return AdminUserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AdminUserUpdateSerializer
        elif self.action == 'retrieve':
            return UserSerializer
        # Custom actionlar uchun serializer qaytarmaymiz,
        # swagger_auto_schema ga ishonamiz
        # Agar shunda ham ishlamasa, default serializer qaytarish kerak bo'ladi
        return None # <<<--- O'ZGARTIRISHLAR ---<<<

    @action(detail=True, methods=['get'], url_path='payment-history')
    @swagger_auto_schema(
        operation_summary="Foydalanuvchining to'lov tarixini olish",
        responses={status.HTTP_200_OK: PaymentSerializer(many=True)}
    )
    def user_payment_history(self, request, pk=None):
        user = self.get_object()
        payments = Payment.objects.filter(user=user).order_by('-created_at')
        # Serializerni aniq chaqiramiz:
        serializer = PaymentSerializer(payments, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='statistics')
    @swagger_auto_schema(
        operation_summary="Foydalanuvchi statistikasini olish",
        responses={status.HTTP_200_OK: AdminUserStatisticsDetailSerializer()}
    )
    def user_statistics(self, request, pk=None):
        user = self.get_object()
        # ... (Statistika hisoblash avvalgidek) ...
        completed_tests = UserTestResult.objects.filter(user=user, status='completed').count()
        avg_score_agg = UserTestResult.objects.filter(user=user, status='completed').aggregate(avg=Avg('percentage'))
        avg_score = avg_score_agg['avg'] if avg_score_agg['avg'] else 0
        total_payments = Payment.objects.filter(user=user, status='successful', amount__gt=0).aggregate(total=Sum('amount'))['total'] or decimal.Decimal('0.00')
        data = {
            "completed_tests": completed_tests,
            "average_score": round(avg_score, 2),
            "total_payments": total_payments,
        }
        # Serializerni aniq chaqiramiz:
        serializer = AdminUserStatisticsDetailSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='test-history')
    @swagger_auto_schema(
        operation_summary="Foydalanuvchining test tarixini olish",
        responses={status.HTTP_200_OK: UserTestResultSerializer(many=True)}
    )
    def user_test_history(self, request, pk=None):
        user = self.get_object()
        results = UserTestResult.objects.filter(user=user).select_related('test', 'test__subject').order_by('-start_time')
        # Serializerni aniq chaqiramiz:
        serializer = UserTestResultSerializer(results, many=True, context={'request': request})
        return Response(serializer.data)

    # --- Boshqa actionlar o'zgarishsiz qoladi ---
    @action(detail=True, methods=['post'], url_path='add-balance')
    @swagger_auto_schema(
        operation_summary="Foydalanuvchi hisobini to'ldirish (Admin)",
        request_body=AdminAddBalanceSerializer,
        responses={status.HTTP_200_OK: UserSerializer()}
    )
    def add_balance(self, request, pk=None):
        user = self.get_object()
        balance_serializer = AdminAddBalanceSerializer(data=request.data)
        balance_serializer.is_valid(raise_exception=True)
        amount = balance_serializer.validated_data['amount']
        description = balance_serializer.validated_data.get('description', _('Admin tomonidan hisob to\'ldirildi'))
        Payment.objects.create(
            user=user, amount=amount, payment_type='bonus', status='successful',
            payment_method='admin', description=description
        )
        user.refresh_from_db()
        user_serializer = UserSerializer(user, context={'request': request})
        return Response(user_serializer.data)

    @action(detail=True, methods=['post'], url_path='block')
    @swagger_auto_schema(responses={status.HTTP_200_OK: UserSerializer()})
    def block_user(self, request, pk=None):
        user = self.get_object()
        user.is_blocked = True; user.is_active = False
        user.save(update_fields=['is_blocked', 'is_active'])
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='unblock')
    @swagger_auto_schema(responses={status.HTTP_200_OK: UserSerializer()})
    def unblock_user(self, request, pk=None):
        user = self.get_object()
        user.is_blocked = False; user.is_active = True
        user.save(update_fields=['is_blocked', 'is_active'])
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save()

class AdminTestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.select_related('subject', 'created_by').prefetch_related('questions')
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'difficulty', 'test_type', 'status']
    search_fields = ['title', 'subject__name']
    ordering_fields = ['created_at', 'title', 'question_count', 'price']
    ordering = ['-created_at']

    def get_serializer_class(self):
        action_serializer_map = {
            'list': AdminTestListSerializer,
            'create': AdminTestCreateUpdateSerializer,
            'update': AdminTestCreateUpdateSerializer,
            'partial_update': AdminTestCreateUpdateSerializer,
            'retrieve': TestDetailSerializer, # Savollar bilan ko'rsatish
            'participants': UserTestResultSerializer,
            'statistics': serializers.Serializer, # Maxsus serializer kerak bo'lishi mumkin
        }
        return action_serializer_map.get(self.action, TestDetailSerializer) # Default retrieve uchun

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='participants')
    def participants(self, request, pk=None):
        test = self.get_object()
        results = UserTestResult.objects.filter(test=test).select_related('user').order_by('-start_time') # Hamma statusdagini olish mumkin
        page = self.paginate_queryset(results)
        serializer_context = self.get_serializer_context()
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=serializer_context)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(results, many=True, context=serializer_context)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='statistics')
    def statistics(self, request, pk=None):
        test = self.get_object()
        # ... (Statistika hisoblash avvalgidek) ...
        participants_count = UserTestResult.objects.filter(test=test, status='completed').count()
        avg_score = UserTestResult.objects.filter(test=test, status='completed').aggregate(avg=Avg('percentage'))['avg'] or 0
        total_income = Payment.objects.filter(test=test, status='successful', payment_type='test_purchase').aggregate(total=Sum('amount'))['total'] or 0
        # Serializer ishlatish yaxshiroq
        return Response({
            "participants_count": participants_count,
            "average_score": round(avg_score, 2),
            "total_income": abs(total_income) if total_income else 0,
        })

class AdminQuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.select_related('test') # Testni ham olish
    serializer_class = AdminQuestionSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None # Odatda test savollari ko'p bo'lmaydi

    def get_queryset(self):
        test_pk = self.kwargs.get('test_pk')
        if test_pk:
            return Question.objects.filter(test_id=test_pk).order_by('order', 'id')
        # Agar nested bo'lmasa (masalan, /api/admin/questions/), bo'sh queryset qaytarish mumkin
        return Question.objects.none()

    def perform_create(self, serializer):
        test_pk = self.kwargs.get('test_pk')
        if not test_pk: raise ValidationError(_("URL da test ID si ko'rsatilmagan."))
        test = get_object_or_404(Test, pk=test_pk)
        # Orderni avtomatik belgilash (oxirgisidan keyingi)
        last_order = Question.objects.filter(test=test).aggregate(max_order=Max('order'))['max_order'] or 0
        instance = serializer.save(test=test, order=last_order + 1)
        test.question_count = F('question_count') + 1 # Atomik tarzda oshirish
        test.save(update_fields=['question_count'])

    def perform_update(self, serializer):
         # Testni o'zgartirmaslik kerak
         serializer.save()

    def perform_destroy(self, instance):
        test = instance.test
        instance.delete()
        # Atomik tarzda kamaytirish
        test.question_count = F('question_count') - 1
        test.save(update_fields=['question_count'])
        # Qolgan savollarning orderini yangilash kerak bo'lishi mumkin

class AdminMaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.select_related('subject', 'uploaded_by')
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'material_type', 'file_format', 'status', 'is_free']
    search_fields = ['title', 'subject__name']
    ordering_fields = ['uploaded_at', 'title', 'downloads_count']
    ordering = ['-uploaded_at']

    def get_serializer_class(self):
        if self.action == 'list': return AdminMaterialListSerializer
        return AdminMaterialCreateUpdateSerializer

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

class AdminPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.select_related('user').order_by('-created_at')
    serializer_class = PaymentSerializer # Admin ham shu serializerdan foydalansin
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'status', 'payment_type', 'payment_method']
    search_fields = ['user__email', 'user__full_name', 'transaction_id']
    ordering_fields = ['created_at', 'amount']

class AdminUniversityViewSet(viewsets.ModelViewSet):
    queryset = University.objects.all().order_by('region', 'name')
    serializer_class = UniversitySerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['region']
    search_fields = ['name', 'short_name']

class AdminAchievementViewSet(viewsets.ModelViewSet):
    queryset = Achievement.objects.all().order_by('category', 'name')
    serializer_class = AchievementSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']

class AdminCourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related('subject', 'teacher').prefetch_related('lessons', 'reviews')
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'teacher', 'status', 'difficulty', 'language']
    search_fields = ['title', 'subject__name', 'teacher__full_name']
    ordering_fields = ['created_at', 'title', 'price', 'rating', 'enrolled_students_count']
    ordering = ['-created_at']

    def get_serializer_class(self):
        action_serializer_map = {
            'list': CourseListSerializer, # Admin ham student ko'radigan listni ko'rsin
            'retrieve': CourseDetailSerializer, # Darslar va sharhlar bilan
            'create': CourseDetailSerializer, # Yaratish uchun ham shu (yoki maxsus)
            'update': CourseDetailSerializer,
            'partial_update': CourseDetailSerializer,
            'enrollments': CourseEnrollmentSerializer,
            'reviews': CourseReviewSerializer,
        }
        return action_serializer_map.get(self.action, CourseDetailSerializer)

    # perform_create da teacher ni belgilash kerak bo'lishi mumkin
    # def perform_create(self, serializer):
    #     serializer.save(teacher=self.request.user) # Agar admin o'qituvchi bo'lsa

    @action(detail=True, methods=['get'], url_path='enrollments')
    def enrollments(self, request, pk=None):
        course = self.get_object()
        enrolls = UserCourseEnrollment.objects.filter(course=course).select_related('user')
        page = self.paginate_queryset(enrolls)
        serializer_context = self.get_serializer_context()
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=serializer_context)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(enrolls, many=True, context=serializer_context)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='reviews')
    def reviews(self, request, pk=None):
        course = self.get_object()
        reviews_qs = CourseReview.objects.filter(course=course).select_related('user').order_by('-created_at')
        page = self.paginate_queryset(reviews_qs)
        serializer_context = self.get_serializer_context()
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=serializer_context)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(reviews_qs, many=True, context=serializer_context)
        return Response(serializer.data)


class AdminLessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.select_related('course')
    serializer_class = LessonSerializer # Admin ham shu serializerdan foydalansin
    permission_classes = [IsAdminUser]
    pagination_class = None # Kurs darslari odatda ko'p emas

    def get_queryset(self):
        course_pk = self.kwargs.get('course_pk')
        if course_pk:
            return Lesson.objects.filter(course_id=course_pk).order_by('order', 'id')
        return Lesson.objects.none() # Nested bo'lmasa ko'rsatma

    def perform_create(self, serializer):
        course_pk = self.kwargs.get('course_pk')
        if not course_pk: raise ValidationError(_("URL da kurs ID si ko'rsatilmagan."))
        course = get_object_or_404(Course, pk=course_pk)
        # Orderni avtomatik belgilash
        last_order = Lesson.objects.filter(course=course).aggregate(max_order=Max('order'))['max_order'] or 0
        instance = serializer.save(course=course, order=last_order + 1)
        course.update_lessons_count()

    def perform_update(self, serializer):
        # Kursni o'zgartirish mumkin emas
        instance = serializer.save()
        # Agar order o'zgarsa, boshqa darslarning orderini yangilash kerak bo'lishi mumkin

    def perform_destroy(self, instance):
        course = instance.course
        instance.delete()
        course.update_lessons_count()




