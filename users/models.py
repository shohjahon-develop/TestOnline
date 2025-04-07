import os
import decimal
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

def user_profile_picture_path(instance, filename):
    # Fayl nomini xavfsiz holga keltirish va unikal ID qo'shish
    ext = filename.split('.')[-1]
    # Ensure instance has a pk before generating filename if needed, or use a unique id
    user_id = instance.pk or timezone.now().strftime('%Y%m%d%H%M%S%f')
    filename = f'{user_id}_profile.{ext}'
    return os.path.join('profile_pictures/', filename)

class UserManager(BaseUserManager):
    def create_user(self, email, phone_number, full_name, password=None, role='student', **extra_fields):
        if not email:
            raise ValueError(_("Email kiritish majburiy"))
        if not phone_number:
             raise ValueError(_("Telefon raqam kiritish majburiy"))
        if not full_name:
            raise ValueError(_("To'liq ism kiritish majburiy"))

        email = self.normalize_email(email)
        # Ensure role is valid
        if role not in [r[0] for r in User.ROLE_CHOICES]:
            raise ValueError(_("Noto'g'ri rol tanlandi."))

        user = self.model(email=email, phone_number=phone_number, full_name=full_name, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        # Create related objects after user is saved and has a pk
        UserRating.objects.get_or_create(user=user)
        UserSettings.objects.get_or_create(user=user)
        return user

    def create_superuser(self, email, phone_number, full_name, password):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        # Create superuser with 'admin' role
        return self.create_user(email, phone_number, full_name, password, role='admin', **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        # ('teacher', 'Teacher'), # Add if needed
    ]
    GENDER_CHOICES = [
        ('male', 'Erkak'),
        ('female', 'Ayol'),
    ]

    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(_('phone number'), max_length=20, unique=True)
    full_name = models.CharField(_('full name'), max_length=255)
    birth_date = models.DateField(_('birth date'), blank=True, null=True)
    gender = models.CharField(_('gender'), max_length=10, choices=GENDER_CHOICES, blank=True, null=True)

    grade = models.CharField(_('grade/class'), max_length=50, blank=True, null=True)
    region = models.CharField(_('region'), max_length=100, blank=True, null=True)
    study_place = models.CharField(_('study place'), max_length=255, blank=True, null=True)
    address = models.TextField(_('address'), blank=True, null=True)
    target_university = models.CharField(_('target university'), max_length=255, blank=True, null=True)
    target_faculty = models.CharField(_('target faculty'), max_length=255, blank=True, null=True)
    about_me = models.TextField(_('about me'), blank=True, null=True)

    profile_picture = models.ImageField(_('profile picture'), upload_to=user_profile_picture_path, blank=True, null=True)
    balance = models.DecimalField(_('balance'), max_digits=12, decimal_places=2, default=0.00)
    role = models.CharField(_('role'), max_length=10, choices=ROLE_CHOICES, default='student')
    agreetoterms = models.BooleanField(_('agreed to terms'), default=False)

    is_active = models.BooleanField(_('active'), default=True)
    is_blocked = models.BooleanField(_('blocked'), default=False)
    is_staff = models.BooleanField(_('staff status'), default=False)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number', 'full_name']

    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="custom_user_groups",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_permissions",
        related_query_name="user",
    )

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def get_balance_display(self):
        try:
            # Ensure balance is a Decimal for formatting
            balance_decimal = decimal.Decimal(self.balance or 0)
            return f"{balance_decimal:,.0f} so'm".replace(',', ' ')
        except (TypeError, decimal.InvalidOperation):
            return "0 so'm" # Default if conversion fails


class Subject(models.Model):
    name = models.CharField(_('subject name'), max_length=100, unique=True)
    icon = models.ImageField(_('icon'), upload_to='subject_icons/', blank=True, null=True)

    class Meta:
        verbose_name = _('subject')
        verbose_name_plural = _('subjects')
        ordering = ['name']

    def __str__(self):
        return self.name


