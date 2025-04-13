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

# --- Helper Serializers ---
class ValueChangeTargetIntSerializer(serializers.Serializer): # <<< NOM O'ZGARTIRILDI
    """Statistika kartasi uchun: Qiymat (int), Foiz o'zgarishi, Maqsad (int)."""
    value = serializers.IntegerField()
    change_percentage = serializers.FloatField(allow_null=True)
    target = serializers.IntegerField()

class ValueChangeTargetDecimalSerializer(serializers.Serializer):
    """Statistika kartasi uchun: Qiymat (Decimal), Foiz o'zgarishi, Maqsad (Decimal/Int)."""
    value = serializers.DecimalField(max_digits=15, decimal_places=2)
    change_percentage = serializers.FloatField(allow_null=True)
    target = serializers.DecimalField(max_digits=15, decimal_places=2) # Maqsad ham Decimal bo'lishi mumkin

class GraphDataPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    value = serializers.IntegerField() # Yoki DecimalField

class DetailedStatSerializer(serializers.Serializer):
    """Umumiy statistika uchun: qiymat (int/float/str) va o'zgarish foizi."""
    value = serializers.IntegerField() # Default, lekin boshqa serializerlarda override qilinishi mumkin
    change_percentage = serializers.FloatField(allow_null=True)

class DetailedDecimalStatSerializer(DetailedStatSerializer):
    """Statistika uchun, qiymat Decimal bo'lganda."""
    value = serializers.DecimalField(max_digits=15, decimal_places=2)

class DetailedCharStatSerializer(DetailedStatSerializer):
    """Statistika uchun, qiymat matn bo'lganda (masalan, vaqt)."""
    value = serializers.CharField()


# --- Authentication Serializers ---

class SignupSerializer(serializers.ModelSerializer):
    # Frontend nomlari bilan fieldlarni e'lon qilamiz va `source` orqali bog'laymiz
    email = serializers.EmailField(required=True)
    fullName = serializers.CharField(source='full_name', required=True, label=_("Full Name"))
    phone = serializers.CharField(source='phone_number', required=True, label=_("Phone Number"))
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    agreeToTerms = serializers.BooleanField(source='agreetoterms', required=True, write_only=True, label=_("Agree to Terms"))

    # Ixtiyoriy maydonlar (frontend nomlari bilan)
    birthDate = serializers.DateField(source='birth_date', required=False, allow_null=True, label=_("Birth Date"))
    gender = serializers.ChoiceField(choices=User.GENDER_CHOICES, required=False, allow_null=True)
    grade = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    region = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    school = serializers.CharField(source='study_place', required=False, allow_null=True, allow_blank=True, label=_("School/Study Place"))

    class Meta:
        model = User
        fields = (
            'email', 'fullName', 'phone', 'password', 'agreeToTerms',
            'birthDate', 'gender', 'grade', 'region', 'school'
        )
        extra_kwargs = {
            'password': {'write_only': True},
        }

    # --- Validationlar ---
    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("Bu email manzili allaqachon ro'yxatdan o'tgan."))
        return value

    def validate_phone(self, value): # Frontend nomi 'phone'
        if not value:
             raise serializers.ValidationError(_("Telefon raqam kiritilishi shart."))
        if not value.startswith('+998') or len(value) != 13 or not value[1:].isdigit():
             raise serializers.ValidationError(_("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak."))
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(_("Bu telefon raqam allaqachon ro'yxatdan o'tgan."))
        return value

    def validate(self, data):
        if not data.get('agreetoterms'): # Model field nomi bilan tekshiramiz
            raise serializers.ValidationError({"agreeToTerms": _("Ro'yxatdan o'tish uchun shartlarga rozilik bildiring.")})
        try:
            password_validation.validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return data

    def create(self, validated_data):
        validated_data['role'] = 'student'
        user = User.objects.create_user(**validated_data)
        # UserManager.create_user avtomatik rating va settings yaratishi kerak
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, label=_("Email"))
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label=_("Password")
    )
    # Read-only fields for the response
    token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True) # Nested user info

    # Internal field to hold user instance after validation
    _user_instance = None

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        request = self.context.get('request')

        user = authenticate(request=request, email=email, password=password)

        if user is None:
            raise serializers.ValidationError(_("Email yoki parol noto'g'ri."), code='authorization')
        if not user.is_active:
            raise serializers.ValidationError(_("Foydalanuvchi akkaunti faol emas."), code='authorization')
        if user.is_blocked:
            raise serializers.ValidationError(_("Foydalanuvchi akkaunti bloklangan."), code='authorization')

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        data['refresh_token'] = str(refresh)
        data['token'] = str(refresh.access_token)
        self._user_instance = user  # Store user instance for get_user method

        return data

    def get_user(self, obj):
        # Retrieve the stored user instance
        user_instance = self._user_instance
        if user_instance:
            # Return basic user info needed after login
            return {
                'id': user_instance.id,
                'full_name': user_instance.full_name,
                'email': user_instance.email,
                'role': user_instance.role,
                'role_display': user_instance.get_role_display(),
                'profile_picture': self.context['request'].build_absolute_uri(user_instance.profile_picture.url) if user_instance.profile_picture else None, # Include profile picture URL
            }
        return None


