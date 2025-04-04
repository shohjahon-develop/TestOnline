# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model, password_validation, authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import *

User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[password_validation.validate_password])
    agreetoterms = serializers.BooleanField(required=True, error_messages={
        'required': 'Shartlarga rozilik berish majburiy.',
        'invalid': 'Shartlarga rozilik true bo‘lishi kerak.'
    })
    fullName = serializers.CharField(source='full_name', required=True)
    phone = serializers.CharField(source='phone_number', required=True)
    birthDate = serializers.DateField(source='birth_date', required=False)
    school = serializers.CharField(source='study_place', required=False)

    class Meta:
        model = User
        fields = (
            'email', 'password', 'fullName', 'phone', 'birthDate', 'gender',
            'grade', 'region', 'school', 'role', 'agreetoterms'
        )
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate(self, data):
        if not data.get('agreetoterms'):
            raise serializers.ValidationError({"agreetoterms": "Ro‘yxatdan o‘tish uchun shartlarga rozilik berishingiz kerak."})
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
            birth_date=validated_data.get('birth_date', None),
            gender=validated_data.get('gender', None),
            grade=validated_data.get('grade', ''),
            region=validated_data.get('region', None),
            study_place=validated_data.get('study_place', None),
            address=validated_data.get('address', ''),
            role=validated_data.get('role', 'student'),
            agreetoterms=validated_data['agreetoterms']  # Modelga qo'shildi
        )
        return user

# Qolgan serializerlar o'zgarishsiz qoladi
class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email', None)
        password = data.get('password', None)

        if email and password:
            user = authenticate(email=email, password=password)
            if user:
                if user.is_active:
                    refresh = RefreshToken.for_user(user)
                    data['refresh'] = str(refresh)
                    data['access'] = str(refresh.access_token)
                    data['role'] = user.role
                else:
                    raise serializers.ValidationError("Foydalanuvchi faol emas")
            else:
                raise serializers.ValidationError("Noto'g'ri login yoki parol")
        else:
            raise serializers.ValidationError("Login va parol majburiy")

        return data

# Statistikalar uchun yangi serializer
class AdminStatisticsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_students = serializers.IntegerField()
    total_tests = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)

# So‘nggi ro‘yxatdan o‘tgan talabalar uchun serializer (allaqachon mavjud, biroz o‘zgartiramiz)
class LastRegisteredUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'full_name', 'phone_number', 'date_joined', 'is_active')

# Oxirgi testlar uchun serializer
class LatestTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('id', 'title', 'fan', 'qoshilgan_sana')