class Test(models.Model):
    DIFFICULTY_CHOICES = [
        ('oson', 'Oson'),
        ('orta', "O'rta"),
        ('qiyin', 'Qiyin'),
        ('murakkab', 'Murakkab'),
    ]
    TYPE_CHOICES = [
        ('free', 'Bepul'),
        ('premium', 'Premium'),
    ]
    STATUS_CHOICES = [
        ('active', 'Faol'),
        ('inactive', 'Nofaol'),
        ('draft', 'Qoralama'),
    ]

    title = models.CharField(_('test title'), max_length=255)
    subject = models.ForeignKey(Subject, related_name='tests', on_delete=models.CASCADE, verbose_name=_('subject'))
    description = models.TextField(_('description'), blank=True, null=True)
    question_count = models.IntegerField(_('number of questions'), default=0, validators=[MinValueValidator(0)]) # Can be 0 initially
    difficulty = models.CharField(_('difficulty'), max_length=10, choices=DIFFICULTY_CHOICES, default='orta')
    test_type = models.CharField(_('test type'), max_length=10, choices=TYPE_CHOICES, default='free')
    price = models.DecimalField(_('price'), max_digits=10, decimal_places=2, default=0.00, help_text=_("Premium testlar uchun narx (so'mda)"))
    reward_points = models.IntegerField(_('reward points'), default=0, help_text=_("Testni muvaffaqiyatli topshirganlik uchun beriladigan ball"))
    time_limit = models.IntegerField(_('time limit (minutes)'), default=60, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    status = models.CharField(_('status'), max_length=10, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_tests', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('created by'))

    class Meta:
        verbose_name = _('test')
        verbose_name_plural = _('tests')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.subject.name})"

    def save(self, *args, **kwargs):
        if self.test_type == 'free':
            self.price = 0.00
        # Update question count if not explicitly set (e.g., after adding questions via admin)
        # Note: This might be inefficient if called very frequently without necessity.
        # Consider updating count only when questions are added/removed.
        # if self.pk: # Only if the test already exists
        #    self.question_count = self.questions.count()
        super().save(*args, **kwargs)

class Question(models.Model):
    DIFFICULTY_CHOICES = Test.DIFFICULTY_CHOICES
    ANSWER_CHOICES = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]

    test = models.ForeignKey(Test, related_name='questions', on_delete=models.CASCADE, verbose_name=_('test'))
    question_text = models.TextField(_('question text'))
    # image = models.ImageField(upload_to='question_images/', blank=True, null=True)
    difficulty = models.CharField(_('difficulty'), max_length=10, choices=DIFFICULTY_CHOICES, default='orta')
    option_a = models.CharField(_('option A'), max_length=500)
    option_b = models.CharField(_('option B'), max_length=500)
    option_c = models.CharField(_('option C'), max_length=500)
    option_d = models.CharField(_('option D'), max_length=500)
    correct_answer = models.CharField(_('correct answer'), max_length=1, choices=ANSWER_CHOICES)
    explanation = models.TextField(_('explanation'), blank=True, null=True, help_text=_("To'g'ri javob uchun izoh"))
    points = models.PositiveSmallIntegerField(_('points'), default=1, help_text=_("Ushbu savol uchun ball"))
    order = models.PositiveIntegerField(_('order'), default=0, help_text=_("Test ichidagi tartib raqami"))

    class Meta:
        verbose_name = _('question')
        verbose_name_plural = _('questions')
        ordering = ['test', 'order', 'id']

    def __str__(self):
        return f"{self.test.title} - Q {self.order or self.id}"

    # Update Test question_count on save/delete using signals or overriding save/delete
    # For simplicity, we'll handle this in the admin/view logic for now.

class UserTestResult(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'Jarayonda'),
        ('completed', 'Tugatilgan'),
        ('cancelled', 'Bekor qilingan')
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='test_results', on_delete=models.CASCADE, verbose_name=_('user'))
    test = models.ForeignKey(Test, related_name='results', on_delete=models.CASCADE, verbose_name=_('test'))
    score = models.IntegerField(_('score'), default=0)
    total_questions = models.IntegerField(_('total questions'), default=0)
    percentage = models.FloatField(_('percentage'), default=0.0)
    start_time = models.DateTimeField(_('start time'), default=timezone.now) # Use default=timezone.now
    end_time = models.DateTimeField(_('end time'), null=True, blank=True)
    time_spent = models.DurationField(_('time spent'), null=True, blank=True)
    status = models.CharField(_('status'), max_length=20, default='in_progress', choices=STATUS_CHOICES)

    class Meta:
        verbose_name = _('user test result')
        verbose_name_plural = _('user test results')
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.user.full_name} - {self.test.title} ({self.score}/{self.total_questions})"

    def calculate_result(self, user_answers):
        correct_count = 0
        questions = self.test.questions.all()
        self.total_questions = questions.count()
        # Clear previous answers for this result if recalculating
        self.user_answers.all().delete()

        for question in questions:
            user_answer = user_answers.get(str(question.id)) # Ensure key is string
            is_correct = user_answer is not None and user_answer == question.correct_answer
            if is_correct:
                correct_count += question.points # Use question points
            UserAnswer.objects.create(
                result=self,
                question=question,
                selected_answer=user_answer,
                is_correct=is_correct
            )

        self.score = correct_count
        total_possible_points = sum(q.points for q in questions) # Calculate total possible points
        if total_possible_points > 0:
            self.percentage = round((correct_count / total_possible_points) * 100, 2)
        else:
            self.percentage = 0.0

        self.end_time = timezone.now()
        if self.start_time:
            self.time_spent = self.end_time - self.start_time
        self.status = 'completed'
        self.save()

        # Update UserRating
        try:
            user_rating = UserRating.objects.get(user=self.user)
            # Use a method in UserRating to handle subject-specific score update
            user_rating.update_score(self.score, self.test.subject.name)
        except UserRating.DoesNotExist:
            # Log this error or handle it appropriately
            print(f"Warning: UserRating not found for user {self.user.id}")
        except Exception as e:
            print(f"Error updating rating for user {self.user.id}: {e}")


