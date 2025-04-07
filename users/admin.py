# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Subject, Test, Question, UserTestResult, UserAnswer, Material, Payment,
    UserRating, MockTest, MockTestResult, MockTestMaterial, University,
    Achievement, UserAchievement, Course, Lesson, UserCourseEnrollment,
    CourseReview, ScheduleItem, Notification, UserSettings
)

# Inlines
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ('order', 'question_text', 'difficulty', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'points')
    ordering = ('order',)
    fk_name = 'test' # Explicitly set foreign key name

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('order', 'title', 'duration_minutes', 'is_free_preview', 'video_url', 'video_file')
    ordering = ('order',)
    fk_name = 'course' # Explicitly set foreign key name

class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    can_delete = False
    verbose_name_plural = 'Sozlamalar'
    fk_name = 'user'

class UserRatingInline(admin.StackedInline):
    model = UserRating
    can_delete = False
    verbose_name_plural = 'Reyting'
    fk_name = 'user'
    readonly_fields = ('total_score', 'rank', 'level', 'points_to_next_level', 'current_level_points', 'last_updated')
    fields = ('total_score', 'rank', 'level', 'math_score', 'physics_score', 'english_score')

# ModelAdmins
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'phone_number', 'role', 'is_active', 'is_blocked', 'is_staff', 'date_joined', 'get_balance_display')
    list_filter = ('role', 'is_active', 'is_blocked', 'is_staff', 'gender', 'region')
    search_fields = ('email', 'full_name', 'phone_number')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'phone_number', 'birth_date', 'gender', 'profile_picture')}),
        ('Student info', {'fields': ('grade', 'region', 'study_place', 'address', 'target_university', 'target_faculty', 'about_me')}),
        ('Platform Data', {'fields': ('balance',)}),
        ('Permissions', {'fields': ('is_active', 'is_blocked', 'is_staff', 'is_superuser', 'role', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone_number', 'password', 'password2', 'role'),
        }),
    )
    readonly_fields = ('last_login', 'date_joined', 'get_balance_display')
    inlines = (UserSettingsInline, UserRatingInline)
    # Remove default username field if not used explicitly
    exclude = ('username',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'id')
    search_fields = ('name',)

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'test_type', 'question_count', 'difficulty', 'status', 'price', 'created_at', 'created_by')
    list_filter = ('subject', 'test_type', 'difficulty', 'status') # Removed created_by as it might be null
    search_fields = ('title', 'subject__name', 'description')
    inlines = [QuestionInline]
    readonly_fields = ('created_at', 'updated_at', 'question_count') # question_count is updated via inline save
    list_editable = ('status', 'test_type', 'difficulty')
    list_select_related = ('subject', 'created_by')
    fieldsets = (
        (None, {'fields': ('title', 'subject', 'description')}),
        ('Details', {'fields': ('test_type', 'price', 'difficulty', 'time_limit', 'reward_points')}),
        ('Status & Meta', {'fields': ('status', 'created_by', 'created_at', 'updated_at', 'question_count')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk: # If creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            # You can add logic here if needed before saving each question
            instance.save()
        formset.save_m2m()
        # Update the question count on the Test instance
        test_instance = form.instance
        test_instance.question_count = test_instance.questions.count()
        test_instance.save(update_fields=['question_count'])

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'test_title', 'question_text_short', 'difficulty', 'correct_answer', 'order')
    list_filter = ('test__subject', 'difficulty', 'test__title') # Filter by test title
    search_fields = ('question_text', 'test__title')
    raw_id_fields = ('test',)
    list_select_related = ('test',)

    def test_title(self, obj):
        return obj.test.title
    test_title.short_description = 'Test'
    test_title.admin_order_field = 'test__title'

    def question_text_short(self, obj):
        return obj.question_text[:80] + '...' if len(obj.question_text) > 80 else obj.question_text
    question_text_short.short_description = 'Savol matni'

@admin.register(UserTestResult)
class UserTestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'status', 'score', 'total_questions', 'percentage', 'start_time', 'time_spent')
    list_filter = ('status', 'test__subject', 'test__title') # Filter by test title
    search_fields = ('user__email', 'user__full_name', 'test__title')
    readonly_fields = ('user', 'test', 'score', 'total_questions', 'percentage', 'start_time', 'end_time', 'time_spent', 'user_answers_link')
    date_hierarchy = 'start_time'
    list_select_related = ('user', 'test')

    def user_answers_link(self, obj):
        # Provide a link to filter UserAnswer admin for this result
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:users_useranswer_changelist') + f'?result__id__exact={obj.id}'
        return format_html('<a href="{}">Ko\'rish</a>', url)
    user_answers_link.short_description = 'Javoblar'

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('result_id', 'question_short', 'selected_answer', 'is_correct')
    list_filter = ('is_correct', 'result__test__subject', 'result__test__title')
    search_fields = ('result__user__email', 'question__question_text')
    readonly_fields = ('result', 'question', 'selected_answer', 'is_correct')
    list_select_related = ('result', 'question')

    def result_id(self, obj):
        return obj.result.id
    result_id.short_description = 'Natija ID'
    result_id.admin_order_field = 'result__id'

    def question_short(self, obj):
        return obj.question.question_text[:50] + '...' if len(obj.question.question_text) > 50 else obj.question.question_text
    question_short.short_description = 'Savol'

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'material_type', 'file_format', 'status', 'is_free', 'price', 'downloads_count', 'uploaded_at')
    list_filter = ('subject', 'material_type', 'file_format', 'status', 'is_free')
    search_fields = ('title', 'subject__name', 'description')
    readonly_fields = ('uploaded_at', 'uploaded_by', 'downloads_count')
    list_editable = ('status', 'is_free')
    list_select_related = ('subject', 'uploaded_by')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount_display', 'payment_type', 'status', 'payment_method', 'created_at', 'transaction_id', 'related_object_link')
    list_filter = ('status', 'payment_type', 'payment_method', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'transaction_id', 'description')
    readonly_fields = ('created_at', 'updated_at', 'user', 'amount', 'payment_type', 'description', 'payment_method', 'transaction_id', 'test', 'course', 'material', 'mock_test') # Make most fields read-only
    date_hierarchy = 'created_at'
    list_select_related = ('user', 'test', 'course', 'material', 'mock_test')

    def amount_display(self, obj):
        sign = "+" if obj.amount >= 0 else ""
        return f"{sign}{obj.amount:,.2f} so'm".replace(',', ' ')
    amount_display.short_description = 'Summa'
    amount_display.admin_order_field = 'amount'

    def related_object_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        related_obj = obj.test or obj.course or obj.material or obj.mock_test
        if related_obj:
            app_label = related_obj._meta.app_label
            model_name = related_obj._meta.model_name
            url = reverse(f'admin:{app_label}_{model_name}_change', args=[related_obj.pk])
            return format_html('<a href="{}">{}</a>', url, str(related_obj))
        return "-"
    related_object_link.short_description = 'Tegishli Obyekt'


