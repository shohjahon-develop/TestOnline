# users/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, email, phone_number, full_name, password=None, role='student', **extra_fields):
        if not email:
            raise ValueError("Email kiritish majburiy")
        email = self.normalize_email(email)
        user = self.model(email=email, phone_number=phone_number, full_name=full_name, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone_number, full_name, password):
        user = self.create_user(email, phone_number, full_name, password, role='superadmin')
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('superadmin', 'SuperAdmin'),
    ]

    GENDER_CHOICES = [
        ('male', 'Erkak'),
        ('female', 'Ayol'),
    ]

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, unique=True, blank=True, null=True)  # Yangi username maydoni
    birth_date = models.DateField(blank=True, null=True)  # Yangi birth_date maydoni
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)  # Yangi gender maydoni
    grade = models.CharField(max_length=20, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)  # Yangi region maydoni
    study_place = models.CharField(max_length=255, blank=True, null=True)  # study_place o'rniga school sifatida ishlatamiz
    address = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

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
        related_name="users_user_groups",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_(
            'Specific permissions for this user.'
        ),
        related_name="users_user_permissions",
        related_query_name="user",
    )

    def __str__(self):
        return f"{self.full_name} - {self.role}"

# Qolgan modellar o'zgarishsiz qoladi
class Test(models.Model):
    title = models.CharField(max_length=255)
    fan = models.CharField(max_length=255)
    savol_soni = models.IntegerField(default=0)
    qiyinlik = models.CharField(max_length=50)
    narx = models.IntegerField(default=0)
    mukofot = models.IntegerField(default=0)
    tavsif = models.TextField(blank=True, null=True)
    vaqt_chegarasi = models.IntegerField(default=60)
    qoshilgan_sana = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=50, default='Faol')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='tests', on_delete=models.CASCADE)
    is_mock = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Savol(models.Model):
    QIYINLIK_CHOICES = [
        ('oson', 'Oson'),
        ('orta', 'O\'rta'),
        ('qiyin', 'Qiyin'),
        ('murakkab', 'Murakkab'),
    ]

    test = models.ForeignKey(Test, related_name='savollar', on_delete=models.CASCADE)
    savol_matni = models.TextField()
    qiyinlik = models.CharField(max_length=10, choices=QIYINLIK_CHOICES, default='oson')
    variant_a = models.CharField(max_length=255)
    variant_b = models.CharField(max_length=255)
    variant_c = models.CharField(max_length=255)
    variant_d = models.CharField(max_length=255)
    togri_javob = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])

    def __str__(self):
        return self.savol_matni[:50]

class OquvMaterial(models.Model):
    MATERIAL_TURLARI = [
        ('kitob', 'Kitob'),
        ('video', 'Video dars'),
        ('qollanma', 'Qo\'llanma'),
        ('maqola', 'Maqola'),
        ('boshqa', 'Boshqa'),
    ]

    FORMAT_TURLARI = [
        ('pdf', 'PDF'),
        ('mp4', 'MP4'),
        ('ppt', 'PPT'),
        ('doc', 'DOC'),
        ('boshqa', 'Boshqa'),
    ]

    fan = models.CharField(max_length=255)
    material_nomi = models.CharField(max_length=255)
    tur = models.CharField(max_length=50, choices=MATERIAL_TURLARI, default='kitob')
    format = models.CharField(max_length=50, choices=FORMAT_TURLARI, default='pdf')
    hajm = models.CharField(max_length=50)
    yuklab_olish_imkoniyati = models.BooleanField(default=True)
    status = models.CharField(max_length=50, default='Faol')
    yuklangan_sana = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.material_nomi

class Tolov(models.Model):
    TUR_CHOYSLARI = [
        ('kirim', 'Kirim'),
        ('chiqim', 'Chiqim'),
    ]

    STATUS_CHOYSLARI = [
        ('muvaffaqiyatli', 'Muvaffaqiyatli'),
        ('bekor_qilingan', 'Bekor qilingan'),
        ('kutilmoqda', 'Kutilmoqda'),
    ]

    foydalanuvchi = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='tolovlar', on_delete=models.CASCADE)
    tavsif = models.CharField(max_length=255)
    tur = models.CharField(max_length=10, choices=TUR_CHOYSLARI, default='kirim')
    summa = models.DecimalField(max_digits=12, decimal_places=2)
    sana = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOYSLARI, default='muvaffaqiyatli')

    def __str__(self):
        return f"{self.tavsif} - {self.summa} so'm"