class UserAnswer(models.Model):
    result = models.ForeignKey(UserTestResult, related_name='user_answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='user_answers', on_delete=models.CASCADE)
    selected_answer = models.CharField(_('selected answer'), max_length=1, choices=Question.ANSWER_CHOICES, null=True, blank=True)
    is_correct = models.BooleanField(_('is correct'), default=False)

    class Meta:
        verbose_name = _('user answer')
        verbose_name_plural = _('user answers')
        unique_together = ('result', 'question')

    # is_correct is set in UserTestResult.calculate_result
    def __str__(self):
        status = 'Correct' if self.is_correct else ('Incorrect' if self.selected_answer else 'Skipped')
        return f"Result {self.result.id} - Q {self.question.id}: {self.selected_answer or '-'} ({status})"


class Material(models.Model):
    TYPE_CHOICES = [
        ('book', 'Kitob'), ('video', 'Video dars'), ('guide', "Qo'llanma"),
        ('article', 'Maqola'), ('presentation', 'Prezentatsiya'),
        ('test_collection', "Test to'plami"), ('other', 'Boshqa'),
    ]
    FORMAT_CHOICES = [
        ('pdf', 'PDF'), ('docx', 'DOCX'), ('pptx', 'PPTX'), ('mp4', 'MP4'),
        ('mp3', 'MP3'), ('zip', 'ZIP'), ('link', 'Havola'), ('other', 'Boshqa'),
    ]
    STATUS_CHOICES = Test.STATUS_CHOICES

    title = models.CharField(_('material title'), max_length=255)
    subject = models.ForeignKey(Subject, related_name='materials', on_delete=models.CASCADE, verbose_name=_('subject'))
    description = models.TextField(_('description'), blank=True, null=True)
    material_type = models.CharField(_('material type'), max_length=20, choices=TYPE_CHOICES, default='book')
    file_format = models.CharField(_('file format'), max_length=10, choices=FORMAT_CHOICES, default='pdf')
    file = models.FileField(_('file'), upload_to='materials/', blank=True, null=True, help_text=_("Format 'link' bo'lmasa yuklang"))
    link = models.URLField(_('link'), blank=True, null=True, help_text=_("Format 'link' bo'lsa kiriting"))
    size_mb = models.FloatField(_('size (MB)'), blank=True, null=True, validators=[MinValueValidator(0)])
    downloads_count = models.PositiveIntegerField(_('downloads count'), default=0)
    status = models.CharField(_('status'), max_length=10, choices=STATUS_CHOICES, default='draft')
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='uploaded_materials', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('uploaded by'))
    is_free = models.BooleanField(_('is free'), default=True)
    price = models.DecimalField(_('price'), max_digits=10, decimal_places=2, default=0.00, help_text=_("Agar bepul bo'lmasa narxi"))

    class Meta:
        verbose_name = _('material')
        verbose_name_plural = _('materials')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} ({self.subject.name})"

    def increment_download_count(self):
        # Use F expression to avoid race conditions
        Material.objects.filter(pk=self.pk).update(downloads_count=models.F('downloads_count') + 1)
        self.refresh_from_db(fields=['downloads_count']) # Update instance

    def save(self, *args, **kwargs):
        if self.is_free:
            self.price = 0.00
        # Optionally calculate size_mb if file exists and size_mb is not set
        if self.file and self.size_mb is None:
            try:
                self.size_mb = round(self.file.size / (1024 * 1024), 2)
            except Exception:
                pass # Might happen if file is not saved yet
        super().save(*args, **kwargs)