# --- User Profile & Settings Serializers ---

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        exclude = ('user',)

class UserRatingSerializer(serializers.ModelSerializer):
    level_progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserRating
        exclude = ('user',)
        read_only_fields = ('total_score', 'rank', 'level', 'points_to_next_level', 'current_level_points', 'last_updated')

    def get_level_progress_percentage(self, obj):
         if obj.points_to_next_level is None: # Max level
             return 100.0
         current_level_threshold = obj.LEVEL_THRESHOLDS.get(obj.level, 0)
         total_points_for_level = obj.points_to_next_level - current_level_threshold
         if total_points_for_level > 0:
             points_earned_in_level = obj.total_score - current_level_threshold
             percentage = (points_earned_in_level / total_points_for_level) * 100
             return round(max(0, min(percentage, 100)), 2)
         return 0.0

class UserSerializer(serializers.ModelSerializer):
    """For retrieving user details (profile view, admin detail view)."""
    settings = UserSettingsSerializer(read_only=True)
    rating = UserRatingSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True, allow_null=True)
    balance_display = serializers.CharField(source='get_balance_display', read_only=True)
    profile_picture = serializers.ImageField(max_length=None, use_url=True, read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'full_name', 'phone_number', 'role', 'role_display',
            'profile_picture', 'balance', 'balance_display', 'date_joined', 'is_active', 'is_blocked',
            'birth_date', 'gender', 'gender_display', 'grade', 'region', 'study_place',
            'address', 'target_university', 'target_faculty', 'about_me',
            'settings', 'rating'
        )
        read_only_fields = ('id', 'email', 'role', 'role_display', 'balance', 'balance_display', 'date_joined', 'is_active', 'is_blocked', 'settings', 'rating', 'profile_picture')

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """For user updating their own profile."""
    profile_picture = serializers.ImageField(max_length=None, use_url=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'full_name', 'phone_number', 'birth_date', 'gender', 'profile_picture',
            'grade', 'region', 'study_place', 'address',
            'target_university', 'target_faculty', 'about_me'
        )
        extra_kwargs = {
            # All fields are optional for PATCH requests
            'profile_picture': {'required': False, 'allow_null': True},
            'full_name': {'required': False},
            'phone_number': {'required': False},
            'birth_date': {'required': False, 'allow_null': True},
            'gender': {'required': False, 'allow_null': True},
            'grade': {'required': False, 'allow_blank': True, 'allow_null': True},
            'region': {'required': False, 'allow_blank': True, 'allow_null': True},
            'study_place': {'required': False, 'allow_blank': True, 'allow_null': True},
            'address': {'required': False, 'allow_blank': True, 'allow_null': True},
            'target_university': {'required': False, 'allow_blank': True, 'allow_null': True},
            'target_faculty': {'required': False, 'allow_blank': True, 'allow_null': True},
            'about_me': {'required': False, 'allow_blank': True, 'allow_null': True},
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
    currentPassword = serializers.CharField(source='old_password', required=True, write_only=True, style={'input_type': 'password'})
    newPassword = serializers.CharField(source='new_password', required=True, write_only=True, style={'input_type': 'password'})
    confirmPassword = serializers.CharField(source='new_password2', required=True, write_only=True, style={'input_type': 'password'}, label=_("Confirm New Password"))

    def validate_currentPassword(self, value): # Frontend nomi bilan
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Joriy parol noto'g'ri."))
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password2']: # Model nomlari bilan ichki tekshiruv
            raise serializers.ValidationError({"newPassword": _("Yangi parollar mos kelmadi.")}) # Frontend nomiga error
        try:
            password_validation.validate_password(data['new_password'], user=self.context['request'].user)
        except Exception as e:
            raise serializers.ValidationError({"newPassword": list(e.messages)}) # Frontend nomiga error
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        # Ichki nom 'new_password' bilan saqlash
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class ProfileSettingsUpdateSerializer(serializers.ModelSerializer):
    """For updating user settings via profile."""
    class Meta:
        model = UserSettings
        # User Settings modelidagi barcha tahrirlanadigan maydonlar
        fields = (
            'language', 'theme', 'autoplay_videos', 'sound_effects', 'high_contrast',
            'notify_email', 'notify_sms', 'notify_push',
            'notify_test_updates', 'notify_course_updates', 'notify_payments', 'notify_reminders',
            'two_factor_enabled', # two_factor_method qo'shilishi mumkin
            'weekly_reports', 'personalized_recommendations'
        )


# --- Subject Serializer ---
class SubjectSerializer(serializers.ModelSerializer):
    icon = serializers.ImageField(max_length=None, use_url=True, read_only=True)
    class Meta:
        model = Subject
        fields = ('id', 'name', 'icon')


# --- Test & Question Serializers ---
class QuestionSerializer(serializers.ModelSerializer):
    """For displaying questions during a test (without correct answer)."""
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'order', 'question_text', 'difficulty', 'difficulty_display', 'points',
                  'option_a', 'option_b', 'option_c', 'option_d')