class Reyting(models.Model):
    foydalanuvchi = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reytinglar', on_delete=models.CASCADE)
    umumiy_ball = models.IntegerField(default=0)
    testlar_ball = models.IntegerField(default=0)
    kurslar_ball = models.IntegerField(default=0)
    platforma_vaqti_ball = models.IntegerField(default=0)
    matematika_reyting = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    fizika_reyting = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ingliz_tili_reyting = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.foydalanuvchi.full_name} - {self.umumiy_ball}"

    def hisoblash_umumiy_ball(self):
        self.umumiy_ball = self.testlar_ball + self.kurslar_ball + self.platforma_vaqti_ball
        self.save()

class IELTSUmumiy(models.Model):
    foydalanuvchi = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='ielts_umumiy', on_delete=models.CASCADE)
    joriy_baho = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    maqsad_baho = models.DecimalField(max_digits=3, decimal_places=1, default=7.5)
    listening = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    reading = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    writing = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    speaking = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    keyingi_imtihon_sanasi = models.DateField(blank=True, null=True)
    umumiy_progress = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.foydalanuvchi.full_name} - IELTS Umumiy"

class IELTSTest(models.Model):
    TIL_CHOYSLARI = [
        ('ingliz', 'Ingliz tili'),
        ('turk', 'Turk tili'),
        ('arab', 'Arab tili'),
    ]
    ielts_umumiy = models.ForeignKey(IELTSUmumiy, related_name='ielts_testlar', on_delete=models.CASCADE)
    nomi = models.CharField(max_length=255)
    til = models.CharField(max_length=20, choices=TIL_CHOYSLARI, default='ingliz')
    baho = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    sana = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.nomi} ({self.til})"

class IELTSMaterial(models.Model):
    ielts_umumiy = models.ForeignKey(IELTSUmumiy, related_name='ielts_materiallar', on_delete=models.CASCADE)
    nomi = models.CharField(max_length=255)
    fayl = models.FileField(upload_to='ielts_materiallar/')
    yuklangan_sana = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.nomi

class Universitet(models.Model):
    nomi = models.CharField(max_length=255)
    hudud = models.CharField(max_length=255)
    website = models.URLField(blank=True, null=True)
    yonalishlar = models.TextField(blank=True, null=True)
    kirish_ballari = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nomi

class Yutuq(models.Model):
    TUR_CHOYSLARI = [
        ('umumiy', 'Umumiy'),
        ('testlar', 'Testlar'),
        ('streak', 'Streak'),
        ('mock_testlar', 'Mock Testlar'),
    ]

    nomi = models.CharField(max_length=255)
    tavsif = models.TextField()
    tur = models.CharField(max_length=20, choices=TUR_CHOYSLARI, default='umumiy')
    ball = models.IntegerField(default=0)
    shart = models.TextField()
    rasm = models.ImageField(upload_to='yutuqlar/', blank=True, null=True)

    def __str__(self):
        return self.nomi

class FoydalanuvchiYutugi(models.Model):
    foydalanuvchi = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='foydalanuvchi_yutuqlari', on_delete=models.CASCADE)
    yutuq = models.ForeignKey(Yutuq, related_name='foydalanuvchilar', on_delete=models.CASCADE)
    olingan_sana = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.foydalanuvchi.full_name} - {self.yutuq.nomi}"

class Kurs(models.Model):
    nomi = models.CharField(max_length=255)
    tavsif = models.TextField()
    narx = models.DecimalField(max_digits=10, decimal_places=2)
    davomiyligi = models.CharField(max_length=50)
    oquvchi = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='kurslar', on_delete=models.CASCADE)

    def __str__(self):
        return self.nomi

class Jadval(models.Model):
    kun = models.CharField(max_length=20)
    fan = models.CharField(max_length=255)
    boshlanish_vaqti = models.TimeField()
    tugash_vaqti = models.TimeField()
    tur = models.CharField(max_length=50)
    oquvchi = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='jadval', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.kun} - {self.fan} ({self.boshlanish_vaqti} - {self.tugash_vaqti})"