class Payment(models.Model):
    TYPE_CHOICES = [
        ('deposit', 'Hisobni to\'ldirish'), ('test_purchase', 'Test sotib olish'),
        ('course_purchase', 'Kurs sotib olish'), ('material_purchase', 'Material sotib olish'),
        ('mock_test_purchase', 'Mock test sotib olish'), ('withdrawal', 'Chiqim'),
        ('refund', 'Qaytarish'), ('bonus', 'Bonus'), ('referral_bonus', "Do'stni taklif bonusi"),
    ]
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'), ('successful', 'Muvaffaqiyatli'),
        ('failed', 'Muvaffaqiyatsiz'), ('cancelled', 'Bekor qilingan'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('click', 'Click'), ('payme', 'Payme'), ('uzum', 'Uzum Bank'),
        ('internal', 'Ichki balans'), ('admin', 'Admin'), ('other', 'Boshqa')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='payments', on_delete=models.CASCADE, verbose_name=_('user'))
    amount = models.DecimalField(_('amount'), max_digits=12, decimal_places=2, help_text=_("Chiqimlar uchun manfiy bo'lishi mumkin"))
    payment_type = models.CharField(_('payment type'), max_length=20, choices=TYPE_CHOICES)
    description = models.CharField(_('description'), max_length=255, blank=True)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    payment_method = models.CharField(_('payment method'), max_length=15, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    transaction_id = models.CharField(_('transaction ID'), max_length=100, blank=True, null=True, unique=True, help_text=_("To'lov tizimi IDsi (agar bo'lsa)"))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    test = models.ForeignKey(Test, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True)
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    mock_test = models.ForeignKey('MockTest', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = _('payment')
        verbose_name_plural = _('payments')
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id} by {self.user.email} - {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        # Atomicity might be needed here if balance updates are critical and concurrent
        is_new = self._state.adding
        old_status = None
        if not is_new:
            try:
                old_instance = Payment.objects.get(pk=self.pk)
                old_status = old_instance.status
            except Payment.DoesNotExist:
                pass # Should not happen in normal flow

        super().save(*args, **kwargs)

        # Update balance only when status changes to successful
        if self.status == 'successful' and old_status != 'successful':
            try:
                user = User.objects.select_for_update().get(pk=self.user.pk) # Lock user row
                # Amount should be positive for deposits/bonuses, negative for purchases/withdrawals
                user.balance = (user.balance or 0) + self.amount # Ensure balance is not None
                user.save(update_fields=['balance'])
            except User.DoesNotExist:
                 print(f"Error: User {self.user.pk} not found during payment {self.pk} balance update.")
            except Exception as e:
                 print(f"Error updating balance for user {self.user.pk} on payment {self.pk}: {e}")


class UserRating(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='rating', on_delete=models.CASCADE, verbose_name=_('user'), primary_key=True)
    total_score = models.IntegerField(_('total score'), default=0, db_index=True)
    rank = models.PositiveIntegerField(_('rank'), default=0, db_index=True)

    # Subject scores - consider moving to a separate UserSubjectScore model for scalability
    math_score = models.IntegerField(_('mathematics score'), default=0)
    physics_score = models.IntegerField(_('physics score'), default=0)
    english_score = models.IntegerField(_('english score'), default=0)
    # Add other subjects as needed

    # Level system (example)
    level = models.PositiveIntegerField(_('level'), default=1)
    points_to_next_level = models.IntegerField(_('points for next level'), default=100)
    current_level_points = models.IntegerField(_('points in current level'), default=0) # Points accumulated within the current level

    last_updated = models.DateTimeField(_('last updated'), auto_now=True)

    LEVEL_THRESHOLDS = { # Example thresholds
        1: 0, 2: 100, 3: 250, 4: 500, 5: 1000, # ... define more levels
    }

    class Meta:
        verbose_name = _('user rating')
        verbose_name_plural = _('user ratings')
        ordering = ['rank', '-total_score'] # Order by rank first

    def __str__(self):
        return f"{self.user.full_name} - Score: {self.total_score}, Rank: {self.rank}"

    def calculate_level(self):
        """Calculates the user's level based on total score."""
        current_level = 1
        next_level_points = self.LEVEL_THRESHOLDS.get(2, 100) # Default for level 2
        points_in_level = self.total_score

        sorted_thresholds = sorted(self.LEVEL_THRESHOLDS.items())

        for level, threshold in sorted_thresholds:
            if self.total_score >= threshold:
                current_level = level
                # Find points for the next level
                try:
                    next_level_index = sorted_thresholds.index((level, threshold)) + 1
                    if next_level_index < len(sorted_thresholds):
                        next_level_points = sorted_thresholds[next_level_index][1]
                    else: # Max level reached
                        next_level_points = threshold # Or set to infinity/None
                except ValueError: # Should not happen
                    pass
                points_in_level = self.total_score - threshold
            else:
                # Found the level just below the current score
                next_level_points = threshold
                break # No need to check further levels

        self.level = current_level
        self.points_to_next_level = next_level_points
        self.current_level_points = points_in_level
        # Don't save here, let the calling method save

    def update_score(self, points_to_add, subject_name=None):
        """Updates subject score and recalculates total score and level."""
        updated = False
        if subject_name:
            subject_field_map = {
                'matematika': 'math_score',
                'fizika': 'physics_score',
                'ingliz tili': 'english_score',
                 # Add other subjects here
            }
            field_name = subject_field_map.get(subject_name.lower())
            if field_name and hasattr(self, field_name):
                current_score = getattr(self, field_name) or 0
                setattr(self, field_name, current_score + points_to_add)
                updated = True
            else:
                 # Handle generic points if subject not matched or not specified
                 print(f"Warning: Subject field for '{subject_name}' not found in UserRating. Adding to total score directly.")
                 self.total_score = (self.total_score or 0) + points_to_add
                 updated = True

        # Recalculate total score if subject score was updated or points were added directly
        if updated or not subject_name:
            # Recalculate total score from individual scores if subject scores are the source
            if subject_name and field_name:
                 self.total_score = (self.math_score or 0) + (self.physics_score or 0) + (self.english_score or 0) # Add all subject scores
            elif not subject_name: # Points added directly to total_score
                pass # Already updated above if subject_name was None
            else: # Subject not matched, points added directly
                 pass # Already updated above

            self.calculate_level() # Calculate level based on new total score
            self.save()
            # Consider triggering rank update after score changes (maybe debounced or periodic)
            # UserRating.update_ranks() # Costly to run on every update

    @staticmethod
    def update_ranks():
        """Updates rank for all active users based on total_score."""
        rank = 0
        current_score = -1
        same_rank_count = 1
        # Order by score descending, then by earliest join date for ties
        ratings = UserRating.objects.filter(user__is_active=True, user__is_blocked=False).order_by('-total_score', 'user__date_joined')

        for i, rating in enumerate(ratings):
            if rating.total_score != current_score:
                rank += same_rank_count # Move rank by the number of users with the previous score
                current_score = rating.total_score
                same_rank_count = 1
            else:
                same_rank_count += 1

            # Check if rank needs updating to avoid unnecessary saves
            if rating.rank != rank:
                rating.rank = rank
                # Use update() for potentially better performance on large datasets,
                # but saving instance by instance is safer for signals/complex logic.
                rating.save(update_fields=['rank'])
        print(f"Ranks updated for {ratings.count()} users.")


class MockTest(models.Model):
    MOCK_TYPE_CHOICES = [
        ('ielts', 'IELTS'), ('toefl', 'TOEFL'), ('cefr', 'CEFR'), ('sat', 'SAT'),
        ('milliy_sertifikat', 'Milliy Sertifikat'), ('dtm', 'DTM Blok Test'),
        ('other', 'Boshqa'),
    ]
    LANGUAGE_CHOICES = [
        ('en', 'Ingliz tili'), ('tr', 'Turk tili'), ('ar', 'Arab tili'),
        ('uz', "O'zbek tili"), ('ru', 'Rus tili'),
    ]
    STATUS_CHOICES = Test.STATUS_CHOICES

    title = models.CharField(_('mock test title'), max_length=255)
    mock_type = models.CharField(_('mock test type'), max_length=20, choices=MOCK_TYPE_CHOICES, default='ielts')
    language = models.CharField(_('language'), max_length=20, choices=LANGUAGE_CHOICES, default='en', blank=True, null=True)
    description = models.TextField(_('description'), blank=True, null=True)
    price = models.DecimalField(_('price'), max_digits=10, decimal_places=2, default=50000.00)
    duration_minutes = models.IntegerField(_('total duration (minutes)'), default=165)
    sections_info = models.JSONField(_('sections info'), blank=True, null=True, help_text=_("Bo'limlar haqida ma'lumot (JSON)"))
    rules = models.TextField(_('rules'), blank=True, null=True)
    status = models.CharField(_('status'), max_length=10, choices=STATUS_CHOICES, default='draft')
    available_from = models.DateField(_('available from'), blank=True, null=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_mock_tests', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = _('mock test')
        verbose_name_plural = _('mock tests')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_mock_type_display()})"


class MockTestResult(models.Model):
    STATUS_CHOICES = UserTestResult.STATUS_CHOICES # Use same statuses
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='mock_test_results', on_delete=models.CASCADE)
    mock_test = models.ForeignKey(MockTest, related_name='results', on_delete=models.CASCADE)
    overall_score = models.DecimalField(_('overall score/band'), max_digits=3, decimal_places=1, null=True, blank=True)
    section_scores = models.JSONField(_('section scores'), blank=True, null=True)
    start_time = models.DateTimeField(_('start time'), default=timezone.now)
    end_time = models.DateTimeField(_('end time'), null=True, blank=True)
    status = models.CharField(_('status'), max_length=20, default='in_progress', choices=STATUS_CHOICES)
    feedback = models.TextField(_('feedback/comments'), blank=True, null=True)

    class Meta:
        verbose_name = _('mock test result')
        verbose_name_plural = _('mock test results')
        ordering = ['-start_time']

    def __str__(self):
        score_display = f" (Score: {self.overall_score})" if self.overall_score else ""
        return f"{self.user.full_name} - {self.mock_test.title}{score_display}"

    # Add calculate_overall_score method similar to UserRating if needed