class QuestionResultSerializer(QuestionSerializer):
    """For displaying question details in results (with correct answer and explanation)."""
    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + ('correct_answer', 'explanation',)


class TestListSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True) # Nested Subject info
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    type_display = serializers.CharField(source='get_test_type_display', read_only=True)
    price_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Test
        fields = ('id', 'title', 'subject', 'test_type', 'type_display', 'question_count',
                  'difficulty', 'difficulty_display', 'price', 'price_display', 'time_limit',
                  'reward_points',  'status', 'status_display', 'created_at') # 'subject_name', 'subject_icon' olib tashlandi, 'subject' ichida
        read_only_fields = ('id', 'subject', 'type_display', 'price_display', 'question_count',
                            'difficulty_display', 'status_display', 'created_at', 'reward_points', 'time_limit')

    def get_price_display(self, obj):
        if obj.test_type == 'free' or obj.price <= 0:
            return _("Bepul")
        return f"{int(obj.price):,} so'm".replace(',', ' ')


class TestDetailSerializer(TestListSerializer):
    questions = QuestionSerializer(many=True, read_only=True, source='questions.all') # questions.all() tartib uchun
    # TestListSerializerdan meros oladi, qo'shimcha maydonlar:
    class Meta(TestListSerializer.Meta):
        fields = TestListSerializer.Meta.fields + ('description', 'questions')
        read_only_fields = TestListSerializer.Meta.read_only_fields + ('description', 'questions')


class SubmitAnswerSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.ChoiceField(choices=Question.ANSWER_CHOICES, allow_blank=True),
        required=True
    )

class UserAnswerSerializer(serializers.ModelSerializer):
    question = QuestionResultSerializer(read_only=True) # Natijada savol ma'lumotlari

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
            minutes, seconds = divmod(total_seconds, 60)
            return f"{minutes:02d}:{seconds:02d}"
        return None

    def get_score_display(self, obj):
        return f"{obj.score} / {obj.total_questions}"


# --- Material Serializers ---
class MaterialSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    format_display = serializers.CharField(source='get_file_format_display', read_only=True)
    size_display = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True, default='')
    file = serializers.FileField(max_length=None, use_url=True, read_only=True) # Faqat URL qaytarish

    class Meta:
        model = Material
        fields = ('id', 'title', 'subject', 'description', 'material_type', 'type_display',
                  'file_format', 'format_display', 'file', 'link', 'size_mb', 'size_display',
                  'downloads_count', 'status', 'uploaded_at', 'uploaded_by_name', 'is_free', 'price', 'price_display', 'download_url')
        read_only_fields = ('id', 'subject', 'type_display', 'format_display', 'size_display', 'file',
                          'downloads_count', 'uploaded_at', 'uploaded_by_name', 'download_url', 'price_display')

    def get_size_display(self, obj):
        if obj.size_mb is not None:
            return f"{obj.size_mb:.1f} MB" if obj.size_mb >= 1 else f"{obj.size_mb * 1024:.0f} KB"
        elif obj.file:
             try: return f"{obj.file.size / (1024*1024):.1f} MB" if obj.file.size >= 1024*1024 else f"{obj.file.size / 1024:.0f} KB"
             except Exception: return "-"
        return "-"

    def get_download_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.link

    def get_price_display(self, obj):
        return _("Bepul") if obj.is_free or obj.price <= 0 else f"{int(obj.price):,} so'm".replace(',', ' ')


# --- Payment Serializers ---
class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    method_display = serializers.CharField(source='get_payment_method_display', read_only=True, allow_null=True)
    amount_display = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ('id', 'user', 'user_email', 'amount', 'amount_display', 'payment_type', 'type_display',
                  'description', 'status', 'status_display', 'payment_method', 'method_display',
                  'transaction_id', 'created_at', 'test', 'material', 'mock_test', 'course')
        read_only_fields = fields # Barchasi o'qish uchun

    def get_amount_display(self, obj):
        # Amount manfiy bo'lishi mumkin (chiqimlar uchun)
        sign = "+" if obj.amount >= 0 else ""
        return f"{sign}{int(obj.amount):,} so'm".replace(',', ' ')


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
        return f"{int(obj.price):,} so'm".replace(',', ' ') if obj.price > 0 else _("Bepul")

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
    file = serializers.FileField(max_length=None, use_url=True, read_only=True)

    class Meta:
        model = MockTestMaterial
        fields = ('id', 'title', 'mock_test_type', 'type_display', 'language', 'language_display',
                  'description', 'file', 'link', 'material_format', 'format_display', 'is_free', 'download_url')
        read_only_fields = ('id', 'type_display', 'language_display', 'format_display', 'download_url', 'file')

    def get_download_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.link