@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_score', 'rank', 'level', 'math_score', 'physics_score', 'english_score', 'last_updated')
    search_fields = ('user__email', 'user__full_name')
    readonly_fields = ('user', 'total_score', 'rank', 'level', 'points_to_next_level', 'current_level_points', 'last_updated')
    actions = ['update_all_ranks']
    list_select_related = ('user',)

    def update_all_ranks(self, request, queryset):
        UserRating.update_ranks()
        self.message_user(request, "Barcha foydalanuvchilar reytingi yangilandi.")
    update_all_ranks.short_description = "Barcha reytinglarni yangilash"

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ('title', 'mock_type', 'language', 'price', 'status', 'available_from', 'created_at')
    list_filter = ('mock_type', 'language', 'status', 'available_from')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'created_by')
    list_editable = ('status', 'price')
    list_select_related = ('created_by',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(MockTestResult)
class MockTestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'mock_test', 'overall_score', 'status', 'start_time')
    list_filter = ('status', 'mock_test__mock_type', 'mock_test__language')
    search_fields = ('user__email', 'user__full_name', 'mock_test__title')
    readonly_fields = ('user', 'mock_test', 'overall_score', 'section_scores', 'start_time', 'end_time', 'feedback')
    date_hierarchy = 'start_time'
    list_select_related = ('user', 'mock_test')