class MockTestMaterial(models.Model):
    mock_test_type = models.CharField(_('mock test type'), max_length=20, choices=MockTest.MOCK_TYPE_CHOICES, db_index=True)
    language = models.CharField(_('language'), max_length=20, choices=MockTest.LANGUAGE_CHOICES, db_index=True, blank=True, null=True)
    title = models.CharField(_('material title'), max_length=255)
    description = models.TextField(_('description'), blank=True, null=True)
    file = models.FileField(_('file'), upload_to='mock_test_materials/', blank=True, null=True)
    link = models.URLField(_('link'), blank=True, null=True)
    material_format = models.CharField(_('format'), max_length=10, choices=Material.FORMAT_CHOICES, default='pdf')
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    is_free = models.BooleanField(_('is free'), default=True)

    class Meta:
        verbose_name = _('mock test material')
        verbose_name_plural = _('mock test materials')
        ordering = ['mock_test_type', 'language', '-uploaded_at']

    def __str__(self):
        lang = f" ({self.get_language_display()})" if self.language else ""
        return f"{self.get_mock_test_type_display()}{lang} - {self.title}"


class University(models.Model):
    REGION_CHOICES = [
        ('Toshkent sh.', 'Toshkent sh.'), ('Andijon', 'Andijon'), ('Buxoro', 'Buxoro'),
        ('Fargʻona', "Farg'ona"), ('Jizzax', 'Jizzax'), ('Xorazm', 'Xorazm'),
        ('Namangan', 'Namangan'), ('Navoiy', 'Navoiy'), ('Qashqadaryo', 'Qashqadaryo'),
        ('Qoraqalpogʻiston R.', "Qoraqalpog'iston R."), ('Samarqand', 'Samarqand'),
        ('Sirdaryo', 'Sirdaryo'), ('Surxondaryo', 'Surxondaryo'), ('Toshkent vil.', 'Toshkent vil.'),
    ]

    name = models.CharField(_('university name'), max_length=255)
    short_name = models.CharField(_('short name'), max_length=20, blank=True, null=True)
    logo = models.ImageField(_('logo'), upload_to='university_logos/', blank=True, null=True)
    region = models.CharField(_('region'), max_length=50, choices=REGION_CHOICES, db_index=True)
    website = models.URLField(_('website'), blank=True, null=True)
    description = models.TextField(_('description'), blank=True, null=True)
    faculties_info = models.JSONField(_('faculties info'), blank=True, null=True, help_text=_("Fakultetlar va kodlari"))
    admission_scores_info = models.JSONField(_('admission scores info'), blank=True, null=True, help_text=_("Kirish ballari (yil bo'yicha)"))

    class Meta:
        verbose_name = _('university')
        verbose_name_plural = _('universities')
        ordering = ['region', 'name']

    def __str__(self):
        return f"{self.name} ({self.region})"