# --- University Serializer ---
class UniversitySerializer(serializers.ModelSerializer):
    region_display = serializers.CharField(source='get_region_display', read_only=True)
    logo = serializers.ImageField(max_length=None, use_url=True, read_only=True)
    class Meta:
        model = University
        fields = '__all__'


# --- Achievement Serializers ---
class AchievementSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    # icon maydoni CharField bo'lgani uchun ImageField kerak emas
    class Meta:
        model = Achievement
        fields = ('id', 'name', 'description', 'category', 'category_display', 'points_reward', 'icon', 'is_active')

class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserAchievement
        fields = ('id', 'achievement', 'earned_at', 'progress', 'target', 'is_completed', 'progress_percentage', 'created_at') # created_at UserAchievement modeli uchun
        read_only_fields = fields

    def get_progress_percentage(self, obj):
        if obj.target is not None and obj.target > 0 and obj.progress is not None:
            return round(min(100, (obj.progress / obj.target) * 100), 1)
        return 100.0 if obj.is_completed else 0.0


# --- Course, Lesson, Review, Enrollment Serializers ---
class TeacherSerializer(serializers.ModelSerializer):
    """O'qituvchi haqida qisqa ma'lumot (nested uchun)."""
    profile_picture = serializers.ImageField(max_length=None, use_url=True, read_only=True)
    class Meta:
        model = User
        fields = ('id', 'full_name', 'profile_picture', 'about_me')

class LessonSerializer(serializers.ModelSerializer):
     """Kurs darslari uchun."""
     read_time_display = serializers.SerializerMethodField()
     video_duration_display = serializers.SerializerMethodField()
     video_file = serializers.FileField(max_length=None, use_url=True, read_only=True)

     class Meta:
         model = Lesson
         fields = ('id', 'order', 'title', 'description', 'video_url', 'video_file',
                   'duration_minutes', 'video_duration_display', 'is_free_preview', 'read_time_display')

     def get_read_time_display(self, obj):
         if readtime and obj.description: return readtime.of_text(obj.description).text
         return _("~1 daqiqa")

     def get_video_duration_display(self, obj):
        if obj.duration_minutes:
            mins = obj.duration_minutes
            return f"{mins // 60} soat {mins % 60} daq" if mins >= 60 else f"{mins} daq"
        return None

