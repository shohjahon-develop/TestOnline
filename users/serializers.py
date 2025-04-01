from rest_framework import serializers
from django.contrib.auth import get_user_model, password_validation

from users.models import *

User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[password_validation.validate_password])

    class Meta:
        model = User
        fields = ('email', 'password', 'phone_number', 'full_name', 'study_place', 'grade', 'address',  'role')
        extra_kwargs = {
            'full_name': {'required': True},
            'phone_number': {'required': True},
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


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)


class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone_number', 'study_place', 'grade', 'address')




class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone_number', 'role', 'is_active')

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone_number', 'study_place', 'grade', 'address',  'role', 'is_active', 'is_staff', 'is_superuser')


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('full_name', 'phone_number', 'study_place', 'grade', 'address',  'role', 'is_active', 'is_staff', 'is_superuser')


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
        fields = ('id', 'title', 'fan', 'savol_soni', 'qiyinlik', 'narx', 'mukofot', 'tavsif','vaqt_chegarasi', 'qoshilgan_sana', 'status')
        read_only_fields = ('id', 'qoshilgan_sana', 'user')

class TestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('title', 'fan', 'savol_soni', 'qiyinlik', 'narx', 'mukofot', 'tavsif','vaqt_chegarasi', 'status')

class TestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ('title', 'fan', 'savol_soni', 'qiyinlik', 'narx', 'mukofot', 'tavsif','vaqt_chegarasi', 'status')



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
        # Test obyekti mavjudligini tekshirish
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
        read_only_fields = ('id', 'foydalanuvchi', 'sana')  # foydalanuvchi va sanani o'zgartirib bo'lmaydi

class TolovCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tolov
        fields = ('tavsif', 'tur', 'summa')




class ReytingSerializer(serializers.ModelSerializer):
    foydalanuvchi_full_name = serializers.CharField(source='foydalanuvchi.full_name', read_only=True)

    class Meta:
        model = Reyting
        fields = ('id', 'foydalanuvchi', 'foydalanuvchi_full_name', 'umumiy_ball', 'testlar_ball', 'kurslar_ball', 'platforma_vaqti_ball')
        read_only_fields = ('id', 'foydalanuvchi', 'umumiy_ball')

class ReytingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reyting
        fields = ('testlar_ball', 'kurslar_ball', 'platforma_vaqti_ball')

    def validate(self, data):
        # Ballar musbat son ekanligini tekshirish
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