class Achievement(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'Umumiy'), ('tests', 'Testlar'), ('streak', 'Streak'),
        ('mock_tests', 'Mock Testlar'), ('courses', 'Kurslar'), ('profile', 'Profil'),
        ('community', 'Jamiyat'),
    ]

    name = models.CharField(_('achievement name'), max_length=255)
    description = models.TextField(_('description'))
    category = models.CharField(_('category'), max_length=20, choices=CATEGORY_CHOICES, default='general', db_index=True)
    points_reward = models.IntegerField(_('points reward'), default=0)
    icon = models.CharField(_('icon name'), max_length=50, blank=True, null=True, help_text=_("Frontend ikonka nomi"))
    is_active = models.BooleanField(_('is active'), default=True)
    # Add condition fields if automatic awarding is needed
    # condition_type = models.CharField(...) e.g., 'test_count', 'streak_days', 'score_above'
    # condition_value = models.IntegerField(...) e.g., 10 (tests), 7 (days), 90 (score)
    # condition_subject = models.ForeignKey(Subject, ...) for subject-specific achievements

    class Meta:
        verbose_name = _('achievement')
        verbose_name_plural = _('achievements')
        ordering = ['category', 'points_reward']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class UserAchievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='achievements', on_delete=models.CASCADE, verbose_name=_('user'))
    achievement = models.ForeignKey(Achievement, related_name='earned_by', on_delete=models.CASCADE, verbose_name=_('achievement'))
    earned_at = models.DateTimeField(_('earned at'), null=True, blank=True) # Set when completed
    progress = models.IntegerField(_('progress'), default=0)
    target = models.IntegerField(_('target'), default=1) # Target value for the achievement condition
    created_at = models.DateTimeField(auto_now_add=True) # When tracking started

    class Meta:
        verbose_name = _('user achievement')
        verbose_name_plural = _('user achievements')
        unique_together = ('user', 'achievement')
        ordering = ['-created_at']

    def __str__(self):
        status = "Completed" if self.is_completed else f"{self.progress}/{self.target}"
        return f"{self.user.full_name} - {self.achievement.name} ({status})"

    @property
    def is_completed(self):
        completed = self.progress >= self.target
        if completed and not self.earned_at:
            # Mark as earned when completed for the first time
            self.earned_at = timezone.now()
            # Consider awarding points here or via a signal
            # self.user.rating.update_score(self.achievement.points_reward)
        return completed

    # Consider adding a method to update progress
    # def update_progress(self, value):
    #     self.progress = value
    #     if self.is_completed: # This will set earned_at if needed
    #         pass
    #     self.save()


