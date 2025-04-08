


# users/serializers.py
import decimal
from rest_framework import serializers
from django.contrib.auth import get_user_model, password_validation, authenticate
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import (
    User, Subject, Test, Question, UserTestResult, UserAnswer, Material, Payment,
    UserRating, MockTest, MockTestResult, MockTestMaterial, University,
    Achievement, UserAchievement, Course, Lesson, UserCourseEnrollment,
    CourseReview, ScheduleItem, Notification, UserSettings
)
try:
    import readtime # Optional: pip install django-readtime
except ImportError:
    readtime = None


User = get_user_model()

# --- Authentication Serializers ---

class SignupSerializer(serializers.ModelSerializer):
    # Frontend nomlari bilan fieldlarni e'lon qilamiz va `source` orqali bog'laymiz
    email = serializers.EmailField(required=True)
    fullName = serializers.CharField(source='full_name', required=True, label=_("Full Name"))
    phone = serializers.CharField(source='phone_number', required=True, label=_("Phone Number"))
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    # password2 olib tashlandi
    agreeToTerms = serializers.BooleanField(source='agreetoterms', required=True, write_only=True, label=_("Agree to Terms"))

    # Ixtiyoriy maydonlar (frontend nomlari bilan)
    birthDate = serializers.DateField(source='birth_date', required=False, allow_null=True, label=_("Birth Date"))
    gender = serializers.ChoiceField(choices=User.GENDER_CHOICES, required=False, allow_null=True)
    grade = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    region = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    school = serializers.CharField(source='study_place', required=False, allow_null=True, allow_blank=True, label=_("School/Study Place"))

    class Meta:
        model = User
        # Frontend yuboradigan field nomlarini ko'rsatamiz
        fields = (
            'email', 'fullName', 'phone', 'password', 'agreeToTerms', # password2 yo'q
            'birthDate', 'gender', 'grade', 'region', 'school'
        )
        # `extra_kwargs` da ham frontend nomlarini ishlatsa bo'ladi, lekin source borligi uchun shart emas
        # Faqat password write_only bo'lishi muhim
        extra_kwargs = {
            'password': {'write_only': True},
        }

    # --- Validationlar ---
    def validate_email(self, value): # Bu nom to'g'ri
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("Bu email manzili allaqachon ro'yxatdan o'tgan."))
        return value

    def validate_phone(self, value): # Frontend nomi 'phone'
        # phone maydoniga kelgan qiymatni validate qilamiz
        if not value:
             raise serializers.ValidationError(_("Telefon raqam kiritilishi shart."))
        if not value.startswith('+998') or len(value) != 13 or not value[1:].isdigit():
             raise serializers.ValidationError(_("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak."))
        # Model maydoni (`phone_number`) bo'yicha tekshiramiz
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(_("Bu telefon raqam allaqachon ro'yxatdan o'tgan."))
        return value

    def validate(self, data):
        # agreeToTerms (frontend nomi) bilan tekshiramiz
        if not data.get('agreetoterms'):
            raise serializers.ValidationError({"agreeToTerms": _("Ro'yxatdan o'tish uchun shartlarga rozilik bildiring.")})
        # password2 tekshiruvi olib tashlandi
        # Kuchli parol tekshiruvi
        try:
            # 'password' kaliti bilan (frontend nomi)
            password_validation.validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        # Role avtomatik belgilanadi create() yoki create_user() ichida
        return data

    def create(self, validated_data):
        # password2 ni pop qilish kerak emas
        # agreeToTerms ni pop qilish shart emas, source borligi uchun create_user ga to'g'ri nom bilan ketadi
        # Faqat create_user ga role='student' ekanligini berish kerak
        validated_data['role'] = 'student'
        # `source` tufayli validated_data ichida model field nomlari bo'ladi
        # Masalan: {'email': '...', 'full_name': '...', 'phone_number': '...', 'password': '...'}
        user = User.objects.create_user(**validated_data)
        # UserManager.create_user avtomatik rating va settings yaratishi kerak (avvalgi kod bo'yicha)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, label=_("Email"))
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label=_("Password")
    )
    token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        request = self.context.get('request')

        # Authenticate using email and password
        user = authenticate(request=request, email=email, password=password)

        if user is None:
            raise serializers.ValidationError(
                _("Email yoki parol noto'g'ri."),
                code='authorization'
            )
        if not user.is_active:
            raise serializers.ValidationError(
                _("Foydalanuvchi akkaunti faol emas."),
                code='authorization'
            )
        if user.is_blocked:
            raise serializers.ValidationError(
                _("Foydalanuvchi akkaunti bloklangan."),
                code='authorization'
            )

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        data['refresh_token'] = str(refresh)
        data['token'] = str(refresh.access_token)
        data['user_instance'] = user  # Store user instance for get_user method

        return data

    def get_user(self, obj):
        user_instance = obj.get('user_instance')
        if user_instance:
            # Return user info including role
            return {
                'id': user_instance.id,  # Fixed magnaid to id
                'full_name': user_instance.full_name,
                'email': user_instance.email,
                'role': user_instance.role,  # Direct role value
                'role_display': user_instance.get_role_display(),  # Human-readable role
            }
        return None