@admin.register(MockTestMaterial)
class MockTestMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'mock_test_type', 'language', 'material_format', 'is_free', 'uploaded_at')
    list_filter = ('mock_test_type', 'language', 'material_format', 'is_free')
    search_fields = ('title', 'description')
    readonly_fields = ('uploaded_at',)
    list_editable = ('is_free',)

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'region', 'website')
    list_filter = ('region',)
    search_fields = ('name', 'short_name', 'region')
    list_editable = ('region',)

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'points_reward', 'icon', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'points_reward')

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'is_completed', 'progress', 'target', 'earned_at', 'created_at')
    list_filter = ('achievement__category', 'earned_at', 'achievement')
    search_fields = ('user__email', 'user__full_name', 'achievement__name')
    readonly_fields = ('user', 'achievement', 'earned_at', 'created_at', 'is_completed')
    date_hierarchy = 'created_at'
    list_select_related = ('user', 'achievement')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'teacher', 'price', 'status', 'difficulty', 'language', 'lessons_count', 'rating', 'enrolled_students_count', 'created_at')
    list_filter = ('subject', 'teacher', 'status', 'difficulty', 'language', 'has_certificate')
    search_fields = ('title', 'subject__name', 'teacher__full_name', 'description')
    inlines = [LessonInline]
    readonly_fields = ('created_at', 'last_updated', 'lessons_count', 'rating', 'enrolled_students_count')
    list_editable = ('status', 'price', 'difficulty')
    raw_id_fields = ('teacher',)
    list_select_related = ('subject', 'teacher')

    def save_formset(self, request, form, formset, change):
        instances = formset.save()
        form.instance.update_lessons_count()

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'duration_minutes', 'is_free_preview')
    list_filter = ('course__subject', 'course__title', 'is_free_preview')
    search_fields = ('title', 'course__title')
    raw_id_fields = ('course',)
    list_select_related = ('course',)
    list_editable = ('order', 'is_free_preview')

@admin.register(UserCourseEnrollment)
class UserCourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'enrolled_at', 'progress', 'completed_at')
    list_filter = ('course__subject', 'course__title')
    search_fields = ('user__email', 'user__full_name', 'course__title')
    readonly_fields = ('user', 'course', 'enrolled_at', 'completed_at', 'last_accessed_lesson')
    date_hierarchy = 'enrolled_at'
    list_select_related = ('user', 'course')

@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'rating', 'created_at')
    list_filter = ('rating', 'course__subject', 'course__title')
    search_fields = ('user__email', 'user__full_name', 'course__title', 'comment')
    readonly_fields = ('user', 'course', 'created_at')
    date_hierarchy = 'created_at'
    list_select_related = ('user', 'course')

@admin.register(ScheduleItem)
class ScheduleItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_day_of_week_display', 'start_time', 'end_time', 'title', 'item_type')
    list_filter = ('user', 'day_of_week', 'item_type')
    search_fields = ('user__email', 'user__full_name', 'title', 'description')
    list_editable = ('item_type',)
    raw_id_fields = ('user',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_short', 'notification_type', 'is_read', 'created_at', 'link')
    list_filter = ('notification_type', 'is_read', 'created_at', 'user')
    search_fields = ('user__email', 'user__full_name', 'message')
    readonly_fields = ('user', 'message', 'notification_type', 'created_at', 'link', 'related_object_id')
    list_editable = ('is_read',)
    date_hierarchy = 'created_at'
    list_select_related = ('user',)

    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Xabar'

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'language', 'theme', 'notify_email', 'notify_push')
    search_fields = ('user__email', 'user__full_name')
    raw_id_fields = ('user',)
    fieldsets = (
        ('Preferences', {'fields': ('language', 'theme', 'autoplay_videos', 'sound_effects', 'high_contrast')}),
        ('Notifications', {'fields': ('notify_email', 'notify_sms', 'notify_push', 'notify_test_updates', 'notify_course_updates', 'notify_payments', 'notify_reminders')}),
        ('Security', {'fields': ('two_factor_enabled',)}),
        ('Statistics', {'fields': ('weekly_reports', 'personalized_recommendations')}),
    )