class Course(models.Model):
    STATUS_CHOICES = Test.STATUS_CHOICES
    DIFFICULTY_CHOICES = Test.DIFFICULTY_CHOICES
    LANGUAGE_CHOICES = MockTest.LANGUAGE_CHOICES

    title = models.CharField(_('course title'), max_length=255)
    subject = models.ForeignKey(Subject, related_name='courses', on_delete=models.CASCADE, verbose_name=_('subject'))
    description = models.TextField(_('description'))
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='taught_courses', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role__in': ['admin', 'teacher']}, verbose_name=_('teacher')) # Allow admin or teacher
    price = models.DecimalField(_('price'), max_digits=10, decimal_places=2, default=0.00)
    duration_weeks = models.PositiveSmallIntegerField(_('duration (weeks)'), blank=True, null=True)
    lessons_count = models.PositiveSmallIntegerField(_('lessons count'), default=0)
    difficulty = models.CharField(_('difficulty'), max_length=10, choices=DIFFICULTY_CHOICES, default='orta')
    language = models.CharField(_('language'), max_length=20, choices=LANGUAGE_CHOICES, default='uz')
    thumbnail = models.ImageField(_('thumbnail'), upload_to='course_thumbnails/', blank=True, null=True)
    requirements = models.TextField(_('requirements'), blank=True, null=True)
    what_you_learn = models.TextField(_('what you learn'), blank=True, null=True)
    has_certificate = models.BooleanField(_('certificate provided'), default=False)
    status = models.CharField(_('status'), max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    last_updated = models.DateTimeField(_('last updated'), auto_now=True)
    rating = models.FloatField(_('average rating'), default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    enrolled_students_count = models.PositiveIntegerField(_('enrolled students count'), default=0)

    class Meta:
        verbose_name = _('course')
        verbose_name_plural = _('courses')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.subject.name})"

    def update_lessons_count(self):
        self.lessons_count = self.lessons.count()
        self.save(update_fields=['lessons_count'])

    def update_rating(self):
        avg = self.reviews.aggregate(avg_rating=models.Avg('rating'))['avg_rating']
        self.rating = round(avg, 1) if avg else 0.0
        self.save(update_fields=['rating'])

    def update_enrollment_count(self):
        self.enrolled_students_count = self.enrollments.count()
        self.save(update_fields=['enrolled_students_count'])