# --- User Profile & Settings Serializers ---

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        exclude = ('user',) # Exclude user foreign key

class UserRatingSerializer(serializers.ModelSerializer):
    level_progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserRating
        exclude = ('user',) # Exclude user foreign key
        read_only_fields = ('total_score', 'rank', 'level', 'points_to_next_level', 'current_level_points', 'last_updated')

    def get_level_progress_percentage(self, obj):
         # Calculate progress towards the next level threshold
         current_level_threshold = obj.LEVEL_THRESHOLDS.get(obj.level, 0)
         next_level_threshold = obj.points_to_next_level

         if next_level_threshold is None or next_level_threshold <= current_level_threshold:
             return 100.0 # Max level or invalid threshold

         total_points_for_level = next_level_threshold - current_level_threshold
         points_earned_in_level = obj.total_score - current_level_threshold

         if total_points_for_level > 0:
             percentage = (points_earned_in_level / total_points_for_level) * 100
             return round(max(0, min(percentage, 100)), 2) # Ensure between 0 and 100
         return 0.0


class UserSerializer(serializers.ModelSerializer):
    settings = UserSettingsSerializer(read_only=True)
    rating = UserRatingSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    balance_display = serializers.CharField(source='get_balance_display', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'full_name', 'phone_number', 'role', 'role_display',
            'profile_picture', 'balance', 'balance_display', 'date_joined', 'is_active', 'is_blocked',
            'birth_date', 'gender', 'gender_display', 'grade', 'region', 'study_place',
            'address', 'target_university', 'target_faculty', 'about_me',
            'settings', 'rating'
        )
        read_only_fields = ('id', 'email', 'role', 'role_display', 'balance', 'balance_display', 'date_joined', 'is_active', 'is_blocked', 'settings', 'rating')

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'full_name', 'phone_number', 'birth_date', 'gender', 'profile_picture',
            'grade', 'region', 'study_place', 'address',
            'target_university', 'target_faculty', 'about_me'
        )
        extra_kwargs = {
            'profile_picture': {'required': False, 'allow_null': True},
            'full_name': {'required': False},
            'phone_number': {'required': False},
            'birth_date': {'required': False, 'allow_null': True},
            'gender': {'required': False, 'allow_null': True},
            'grade': {'required': False, 'allow_blank': True},
            'region': {'required': False, 'allow_blank': True},
            'study_place': {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'target_university': {'required': False, 'allow_blank': True},
            'target_faculty': {'required': False, 'allow_blank': True},
            'about_me': {'required': False, 'allow_blank': True},
        }

    def validate_phone_number(self, value):
        user = self.context['request'].user
        if not value:
            raise serializers.ValidationError(_("Telefon raqami bo'sh bo'lishi mumkin emas."))
        if not value.startswith('+998') or len(value) != 13 or not value[1:].isdigit():
             raise serializers.ValidationError(_("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak."))
        if User.objects.filter(phone_number=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError(_("Bu telefon raqam boshqa foydalanuvchiga tegishli."))
        return value

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password2 = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'}, label=_("Confirm New Password"))

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Joriy parol noto'g'ri."))
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({"new_password": _("Yangi parollar mos kelmadi.")}) # Error on new_password field
        try:
            password_validation.validate_password(data['new_password'], user=self.context['request'].user)
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class ProfileSettingsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = (
            'language', 'theme', 'autoplay_videos', 'sound_effects', 'high_contrast',
            'notify_email', 'notify_sms', 'notify_push',
            'notify_test_updates', 'notify_course_updates', 'notify_payments', 'notify_reminders',
            'two_factor_enabled', 'weekly_reports', 'personalized_recommendations'
        )


# --- Subject Serializer ---
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ('id', 'name', 'icon')

# --- Test & Question Serializers ---
class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for displaying questions during a test (without correct answer)."""
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'order', 'question_text', 'difficulty', 'difficulty_display', 'points',
                  'option_a', 'option_b', 'option_c', 'option_d')

class QuestionResultSerializer(QuestionSerializer):
    """Serializer for displaying question details in results (with correct answer and explanation)."""
    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + ('correct_answer', 'explanation',)


class TestListSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_icon = serializers.ImageField(source='subject.icon', read_only=True, use_url=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    type_display = serializers.CharField(source='get_test_type_display', read_only=True)
    price_display = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ('id', 'title', 'subject', 'subject_name', 'subject_icon', 'test_type', 'type_display', 'question_count',
                  'difficulty', 'difficulty_display', 'price', 'price_display', 'time_limit', 'reward_points')

    def get_price_display(self, obj):
        if obj.test_type == 'free' or obj.price <= 0:
            return _("Bepul")
        return f"{obj.price:,.0f} so'm".replace(',', ' ')


class TestDetailSerializer(TestListSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta(TestListSerializer.Meta):
        fields = TestListSerializer.Meta.fields + ('description', 'questions')


class SubmitAnswerSerializer(serializers.Serializer):
    # Example: { "answers": { "101": "A", "102": "C", "105": "B" } }
    answers = serializers.DictField(
        child=serializers.ChoiceField(choices=Question.ANSWER_CHOICES, allow_blank=True), # Allow skipping questions
        required=True
    )

class UserAnswerSerializer(serializers.ModelSerializer):
    question = QuestionResultSerializer(read_only=True) # Show full question details in results

    class Meta:
        model = UserAnswer
        fields = ('question', 'selected_answer', 'is_correct')

class UserTestResultSerializer(serializers.ModelSerializer):
    test = TestListSerializer(read_only=True)
    user_answers = UserAnswerSerializer(many=True, read_only=True)
    time_spent_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    score_display = serializers.SerializerMethodField()

    class Meta:
        model = UserTestResult
        fields = ('id', 'user', 'test', 'score', 'score_display', 'total_questions', 'percentage',
                  'start_time', 'end_time', 'time_spent', 'time_spent_display', 'status', 'status_display', 'user_answers')
        read_only_fields = fields

    def get_time_spent_display(self, obj):
        if obj.time_spent:
            total_seconds = int(obj.time_spent.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return None

    def get_score_display(self, obj):
        # Display score relative to possible points based on questions answered
        total_possible_points = sum(ua.question.points for ua in obj.user_answers.all() if ua.question)
        # Or use test.questions.aggregate(Sum('points'))['points__sum'] if all questions were presented
        return f"{obj.score} / {total_possible_points}" if total_possible_points else f"{obj.score}"


# --- Material Serializers ---
class MaterialSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    format_display = serializers.CharField(source='get_file_format_display', read_only=True)
    size_display = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True, default='')

    class Meta:
        model = Material
        fields = ('id', 'title', 'subject', 'subject_name', 'description', 'material_type', 'type_display',
                  'file_format', 'format_display', 'file', 'link', 'size_mb', 'size_display',
                  'downloads_count', 'status', 'uploaded_at', 'uploaded_by_name', 'is_free', 'price', 'price_display', 'download_url')
        read_only_fields = ('id', 'subject_name', 'type_display', 'format_display', 'size_display',
                          'downloads_count', 'uploaded_at', 'uploaded_by_name', 'download_url', 'price_display')

    def get_size_display(self, obj):
        if obj.size_mb is not None:
            return f"{obj.size_mb:.1f} MB" if obj.size_mb >= 1 else f"{obj.size_mb * 1024:.1f} KB"
        elif obj.file:
             try: return f"{obj.file.size / (1024*1024):.1f} MB" if obj.file.size >= 1024*1024 else f"{obj.file.size / 1024:.1f} KB"
             except Exception: return "-"
        return "-"

    def get_download_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.link

    def get_price_display(self, obj):
        if obj.is_free or obj.price <= 0:
            return _("Bepul")
        return f"{obj.price:,.0f} so'm".replace(',', ' ')


# --- Payment Serializers ---
class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    amount_display = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ('id', 'user', 'user_email', 'amount', 'amount_display', 'payment_type', 'type_display',
                  'description', 'status', 'status_display', 'payment_method', 'method_display',
                  'transaction_id', 'created_at', 'test', 'material', 'mock_test', 'course') # Added course
        read_only_fields = ('id', 'user', 'user_email', 'amount_display', 'type_display', 'status_display',
                          'method_display', 'created_at', 'transaction_id', 'test', 'material', 'mock_test', 'course')

    def get_amount_display(self, obj):
        sign = "+" if obj.amount >= 0 else "" # Amount itself can be negative for expenses
        return f"{sign}{obj.amount:,.0f} so'm".replace(',', ' ')


import decimal

class AddFundsSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=decimal.Decimal('1000'))
    payment_method = serializers.ChoiceField(
        choices=[choice for choice in Payment.PAYMENT_METHOD_CHOICES if choice[0] not in ['internal', 'admin']]
    )
# --- Mock Test Serializers ---
class MockTestListSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_mock_type_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True, default='')
    price_display = serializers.SerializerMethodField()

    class Meta:
        model = MockTest
        fields = ('id', 'title', 'mock_type', 'type_display', 'language', 'language_display',
                  'price', 'price_display', 'status', 'available_from')

    def get_price_display(self, obj):
        return f"{obj.price:,.0f} so'm".replace(',', ' ') if obj.price > 0 else _("Bepul") # Assume 0 means free

class MockTestDetailSerializer(MockTestListSerializer):
    class Meta(MockTestListSerializer.Meta):
        fields = MockTestListSerializer.Meta.fields + ('description', 'duration_minutes', 'sections_info', 'rules')

class MockTestResultSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    mock_test_title = serializers.CharField(source='mock_test.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = MockTestResult
        fields = ('id', 'user', 'user_full_name', 'mock_test', 'mock_test_title', 'overall_score',
                  'section_scores', 'status', 'status_display', 'start_time', 'end_time', 'feedback')
        read_only_fields = fields


class MockTestMaterialSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_mock_test_type_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True, default='')
    format_display = serializers.CharField(source='get_material_format_display', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MockTestMaterial
        fields = ('id', 'title', 'mock_test_type', 'type_display', 'language', 'language_display',
                  'description', 'file', 'link', 'material_format', 'format_display', 'is_free', 'download_url')
        read_only_fields = ('id', 'type_display', 'language_display', 'format_display', 'download_url')

    def get_download_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.link

# --- University Serializer ---
class UniversitySerializer(serializers.ModelSerializer):
    region_display = serializers.CharField(source='get_region_display', read_only=True)
    class Meta:
        model = University
        fields = '__all__'


# --- Achievement Serializers ---
class AchievementSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    class Meta:
        model = Achievement
        fields = ('id', 'name', 'description', 'category', 'category_display', 'points_reward', 'icon', 'is_active')

class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserAchievement
        fields = ('id', 'achievement', 'earned_at', 'progress', 'target', 'is_completed', 'progress_percentage', 'created_at')
        read_only_fields = fields

    def get_progress_percentage(self, obj):
        if obj.target > 0:
            return round(min(100, (obj.progress / obj.target) * 100), 2)
        return 0.0


# --- Course, Lesson, Review, Enrollment Serializers ---
class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'full_name', 'profile_picture', 'about_me') # Add other relevant teacher fields

class LessonSerializer(serializers.ModelSerializer):
     read_time_display = serializers.SerializerMethodField()
     video_duration_display = serializers.SerializerMethodField()

     class Meta:
         model = Lesson
         fields = ('id', 'order', 'title', 'description', 'video_url', 'video_file',
                   'duration_minutes', 'video_duration_display', 'is_free_preview', 'read_time_display')

     def get_read_time_display(self, obj):
         if readtime and obj.description:
             rt = readtime.of_text(obj.description)
             return rt.text
         return _("~1 daqiqa") # Default if no description or readtime library

     def get_video_duration_display(self, obj):
        if obj.duration_minutes:
            if obj.duration_minutes < 60: return f"{obj.duration_minutes} daq"
            else: return f"{obj.duration_minutes // 60} soat {obj.duration_minutes % 60} daq"
        return None

class CourseReviewSerializer(serializers.ModelSerializer):
    user = TeacherSerializer(read_only=True) # Use TeacherSerializer for basic user info
    class Meta:
        model = CourseReview
        fields = ('id', 'user', 'rating', 'comment', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')

class CourseListSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher = TeacherSerializer(read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    price_display = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ('id', 'title', 'subject', 'subject_name', 'thumbnail', 'teacher', 'price', 'price_display',
                  'duration_weeks', 'duration_display', 'difficulty', 'difficulty_display', 'language', 'language_display',
                  'rating', 'enrolled_students_count', 'lessons_count')
        read_only_fields = fields[:1] + fields[2:] # Make subject writable

    def get_price_display(self, obj):
        return _("Bepul") if obj.price <= 0 else f"{obj.price:,.0f} so'm".replace(',', ' ')

    def get_duration_display(self, obj):
        return f"{obj.duration_weeks} hafta" if obj.duration_weeks else _("Noma'lum")

class CourseDetailSerializer(CourseListSerializer):
    lessons = LessonSerializer(many=True, read_only=True, source='lessons.all') # Ensure ordering
    reviews = serializers.SerializerMethodField() # Get limited reviews
    enrollment_status = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + (
            'description', 'requirements', 'what_you_learn', 'has_certificate', 'status', 'status_display',
            'lessons', 'reviews', 'enrollment_status', 'last_updated'
        )
        read_only_fields = ('id', 'subject_name', 'thumbnail', 'teacher', 'price_display', 'duration_display',
                          'difficulty_display', 'language_display', 'rating', 'enrolled_students_count',
                          'lessons_count', 'lessons', 'reviews', 'enrollment_status', 'last_updated', 'status_display')

    def get_reviews(self, obj):
        # Get latest 5 reviews for detail view
        latest_reviews = obj.reviews.all()[:5]
        return CourseReviewSerializer(latest_reviews, many=True, context=self.context).data

    def get_enrollment_status(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            try:
                enrollment = UserCourseEnrollment.objects.get(user=user, course=obj)
                return {
                    'is_enrolled': True,
                    'progress': enrollment.progress,
                    'completed_at': enrollment.completed_at,
                    'enrollment_id': enrollment.id, # Useful for tracking progress
                    'last_accessed_lesson_id': enrollment.last_accessed_lesson_id
                }
            except UserCourseEnrollment.DoesNotExist:
                return {'is_enrolled': False, 'progress': 0.0}
        return {'is_enrolled': False, 'progress': 0.0} # For anonymous users

class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    # user = UserSerializer(read_only=True, fields=('id', 'full_name')) # Not needed if listing for current user

    class Meta:
        model = UserCourseEnrollment
        fields = ('id', 'course', 'enrolled_at', 'progress', 'completed_at', 'last_accessed_lesson')
        read_only_fields = fields

class EnrollActionSerializer(serializers.Serializer):
    # No input needed, just trigger the action
    pass

class LeaveReviewSerializer(serializers.ModelSerializer):
     class Meta:
         model = CourseReview
         fields = ('rating', 'comment')
         extra_kwargs = {
             'rating': {'required': True},
             'comment': {'required': False, 'allow_blank': True},
         }

class UpdateProgressSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField(required=True)


# --- Schedule Serializer ---
class ScheduleItemSerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    type_display = serializers.CharField(source='get_item_type_display', read_only=True)

    class Meta:
        model = ScheduleItem
        fields = ('id', 'day_of_week', 'day_display', 'start_time', 'end_time', 'title',
                  'item_type', 'type_display', 'description')
        read_only_fields = ('id', 'day_display', 'type_display')


# --- Notification Serializer ---
class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    time_since = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ('id', 'message', 'notification_type', 'type_display', 'is_read',
                  'created_at', 'time_since', 'link', 'related_object_id')
        read_only_fields = fields

    def get_time_since(self, obj):
        from django.utils.timesince import timesince
        return timesince(obj.created_at, now=timezone.now()) + _(" oldin")


# --- Admin Panel Serializers ---

class AdminDashboardStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_users_change = serializers.FloatField()
    active_students = serializers.IntegerField()
    active_students_change = serializers.FloatField()
    total_tests_taken = serializers.IntegerField()
    total_tests_taken_change = serializers.FloatField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_revenue_change = serializers.FloatField()

class AdminLastRegisteredUserSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'full_name', 'phone_number', 'date_joined', 'status_display')

    def get_status_display(self, obj):
        # `obj` bu yerda `User` ob'ekti bo'ladi
        if obj.is_blocked:
            return _("Bloklangan")
        return _("Faol") if obj.is_active else _("Nofaol")

class AdminLatestTestSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    class Meta:
        model = Test
        fields = ('id', 'title', 'subject_name', 'created_at', 'status_display')

class AdminLatestPaymentSerializer(PaymentSerializer):
     user_full_name = serializers.CharField(source='user.full_name', read_only=True)
     class Meta(PaymentSerializer.Meta):
         fields = ('id', 'user_full_name', 'amount_display', 'type_display', 'created_at', 'status_display')

class AdminUserListSerializer(serializers.ModelSerializer):
     role_display = serializers.CharField(source='get_role_display', read_only=True)
     status_display = serializers.SerializerMethodField()
     class Meta:
        model = User
        fields = ('id', 'full_name', 'phone_number', 'email', 'date_joined', 'role', 'role_display', 'status_display')
        read_only_fields = fields

     def get_status_display(self, obj):
         if obj.is_blocked: return _("Bloklangan")
         return _("Faol") if obj.is_active else _("Nofaol")

# Use UserSerializer for Admin User Detail

class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'}, label=_("Confirm Password"))

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone_number', 'role', 'password', 'password2',
                  'is_active', 'is_staff', 'is_superuser') # Allow setting permissions
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': True},
            'phone_number': {'required': True},
            'role': {'required': True},
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": _("Parollar mos kelmadi.")})
        try:
            password_validation.validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        # Use create_user to handle password hashing and role setting
        user = User.objects.create_user(**validated_data)
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Admin updating user - can change role, status, etc."""
    class Meta:
        model = User
        fields = ( # Fields admin can modify
            'full_name', 'phone_number', 'email', # Admin can change email too
            'birth_date', 'gender', 'profile_picture',
            'grade', 'region', 'study_place', 'address',
            'target_university', 'target_faculty', 'about_me',
            'role', 'is_active', 'is_blocked', 'is_staff', 'is_superuser'
        )
        extra_kwargs = {
            'email': {'required': False}, # Make fields optional for PATCH
            'full_name': {'required': False},
            'phone_number': {'required': False},
             # ... make others required=False
        }

    def validate_phone_number(self, value):
         # Allow admin to set any number as long as it's unique (excluding current user)
         if value and User.objects.filter(phone_number=value).exclude(pk=self.instance.pk).exists():
             raise serializers.ValidationError(_("Bu telefon raqam boshqa foydalanuvchiga tegishli."))
         return value

    def validate_email(self, value):
         if value and User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
             raise serializers.ValidationError(_("Bu email manzili boshqa foydalanuvchiga tegishli."))
         return value


class AdminTestListSerializer(TestListSerializer):
     status_display = serializers.CharField(source='get_status_display', read_only=True)
     created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, default='')
     class Meta(TestListSerializer.Meta):
        fields = ('id', 'title', 'subject_name', 'question_count', 'difficulty_display',
                  'created_at', 'status', 'status_display', 'created_by_name') # Added status for editing

class AdminTestCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('title', 'subject', 'description', # 'question_count' is read-only or updated internally
                  'difficulty', 'test_type',
                  'price', 'reward_points', 'time_limit', 'status')

class AdminQuestionSerializer(serializers.ModelSerializer):
     class Meta:
         model = Question
         fields = ('id', 'test', 'order', 'question_text', 'difficulty', 'option_a', 'option_b',
                   'option_c', 'option_d', 'correct_answer', 'explanation', 'points')
         read_only_fields = ('id',)
         # 'test' will be set based on the URL in the viewset or passed in data for creation
         extra_kwargs = {'test': {'required': False}}


class AdminMaterialListSerializer(MaterialSerializer):
     status_display = serializers.CharField(source='get_status_display', read_only=True)
     class Meta(MaterialSerializer.Meta):
        fields = ('id', 'title', 'subject_name', 'material_type', 'file_format', 'size_display',
                  'downloads_count', 'status', 'status_display', 'uploaded_at', 'uploaded_by_name') # Added status

class AdminMaterialCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ('title', 'subject', 'description', 'material_type', 'file_format', 'file', 'link',
                  'size_mb', 'status', 'is_free', 'price')
        extra_kwargs = {
            'file': {'required': False, 'allow_null': True},
            'link': {'required': False, 'allow_blank': True, 'allow_null': True},
            'size_mb': {'required': False, 'allow_null': True},
            'description': {'required': False, 'allow_blank': True},
             }

    def validate(self, data):
        file_format = data.get('file_format', self.instance.file_format if self.instance else None)
        file = data.get('file') # Check if file is being uploaded
        link = data.get('link')
        # Get existing file/link if updating and not provided
        instance_file = getattr(self.instance, 'file', None) if self.instance else None
        instance_link = getattr(self.instance, 'link', None) if self.instance else None

        if file_format == 'link' and not link:
             if not instance_link: # Only raise error if creating new or removing existing link
                raise serializers.ValidationError({"link": _("Format 'link' bo'lsa, havola kiritilishi shart.")})
        # Check if file is provided when format is not link
        # This needs careful handling for updates: only require file if it's a new instance or if file_format changes from 'link'
        elif file_format != 'link' and file is None: # 'file is None' means no new file uploaded
            if not self.instance or not instance_file: # Creating new or no existing file
                 raise serializers.ValidationError({"file": _("Format 'link' bo'lmasa, fayl yuklanishi shart.")})
            # If format changes from 'link' to something else, file is needed
            elif self.instance and instance_link and not instance_file:
                 raise serializers.ValidationError({"file": _("Format 'link' dan o'zgartirilsa, fayl yuklanishi shart.")})
        # If format is link, clear the file field
        elif file_format == 'link':
             data['file'] = None

        is_free = data.get('is_free', getattr(self.instance, 'is_free', True) if self.instance else True)
        price = data.get('price', getattr(self.instance, 'price', 0) if self.instance else 0)

        if is_free:
            data['price'] = 0.00
        elif price <= 0:
             raise serializers.ValidationError({"price": _("Pullik material uchun narx musbat bo'lishi kerak.")})

        return data


# --- Admin Statistics Serializers ---
class BaseStatSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    change_percentage = serializers.FloatField(allow_null=True) # Allow null if no previous data

class DetailedStatSerializer(serializers.Serializer):
    value = serializers.IntegerField()
    change_percentage = serializers.FloatField(allow_null=True)
    target = serializers.IntegerField(allow_null=True) # Optional target

class GraphDataPointSerializer(serializers.Serializer):
    date = serializers.DateField() # Or DateTimeField
    value = serializers.IntegerField()

# class AdminDashboardStatsSerializer(serializers.Serializer):
#     total_users = DetailedStatSerializer()
#     active_students = DetailedStatSerializer()
#     total_tests = DetailedStatSerializer() # Or tests taken
#     total_revenue = DetailedStatSerializer()

class AdminUserStatisticsSerializer(serializers.Serializer):
     users_graph = GraphDataPointSerializer(many=True)
     new_users = DetailedStatSerializer()
     active_users = DetailedStatSerializer()
     average_activity = serializers.CharField() # e.g., "24 min"

class AdminTestStatisticsSerializer(serializers.Serializer):
     tests_graph = GraphDataPointSerializer(many=True)
     total_tests = DetailedStatSerializer()
     tests_taken = DetailedStatSerializer()
     average_score = DetailedStatSerializer() # Value as percentage

class AdminPaymentStatisticsSerializer(serializers.Serializer):
     payments_graph = GraphDataPointSerializer(many=True)
     total_income = DetailedStatSerializer()
     total_expenses = DetailedStatSerializer() # If tracking expenses
     average_payment = DetailedStatSerializer()

# Serializer for adding balance by admin
import decimal

class AdminAddBalanceSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=decimal.Decimal('0.01'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

# Serializers for Admin CRUD operations on other models (University, Achievement, Course, etc.)
# Use existing serializers or create specific Admin versions if needed.
class AdminUniversitySerializer(UniversitySerializer): # Can inherit or be specific
     class Meta(UniversitySerializer.Meta):
         pass # Keep all fields for admin

class AdminAchievementSerializer(AchievementSerializer):
     class Meta(AchievementSerializer.Meta):
         pass

class AdminCourseSerializer(CourseDetailSerializer): # Use detail for admin view/update
    class Meta(CourseDetailSerializer.Meta):
        read_only_fields = ('id', 'subject_name', 'teacher', 'price_display', 'duration_display', # Keep teacher read-only or use ID
                          'difficulty_display', 'language_display', 'rating', 'enrolled_students_count',
                          'lessons_count', 'lessons', 'reviews', 'enrollment_status', 'last_updated', 'status_display')
        # Allow admin to edit most fields
        # Teacher might be set via ID

class AdminLessonSerializer(LessonSerializer):
     class Meta(LessonSerializer.Meta):
        pass # Allow editing all fields


class AdminDashboardLatestListsSerializer(serializers.Serializer):
    latest_users = serializers.ListField(child=serializers.DictField(), read_only=True)
    latest_tests = serializers.ListField(child=serializers.DictField(), read_only=True)
    latest_payments = serializers.ListField(child=serializers.DictField(), read_only=True)




class ValueChangeTargetSerializer(serializers.Serializer): # Yordamchi serializer
    value = serializers.IntegerField()
    change_percentage = serializers.FloatField()
    target = serializers.IntegerField()