class CourseReviewSerializer(serializers.ModelSerializer):
    user = TeacherSerializer(read_only=True) # User ma'lumoti
    class Meta:
        model = CourseReview
        fields = ('id', 'user', 'rating', 'comment', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')

class CourseListSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    teacher = TeacherSerializer(read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    price_display = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    thumbnail = serializers.ImageField(max_length=None, use_url=True, read_only=True)
    # Student uchun progressni ham qo'shamiz (agar login qilgan bo'lsa)
    user_progress = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ('id', 'title', 'subject', 'thumbnail', 'teacher', 'price', 'price_display',
                  'duration_weeks', 'duration_display', 'difficulty', 'difficulty_display', 'language', 'language_display',
                  'rating', 'enrolled_students_count', 'lessons_count', 'user_progress') # user_progress qo'shildi
        read_only_fields = fields

    def get_price_display(self, obj):
        return _("Bepul") if obj.price <= 0 else f"{int(obj.price):,} so'm".replace(',', ' ')

    def get_duration_display(self, obj):
        return f"{obj.duration_weeks} hafta" if obj.duration_weeks else _("Noma'lum")

    def get_user_progress(self, obj):
         # Contextdan requestni olish
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Foydalanuvchining ushbu kursdagi progressini olish
            enrollment = UserCourseEnrollment.objects.filter(user=request.user, course=obj).first()
            return enrollment.progress if enrollment else 0.0
        return None # Agar login qilmagan bo'lsa


class CourseDetailSerializer(CourseListSerializer):
    lessons = LessonSerializer(many=True, read_only=True, source='get_ordered_lessons') # Model methodidan olish
    reviews = serializers.SerializerMethodField() # Oxirgi bir nechtasini olish
    enrollment_status = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta(CourseListSerializer.Meta):
        # user_progress ni olib tashlaymiz, chunki enrollment_status ichida bor
        fields = [f for f in CourseListSerializer.Meta.fields if f != 'user_progress'] + [
            'description', 'requirements', 'what_you_learn', 'has_certificate', 'status', 'status_display',
            'lessons', 'reviews', 'enrollment_status', 'last_updated'
        ]
        read_only_fields = fields # Detail viewda hamma narsa read-only

    def get_reviews(self, obj):
        latest_reviews = obj.reviews.all()[:5] # Oxirgi 5 ta sharh
        return CourseReviewSerializer(latest_reviews, many=True, context=self.context).data

    def get_enrollment_status(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            try:
                enrollment = UserCourseEnrollment.objects.select_related('last_accessed_lesson').get(user=user, course=obj)
                return {
                    'is_enrolled': True,
                    'progress': enrollment.progress,
                    'completed_at': enrollment.completed_at,
                    'enrollment_id': enrollment.id,
                    'last_accessed_lesson': LessonSerializer(enrollment.last_accessed_lesson, context=self.context).data if enrollment.last_accessed_lesson else None
                }
            except UserCourseEnrollment.DoesNotExist:
                pass
        return {'is_enrolled': False, 'progress': 0.0, 'completed_at': None, 'enrollment_id': None, 'last_accessed_lesson': None}

class CourseEnrollmentSerializer(serializers.ModelSerializer):
    """Foydalanuvchining kurs yozuvlari uchun."""
    course = CourseListSerializer(read_only=True) # Kurs haqida qisqa ma'lumot
    last_accessed_lesson = LessonSerializer(read_only=True) # Oxirgi kirilgan dars

    class Meta:
        model = UserCourseEnrollment
        fields = ('id', 'course', 'enrolled_at', 'progress', 'completed_at', 'last_accessed_lesson')
        read_only_fields = fields

class EnrollActionSerializer(serializers.Serializer):
    pass # No fields needed, just triggers action

class LeaveReviewSerializer(serializers.ModelSerializer):
     class Meta:
         model = CourseReview
         fields = ('rating', 'comment')
         extra_kwargs = {'rating': {'required': True}, 'comment': {'required': False, 'allow_blank': True}}

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
    # related_object = serializers.SerializerMethodField() # Yoki alohida serializerlar

    class Meta:
        model = Notification
        fields = ('id', 'message', 'notification_type', 'type_display', 'is_read',
                  'created_at', 'time_since', 'link', 'related_object_id')
        read_only_fields = fields

    def get_time_since(self, obj):
        from django.utils.timesince import timesince
        now_aware = timezone.now()
        if timezone.is_naive(obj.created_at): # Agar naive bo'lsa
             created_at_aware = timezone.make_aware(obj.created_at, timezone.get_default_timezone())
        else:
             created_at_aware = obj.created_at
        return timesince(created_at_aware, now=now_aware) + _(" oldin")

    # def get_related_object(self, obj): # Murakkabroq, lekin foydali
    #     if obj.notification_type == 'test_result' and obj.related_object_id:
    #         try: return UserTestResultSerializer(UserTestResult.objects.get(pk=obj.related_object_id)).data
    #         except UserTestResult.DoesNotExist: return None
    #     # ... boshqa turlar uchun ...
    #     return None


# ==============================================
#               ADMIN PANEL SERIALIZERS
# ==============================================

# --- Admin Dashboard Serializers ---

class AdminDashboardStatsSerializer(serializers.Serializer):
    """Admin paneli bosh sahifasidagi katta kartalar uchun."""
    total_users = ValueChangeTargetIntSerializer(read_only=True)
    active_students = ValueChangeTargetIntSerializer(read_only=True)
    # total_tests maydoni qo'shilgan edi avvalgi kodda, uni ham ValueChangeTargetIntSerializer qilamiz
    total_tests_taken = ValueChangeTargetIntSerializer(read_only=True) # Yoki total_tests
    total_revenue = ValueChangeTargetDecimalSerializer(read_only=True) # Decimal uchun alohida serializer

class AdminLastRegisteredUserSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('id', 'full_name', 'phone_number', 'date_joined', 'status_display')
    def get_status_display(self, obj):
        return _("Bloklangan") if obj.is_blocked else (_("Faol") if obj.is_active else _("Nofaol"))

class AdminLatestTestSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    class Meta:
        model = Test
        fields = ('id', 'title', 'subject_name', 'created_at', 'status_display')

class AdminLatestPaymentSerializer(PaymentSerializer): # Mavjudidan foydalanamiz
     user_full_name = serializers.CharField(source='user.full_name', read_only=True)
     class Meta(PaymentSerializer.Meta):
         fields = ('id', 'user_full_name', 'amount_display', 'type_display', 'created_at', 'status_display')

class AdminDashboardLatestListsSerializer(serializers.Serializer):
    """Admin paneli bosh sahifasidagi oxirgi ro'yxatlar uchun."""
    latest_users = AdminLastRegisteredUserSerializer(many=True, read_only=True)
    latest_tests = AdminLatestTestSerializer(many=True, read_only=True)
    latest_payments = AdminLatestPaymentSerializer(many=True, read_only=True)


# --- Admin CRUD Serializers ---

class AdminUserListSerializer(serializers.ModelSerializer):
     role_display = serializers.CharField(source='get_role_display', read_only=True)
     status_display = serializers.SerializerMethodField()
     class Meta:
        model = User
        fields = ('id', 'full_name', 'phone_number', 'email', 'date_joined', 'role', 'role_display', 'status_display') # role ni ham qo'shdim
        read_only_fields = fields
     def get_status_display(self, obj):
         return _("Bloklangan") if obj.is_blocked else (_("Faol") if obj.is_active else _("Nofaol"))

class AdminUserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    full_name = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    is_active = serializers.BooleanField(required=False, default=True)
    is_staff = serializers.BooleanField(required=False, default=False)
    is_superuser = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = (
            'email', 'full_name', 'phone_number', 'role',
            'password', 'is_active', 'is_staff', 'is_superuser'
        ) # is_blocked bu yerda yo'q

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(_("Bu telefon raqam allaqachon mavjud."))
        if not value.startswith('+998') or len(value) != 13 or not value[1:].isdigit():
             raise serializers.ValidationError(_("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak."))
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("Bu email manzili allaqachon mavjud."))
        return value

    def validate(self, data):
        try: password_validation.validate_password(data['password'])
        except Exception as e: raise serializers.ValidationError({"password": list(e.messages)})
        return data

    def create(self, validated_data):
        # is_blocked avtomatik False bo'ladi
        user = User.objects.create_user(**validated_data)
        return user

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'full_name', 'phone_number',
            'birth_date', 'gender', 'profile_picture',
            'grade', 'region', 'study_place', 'address',
            'target_university', 'target_faculty', 'about_me',
            'role', 'balance', # Admin balansni o'zgartira olsin
            'is_active', 'is_blocked', 'is_staff', 'is_superuser'
        )
        extra_kwargs = { field: {'required': False} for field in fields } # All optional for PATCH
        extra_kwargs['profile_picture'] = {'required': False, 'allow_null': True}
        extra_kwargs['birth_date'] = {'required': False, 'allow_null': True}
        extra_kwargs['gender'] = {'required': False, 'allow_null': True}
        # ... other fields allowing null/blank should be specified ...

    # --- Validations for email and phone (ensure uniqueness excluding self) ---
    def validate_phone_number(self, value):
         if value and User.objects.filter(phone_number=value).exclude(pk=self.instance.pk).exists():
             raise serializers.ValidationError(_("Bu telefon raqam boshqa foydalanuvchiga tegishli."))
         if value and (not value.startswith('+998') or len(value) != 13 or not value[1:].isdigit()):
              raise serializers.ValidationError(_("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak."))
         return value

    def validate_email(self, value):
         if value and User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
             raise serializers.ValidationError(_("Bu email manzili boshqa foydalanuvchiga tegishli."))
         return value

    def validate_balance(self, value):
        # Balans manfiy bo'lishi mumkin emas (agar shart shunday bo'lsa)
        if value < 0:
            raise serializers.ValidationError(_("Balans manfiy bo'lishi mumkin emas."))
        return value


class AdminTestListSerializer(TestListSerializer):
     status_display = serializers.CharField(source='get_status_display', read_only=True)
     created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, default='')
     subject = SubjectSerializer(read_only=True) # Show nested subject

     class Meta(TestListSerializer.Meta):
        fields = ('id', 'title', 'subject', 'question_count', 'difficulty_display', # subject_name/icon o'rniga subject
                  'created_at', 'status', 'status_display', 'created_by_name')
        read_only_fields = ('id', 'subject', 'question_count', 'difficulty_display', # status ni tahrirlash mumkin
                          'created_at', 'status_display', 'created_by_name')