class Lesson(models.Model):
    course = models.ForeignKey(Course, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(_('lesson title'), max_length=255)
    description = models.TextField(_('description'), blank=True, null=True)
    video_url = models.URLField(_('video URL'), blank=True, null=True)
    video_file = models.FileField(_('video file'), upload_to='lesson_videos/', blank=True, null=True)
    duration_minutes = models.PositiveSmallIntegerField(_('duration (minutes)'), blank=True, null=True)
    order = models.PositiveIntegerField(_('order'), default=0)
    is_free_preview = models.BooleanField(_('free preview'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('lesson')
        verbose_name_plural = _('lessons')
        ordering = ['course', 'order']

    def __str__(self):
        return f"{self.course.title} - L{self.order}: {self.title}"

    # Update Course lessons_count on save/delete using signals or overriding save/delete


class UserCourseEnrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='enrollments', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name='enrollments', on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress = models.FloatField(_('progress percentage'), default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    last_accessed_lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = _('course enrollment')
        verbose_name_plural = _('course enrollments')
        unique_together = ('user', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.user.full_name} enrolled in {self.course.title}"

    def save(self, *args, **kwargs):
         is_new = self._state.adding
         super().save(*args, **kwargs)
         if is_new:
             self.course.update_enrollment_count()

    def delete(self, *args, **kwargs):
         course = self.course
         super().delete(*args, **kwargs)
         course.update_enrollment_count()


class CourseReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='course_reviews', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name='reviews', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(_('rating'), validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(_('comment'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('course review')
        verbose_name_plural = _('course reviews')
        unique_together = ('user', 'course')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.course.title} by {self.user.full_name} ({self.rating} stars)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.course.update_rating()

    def delete(self, *args, **kwargs):
        course = self.course
        super().delete(*args, **kwargs)
        course.update_rating()


class ScheduleItem(models.Model):
    DAY_CHOICES = [
        (1, 'Dushanba'), (2, 'Seshanba'), (3, 'Chorshanba'),
        (4, 'Payshanba'), (5, 'Juma'), (6, 'Shanba'), (7, 'Yakshanba')
    ]
    TYPE_CHOICES = [
        ('lesson', 'Dars'), ('test', 'Test'), ('study', "Mustaqil o'qish"),
        ('event', 'Tadbir'), ('other', 'Boshqa'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='schedule_items', on_delete=models.CASCADE)
    day_of_week = models.PositiveSmallIntegerField(_('day of week'), choices=DAY_CHOICES)
    start_time = models.TimeField(_('start time'))
    end_time = models.TimeField(_('end time'))
    title = models.CharField(_('title'), max_length=255)
    item_type = models.CharField(_('item type'), max_length=10, choices=TYPE_CHOICES, default='study')
    description = models.TextField(_('description'), blank=True, null=True)

    class Meta:
        verbose_name = _('schedule item')
        verbose_name_plural = _('schedule items')
        ordering = ['user', 'day_of_week', 'start_time']

    def __str__(self):
        return f"{self.user.full_name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}: {self.title}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('new_test', 'Yangi test'), ('new_course', 'Yangi kurs'), ('new_material', 'Yangi material'),
        ('test_result', 'Test natijasi'), ('mock_test_result', 'Mock test natijasi'),
        ('payment_success', "Muvaffaqiyatli to'lov"), ('payment_failed', "Muvaffaqiyatsiz to'lov"),
        ('achievement_unlocked', 'Yutuqqa erishildi'), ('schedule_reminder', 'Jadval eslatmasi'),
        ('announcement', "E'lon"), ('system', 'Tizim xabari'), ('course_enrollment', 'Kursga yozilish'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    message = models.CharField(_('message'), max_length=255)
    notification_type = models.CharField(_('type'), max_length=20, choices=TYPE_CHOICES)
    is_read = models.BooleanField(_('is read'), default=False, db_index=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    link = models.CharField(_('link'), max_length=500, blank=True, null=True, help_text=_("Frontend uchun link (masalan, '/tests/123')"))
    related_object_id = models.PositiveIntegerField(null=True, blank=True) # Qaysi obyektga tegishli (Test ID, Course ID, etc.)
    # content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True) # Generic relation uchun
    # object_id = models.PositiveIntegerField(null=True, blank=True)
    # content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.email}: {self.message[:50]}"


class UserSettings(models.Model):
    THEME_CHOICES = [('light', "Yorug'"), ('dark', 'Tungi')]
    LANGUAGE_CHOICES = [('uz', "O'zbek"), ('ru', 'Русский'), ('en', 'English')]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='settings', on_delete=models.CASCADE, primary_key=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='uz')
    theme = models.CharField(max_length=5, choices=THEME_CHOICES, default='light')
    autoplay_videos = models.BooleanField(default=True)
    sound_effects = models.BooleanField(default=False)
    high_contrast = models.BooleanField(default=False)

    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)
    notify_push = models.BooleanField(default=True)
    notify_test_updates = models.BooleanField(default=True)
    notify_course_updates = models.BooleanField(default=True)
    notify_payments = models.BooleanField(default=True)
    notify_reminders = models.BooleanField(default=True)

    two_factor_enabled = models.BooleanField(default=False)
    weekly_reports = models.BooleanField(default=True)
    personalized_recommendations = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('user settings')
        verbose_name_plural = _('user settings')

    def __str__(self):
        return f"Settings for {self.user.email}"