# Oxirgi to‘lovlar uchun serializer
class LatestPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tolov
        fields = ('id', 'tavsif', 'summa', 'sana', 'status')


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone_number', 'role', 'is_active')

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone_number', 'study_place', 'grade', 'address', 'role', 'is_active', 'is_staff', 'is_superuser')

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('full_name', 'phone_number', 'study_place', 'grade', 'address', 'role', 'is_active', 'is_staff', 'is_superuser')

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[password_validation.validate_password])

    class Meta:
        model = User
        fields = ('email', 'password', 'phone_number', 'full_name', 'study_place', 'grade', 'address', 'role')
        extra_kwargs = {
            'full_name': {'required': True},
            'phone_number': {'required': True},
            'email': {'required': True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
            study_place=validated_data.get('study_place', None),
            grade=validated_data.get('grade', ''),
            address=validated_data.get('address', ''),
            role=validated_data['role']
        )
        return user

class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('id', 'title', 'fan', 'savol_soni', 'qiyinlik', 'narx', 'mukofot', 'tavsif', 'vaqt_chegarasi', 'qoshilgan_sana', 'status')
        read_only_fields = ('id', 'qoshilgan_sana', 'user')

class TestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('title', 'fan', 'savol_soni', 'qiyinlik', 'narx', 'mukofot', 'tavsif', 'vaqt_chegarasi', 'status')

class TestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('title', 'fan', 'savol_soni', 'qiyinlik', 'narx', 'mukofot', 'tavsif', 'vaqt_chegarasi', 'status')

class SavolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Savol
        fields = ('id', 'test', 'savol_matni', 'qiyinlik', 'variant_a', 'variant_b', 'variant_c', 'variant_d', 'togri_javob')
        read_only_fields = ('id', 'test')

class SavolCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Savol
        fields = ('savol_matni', 'qiyinlik', 'variant_a', 'variant_b', 'variant_c', 'variant_d', 'togri_javob')

    def validate_test(self, value):
        if not Test.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError("Kiritilgan test mavjud emas.")
        return value

class SavolUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Savol
        fields = ('savol_matni', 'qiyinlik', 'variant_a', 'variant_b', 'variant_c', 'variant_d', 'togri_javob')

class OquvMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = OquvMaterial
        fields = ('id', 'fan', 'material_nomi', 'tur', 'format', 'hajm', 'yuklab_olish_imkoniyati', 'status', 'yuklangan_sana')
        read_only_fields = ('id', 'yuklangan_sana')

class OquvMaterialCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OquvMaterial
        fields = ('fan', 'material_nomi', 'tur', 'format', 'hajm', 'yuklab_olish_imkoniyati', 'status')

class OquvMaterialUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OquvMaterial
        fields = ('fan', 'material_nomi', 'tur', 'format', 'hajm', 'yuklab_olish_imkoniyati', 'status')

class TolovSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tolov
        fields = ('id', 'foydalanuvchi', 'tavsif', 'tur', 'summa', 'sana', 'status')
        read_only_fields = ('id', 'foydalanuvchi', 'sana')

class TolovCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tolov
        fields = ('tavsif', 'tur', 'summa')

class ReytingSerializer(serializers.ModelSerializer):
    foydalanuvchi_full_name = serializers.CharField(source='foydalanuvchi.full_name', read_only=True)

    class Meta:
        model = Reyting
        fields = ('id', 'foydalanuvchi', 'foydalanuvchi_full_name', 'umumiy_ball', 'testlar_ball', 'kurslar_ball', 'platforma_vaqti_ball', 'matematika_reyting', 'fizika_reyting', 'ingliz_tili_reyting')
        read_only_fields = ('id', 'foydalanuvchi', 'umumiy_ball')

class ReytingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reyting
        fields = ('testlar_ball', 'kurslar_ball', 'platforma_vaqti_ball', 'matematika_reyting', 'fizika_reyting', 'ingliz_tili_reyting')

    def validate(self, data):
        if any(value < 0 for value in data.values() if isinstance(value, int)):
            raise serializers.ValidationError("Ballar musbat bo'lishi kerak.")
        return data

class IELTSUmumiySerializer(serializers.ModelSerializer):
    class Meta:
        model = IELTSUmumiy
        fields = ('id', 'foydalanuvchi', 'joriy_baho', 'maqsad_baho', 'listening', 'reading', 'writing', 'speaking', 'keyingi_imtihon_sanasi', 'umumiy_progress')
        read_only_fields = ('id', 'foydalanuvchi')

class IELTSTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = IELTSTest
        fields = ('id', 'ielts_umumiy', 'nomi', 'til', 'baho', 'sana')
        read_only_fields = ('id', 'ielts_umumiy', 'sana')

class IELTSMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = IELTSMaterial
        fields = ('id', 'ielts_umumiy', 'nomi', 'fayl', 'yuklangan_sana')
        read_only_fields = ('id', 'ielts_umumiy', 'yuklangan_sana')

class IELTSUmumiyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IELTSUmumiy
        fields = ('joriy_baho', 'maqsad_baho', 'listening', 'reading', 'writing', 'speaking', 'keyingi_imtihon_sanasi', 'umumiy_progress')

class UniversitetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Universitet
        fields = ('id', 'nomi', 'hudud', 'website', 'yonalishlar', 'kirish_ballari')
        read_only_fields = ('id',)

class UniversitetCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Universitet
        fields = ('nomi', 'hudud', 'website', 'yonalishlar', 'kirish_ballari')

class UniversitetUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Universitet
        fields = ('nomi', 'hudud', 'website', 'yonalishlar', 'kirish_ballari')

class YutuqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Yutuq
        fields = ('id', 'nomi', 'tavsif', 'tur', 'ball', 'shart', 'rasm')
        read_only_fields = ('id',)

class YutuqCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Yutuq
        fields = ('nomi', 'tavsif', 'tur', 'ball', 'shart', 'rasm')

class YutuqUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Yutuq
        fields = ('nomi', 'tavsif', 'tur', 'ball', 'shart', 'rasm')

class FoydalanuvchiYutugiSerializer(serializers.ModelSerializer):
    yutuq_nomi = serializers.CharField(source='yutuq.nomi', read_only=True)
    class Meta:
        model = FoydalanuvchiYutugi
        fields = ('id', 'foydalanuvchi', 'yutuq', 'olingan_sana', 'yutuq_nomi')
        read_only_fields = ('id', 'foydalanuvchi', 'yutuq', 'olingan_sana')

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone_number', 'study_place', 'grade', 'address')
        read_only_fields = ('email',)

class TestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('id', 'title', 'fan', 'savol_soni', 'qiyinlik', 'qoshilgan_sana')

class TestDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('id', 'title', 'fan', 'savol_soni', 'qiyinlik', 'qoshilgan_sana', 'savollar')

class TestResultSerializer(serializers.Serializer):
    test_id = serializers.IntegerField()
    user_answers = serializers.JSONField()

class MockTestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('id', 'title', 'fan', 'savol_soni', 'qiyinlik', 'qoshilgan_sana')

class MockTestDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = '__all__'

class KursListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kurs
        fields = ('id', 'nomi', 'tavsif', 'narx', 'davomiyligi')

class KursDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kurs
        fields = ('id', 'nomi', 'tavsif', 'narx', 'davomiyligi')

class KursCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kurs
        fields = ('nomi', 'tavsif', 'narx', 'davomiyligi')

class KursUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kurs
        fields = ('nomi', 'tavsif', 'narx', 'davomiyligi')

class JadvalListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jadval
        fields = ('id', 'kun', 'fan', 'boshlanish_vaqti', 'tugash_vaqti', 'tur')

class JadvalDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jadval
        fields = ('id', 'kun', 'fan', 'boshlanish_vaqti', 'tugash_vaqti', 'tur')

class JadvalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jadval
        fields = ('kun', 'fan', 'boshlanish_vaqti', 'tugash_vaqti', 'tur')

class JadvalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jadval
        fields = ('kun', 'fan', 'boshlanish_vaqti', 'tugash_vaqti', 'tur')

class LastRegisteredUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'full_name', 'email', 'phone_number', 'role', 'date_joined')