class AdminTestCreateUpdateSerializer(serializers.ModelSerializer):
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())

    class Meta:
        model = Test
        # question_count ni olib tashlaymiz, u savollar qo'shilganda/o'chirilganda yangilanadi
        fields = ('title', 'subject', 'description', 'difficulty', 'test_type',
                  'price', 'reward_points', 'time_limit', 'status')
        extra_kwargs = {
             'description': {'required': False, 'allow_blank': True},
             'price': {'required': False, 'default': 0},
             'reward_points': {'required': False, 'default': 0},
             'time_limit': {'required': False, 'default': 60},
        }

    def validate_price(self, value):
        if value < 0: raise serializers.ValidationError(_("Narx manfiy bo'lishi mumkin emas."))
        return value

    def validate(self, data):
        # `instance` mavjud bo'lsa (update) yoki yo'q bo'lsa (create) type va price ni olish
        test_type = data.get('test_type', getattr(self.instance, 'test_type', None))
        price = data.get('price', getattr(self.instance, 'price', None))

        # Agar price kiritilmagan bo'lsa, default 0 deb olamiz (yoki instance dagi qiymat)
        if price is None: price = 0

        if test_type == 'free':
            data['price'] = decimal.Decimal('0.00')
        elif price <= 0 and test_type == 'premium':
             raise serializers.ValidationError({'price': _("Premium test uchun narx 0 dan katta bo'lishi kerak.")})
        # Agar price kiritilgan bo'lsa, uni Decimal ga o'tkazish
        if 'price' in data: data['price'] = decimal.Decimal(data['price'])

        return data

class AdminQuestionSerializer(serializers.ModelSerializer):
     difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
     correct_answer_display = serializers.CharField(source='get_correct_answer_display', read_only=True)

     class Meta:
         model = Question
         fields = ('id', 'test', 'order', 'question_text', 'difficulty', 'difficulty_display', 'option_a', 'option_b',
                   'option_c', 'option_d', 'correct_answer', 'correct_answer_display', 'explanation', 'points')
         read_only_fields = ('id', 'difficulty_display', 'correct_answer_display')
         # 'test' maydonini faqat yaratishda (data orqali) yoki update da (instance dan) o'qish uchun qoldiramiz
         extra_kwargs = {'test': {'required': False, 'read_only': True}}


class AdminMaterialListSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    format_display = serializers.CharField(source='get_file_format_display', read_only=True)
    size_display = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True, default='')
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = ('id', 'title', 'subject', 'material_type', 'type_display', 'file_format', 'format_display',
                  'size_display', 'downloads_count', 'status', 'status_display', 'uploaded_at', 'uploaded_by_name', 'file_url')
        read_only_fields = ('id', 'subject', 'type_display', 'format_display', 'size_display',
                          'downloads_count', 'uploaded_at', 'uploaded_by_name', 'status_display', 'file_url')

    def get_size_display(self, obj):
        # Avvalgi kod bilan bir xil
        if obj.size_mb is not None: return f"{obj.size_mb:.1f} MB" if obj.size_mb >= 1 else f"{obj.size_mb * 1024:.0f} KB"
        elif obj.file:
             try: return f"{obj.file.size / (1024*1024):.1f} MB" if obj.file.size >= 1024*1024 else f"{obj.file.size / 1024:.0f} KB"
             except Exception: return "-"
        return "-"

    def get_file_url(self, obj):
         request = self.context.get('request')
         if obj.file and request:
             return request.build_absolute_uri(obj.file.url)
         return obj.link # Agar fayl yo'q bo'lsa link

class AdminMaterialCreateUpdateSerializer(serializers.ModelSerializer):
    # file maydonini alohida handle qilamiz
    file = serializers.FileField(required=False, allow_null=True, max_length=None, use_url=True)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())

    class Meta:
        model = Material
        fields = ('title', 'subject', 'description', 'material_type', 'file_format', 'file', 'link',
                  'size_mb', 'status', 'is_free', 'price')
        extra_kwargs = {
            # file required=False qilindi
            'link': {'required': False, 'allow_blank': True, 'allow_null': True},
            'size_mb': {'required': False, 'allow_null': True}, # Avto hisoblash yaxshiroq
            'description': {'required': False, 'allow_blank': True},
            'is_free': {'required': False},
            'price': {'required': False},
             }

    def validate(self, data):
        file_format = data.get('file_format', getattr(self.instance, 'file_format', None))
        file = data.get('file') # Yuklanayotgan fayl
        link = data.get('link')
        instance_file = getattr(self.instance, 'file', None) if self.instance else None

        if file_format == 'link':
            if not link: raise serializers.ValidationError({"link": _("Format 'link' bo'lsa, havola kiritilishi shart.")})
            data['file'] = None # Faylni tozalash
        elif file is None and not instance_file: # Agar yangi yoki eski fayl yo'q bo'lsa
             if not self.instance: # Faqat yaratishda xatolik beramiz
                raise serializers.ValidationError({"file": _("Fayl yuklanishi shart (format 'link' emas).")})
        elif file is not None: # Agar yangi fayl yuklansa
             data['link'] = None # Linkni tozalash
             # Hajmni avto hisoblash
             try: data['size_mb'] = round(file.size / (1024 * 1024), 2)
             except: data['size_mb'] = None # Hajmni olib bo'lmadi

        is_free = data.get('is_free', getattr(self.instance, 'is_free', True))
        price = data.get('price', getattr(self.instance, 'price', None))
        if price is None: price = decimal.Decimal('0.00')
        else: price = decimal.Decimal(price) # Decimal ga o'tkazish

        if is_free: data['price'] = decimal.Decimal('0.00')
        elif price <= 0: raise serializers.ValidationError({"price": _("Pullik material uchun narx musbat bo'lishi kerak.")})
        data['price'] = price # Validatsiyadan o'tgan narxni qaytarish

        return data

# Admin Payment (ReadOnly) uses PaymentSerializer

# --- Admin Statistics Serializers ---
class AdminUserStatisticsDataSerializer(serializers.Serializer):
    users_graph = GraphDataPointSerializer(many=True, read_only=True)
    new_users = DetailedStatSerializer(read_only=True)
    active_users = DetailedStatSerializer(read_only=True)
    average_activity = DetailedCharStatSerializer(read_only=True) # Value endi CharField

class AdminTestStatisticsDataSerializer(serializers.Serializer):
    tests_graph = GraphDataPointSerializer(many=True, read_only=True)
    total_tests = DetailedStatSerializer(read_only=True)
    tests_taken = DetailedStatSerializer(read_only=True)
    average_score = DetailedStatSerializer(read_only=True) # Value default Int (yoki Float)

class AdminPaymentStatisticsDataSerializer(serializers.Serializer):
    payments_graph = GraphDataPointSerializer(many=True, read_only=True)
    # DetailedDecimalStatSerializer ISHLATILADI:
    total_income = DetailedDecimalStatSerializer(read_only=True)
    total_expenses = DetailedDecimalStatSerializer(read_only=True)
    average_payment = DetailedDecimalStatSerializer(read_only=True)

class AdminCourseStatisticsDataSerializer(serializers.Serializer):
    courses_graph = GraphDataPointSerializer(many=True, read_only=True)
    total_courses = DetailedStatSerializer(read_only=True)
    enrollments = DetailedStatSerializer(read_only=True)
    completions = DetailedStatSerializer(read_only=True)

class AdminCombinedStatisticsSerializer(serializers.Serializer):
    users = AdminUserStatisticsDataSerializer(read_only=True)
    tests = AdminTestStatisticsDataSerializer(read_only=True)
    payments = AdminPaymentStatisticsDataSerializer(read_only=True)
    courses = AdminCourseStatisticsDataSerializer(read_only=True)

class AdminUserStatisticsDetailSerializer(serializers.Serializer):
    """Admin user detail page > Statistics tab uchun"""
    completed_tests = serializers.IntegerField(read_only=True)
    average_score = serializers.FloatField(read_only=True)
    total_payments = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

class AdminAddBalanceSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=decimal.Decimal('0.01'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

# --- Admin CRUD Serializers for other models ---
# (University, Achievement, Course, Lesson - avvalgidek yoki moslashtirilgan)
class AdminUniversitySerializer(UniversitySerializer): pass
class AdminAchievementSerializer(AchievementSerializer): pass

class AdminCourseCreateUpdateSerializer(serializers.ModelSerializer):
    """Admin Kurs yaratish/tahrirlash uchun."""
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())
    teacher = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='teacher'), allow_null=True, required=False) # Agar o'qituvchi roli bo'lsa
    thumbnail = serializers.ImageField(max_length=None, use_url=True, required=False, allow_null=True)

    class Meta:
        model = Course
        # Read-only bo'lgan hisoblanuvchi maydonlarni olib tashlaymiz
        exclude = ('created_at', 'last_updated', 'rating', 'enrolled_students_count', 'lessons_count')
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'requirements': {'required': False, 'allow_blank': True},
            'what_you_learn': {'required': False, 'allow_blank': True},
            'price': {'required': False, 'default': 0.00},
            'duration_weeks': {'required': False, 'allow_null': True},
            'has_certificate': {'required': False},
            'status': {'required': False},
        }
    # Narx validatsiyasi (AdminTestCreateUpdateSerializer ga o'xshash)
    def validate_price(self, value):
        if value < 0: raise serializers.ValidationError(_("Narx manfiy bo'lishi mumkin emas."))
        return decimal.Decimal(value)

class AdminLessonSerializer(serializers.ModelSerializer):
    """Admin dars yaratish/tahrirlash uchun."""
    video_file = serializers.FileField(max_length=None, use_url=True, required=False, allow_null=True)

    class Meta:
        model = Lesson
        fields = ('id', 'course', 'order', 'title', 'description', 'video_url', 'video_file',
                  'duration_minutes', 'is_free_preview')
        read_only_fields = ('id',)
        # course URL dan keladi, order avtomatik belgilanadi
        extra_kwargs = {
            'course': {'required': False, 'read_only': True},
            'order': {'required': False, 'read_only': True},
            'video_url': {'required': False, 'allow_blank': True},
            'duration_minutes': {'required': False, 'allow_null': True},
            'description': {'required': False, 'allow_blank': True},
            }

    def validate(self, data):
         # Video URL yoki Fayl bo'lishi kerak (lekin ikkalasi ham bo'lishi shart emas)
         video_url = data.get('video_url', getattr(self.instance, 'video_url', None))
         video_file = data.get('video_file') # Yangi yuklanayotgan fayl
         instance_file = getattr(self.instance, 'video_file', None) if self.instance else None

         if not video_url and not video_file and not instance_file:
             # Agar update bo'lsa va eski fayl ham bo'lmasa yoki create bo'lsa
             # raise serializers.ValidationError(_("Dars uchun Video URL yoki Video Fayl kiritilishi kerak."))
             pass # Ikkalasi ham ixtiyoriy bo'lishi mumkin

         if video_url and video_file is not None: # Agar yangi fayl ham kelsa, URL ustunroq
            data['video_file'] = None
         elif video_file is not None: # Agar faqat fayl kelsa
             data['video_url'] = None
             # Duration ni avto olish mumkin (lekin murakkab)

         return data