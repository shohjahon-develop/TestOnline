from django.db.models import Sum
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from .serializers import *

User = get_user_model()

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignupSerializer
    permission_classes = (permissions.AllowAny,)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({
            'refresh': serializer.validated_data['refresh'],
            'access': serializer.validated_data['access'],
            'role': serializer.validated_data['role']  # Foydalanuvchi rolini qo'shamiz
        })



class LastRegisteredUsersView(generics.ListAPIView):
    serializer_class = LastRegisteredUserSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        return User.objects.order_by('-date_joined')[:50]

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user



class AdminStatisticsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = AdminStatisticsSerializer

    def get(self, request, *args, **kwargs):
        total_users = User.objects.count()
        active_students = User.objects.filter(role='student', is_active=True).count()
        total_tests = Test.objects.count()
        total_revenue = Tolov.objects.filter(tur='kirim', status='muvaffaqiyatli').aggregate(Sum('summa'))['summa__sum'] or 0

        data = {
            'total_users': total_users,
            'active_students': active_students,
            'total_tests': total_tests,
            'total_revenue': total_revenue,
        }
        serializer = self.get_serializer(data)
        return Response(serializer.data)

# So‘nggi ro‘yxatdan o‘tgan talabalar (allaqachon mavjud, biroz o‘zgartiramiz)
class LastRegisteredUsersView(generics.ListAPIView):
    serializer_class = LastRegisteredUserSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        return User.objects.filter(role='student').order_by('-date_joined')[:30]

# Oxirgi yuklangan testlar uchun view
class LatestTestsView(generics.ListAPIView):
    serializer_class = LatestTestSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        return Test.objects.order_by('-qoshilgan_sana')[:10]

# Oxirgi to‘lovlar uchun view
class LatestPaymentsView(generics.ListAPIView):
    serializer_class = LatestPaymentSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        return Tolov.objects.order_by('-sana')[:20]


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class UserUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class UserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]




class TestCreateView(generics.CreateAPIView):
    queryset = Test.objects.all()
    serializer_class = TestCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TestUpdateView(generics.UpdateAPIView):
    queryset = Test.objects.all()
    serializer_class = TestUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]



class SavolListView(generics.ListAPIView):
    serializer_class = SavolSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        test_id = self.kwargs['test_id']
        try:
            test = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            raise NotFound("Test topilmadi")
        return Savol.objects.filter(test=test)

class SavolCreateView(generics.CreateAPIView):
    serializer_class = SavolCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def perform_create(self, serializer):
        test_id = self.kwargs['test_id']
        try:
            test = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            raise NotFound("Test topilmadi")
        serializer.save(test=test)

class SavolUpdateView(generics.UpdateAPIView):
    queryset = Savol.objects.all()
    serializer_class = SavolUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class SavolDeleteView(generics.DestroyAPIView):
    queryset = Savol.objects.all()
    serializer_class = SavolSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]




class OquvMaterialListView(generics.ListAPIView):
    queryset = OquvMaterial.objects.all()
    serializer_class = OquvMaterialSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class OquvMaterialDetailView(generics.RetrieveAPIView):
    queryset = OquvMaterial.objects.all()
    serializer_class = OquvMaterialSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class OquvMaterialCreateView(generics.CreateAPIView):
    queryset = OquvMaterial.objects.all()
    serializer_class = OquvMaterialCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class OquvMaterialUpdateView(generics.UpdateAPIView):
    queryset = OquvMaterial.objects.all()
    serializer_class = OquvMaterialUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class OquvMaterialDeleteView(generics.DestroyAPIView):
    queryset = OquvMaterial.objects.all()
    serializer_class = OquvMaterialSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]



class TolovListView(generics.ListAPIView):
    serializer_class = TolovSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    queryset = Tolov.objects.all()


class TolovCreateView(generics.CreateAPIView):
    serializer_class = TolovCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def perform_create(self, serializer):
        # Yangi to'lovni yaratgan adminni avtomatik ravishda foydalanuvchi sifatida belgilash
        serializer.save(foydalanuvchi=self.request.user)




class ReytingListView(generics.ListAPIView):
    serializer_class = ReytingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Reyting.objects.all()

class ReytingDetailView(generics.RetrieveAPIView):
    serializer_class = ReytingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        queryset = self.get_queryset()
        try:
            return queryset.get(foydalanuvchi=self.request.user)
        except Reyting.DoesNotExist:
            # Reyting yo'q bo'lsa yangi reyting yaratish
            reyting = Reyting.objects.create(foydalanuvchi=self.request.user)
            return reyting

    def get_queryset(self):
        return Reyting.objects.all()

class ReytingUpdateView(generics.UpdateAPIView):
    queryset = Reyting.objects.all()
    serializer_class = ReytingUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]




class IELTSUmumiyListView(generics.ListAPIView):
    queryset = IELTSUmumiy.objects.all()
    serializer_class = IELTSUmumiySerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class IELTSUmumiyDetailView(generics.RetrieveAPIView):
    queryset = IELTSUmumiy.objects.all()
    serializer_class = IELTSUmumiySerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class IELTSUmumiyUpdateView(generics.UpdateAPIView):
    queryset = IELTSUmumiy.objects.all()
    serializer_class = IELTSUmumiyUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class IELTSTestCreateView(generics.CreateAPIView):
    queryset = IELTSTest.objects.all()
    serializer_class = IELTSTestSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class IELTSTestDeleteView(generics.DestroyAPIView):
    queryset = IELTSTest.objects.all()
    serializer_class = IELTSTestSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class IELTSMaterialCreateView(generics.CreateAPIView):
    queryset = IELTSMaterial.objects.all()
    serializer_class = IELTSMaterialSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class IELTSMaterialDeleteView(generics.DestroyAPIView):
    queryset = IELTSMaterial.objects.all()
    serializer_class = IELTSMaterialSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]



class UniversitetListView(generics.ListAPIView):
    queryset = Universitet.objects.all()
    serializer_class = UniversitetSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class UniversitetDetailView(generics.RetrieveAPIView):
    queryset = Universitet.objects.all()
    serializer_class = UniversitetSerializer
    permission_classes = [permissions.IsAuthenticated] # Authenticated qilsa ham bo'ladi

class UniversitetCreateView(generics.CreateAPIView):
    queryset = Universitet.objects.all()
    serializer_class = UniversitetCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class UniversitetUpdateView(generics.UpdateAPIView):
    queryset = Universitet.objects.all()
    serializer_class = UniversitetUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class UniversitetDeleteView(generics.DestroyAPIView):
    queryset = Universitet.objects.all()
    serializer_class = UniversitetSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]



class YutuqListView(generics.ListAPIView):
    queryset = Yutuq.objects.all()
    serializer_class = YutuqSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class YutuqDetailView(generics.RetrieveAPIView):
    queryset = Yutuq.objects.all()
    serializer_class = YutuqSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class YutuqCreateView(generics.CreateAPIView):
    queryset = Yutuq.objects.all()
    serializer_class = YutuqCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class YutuqUpdateView(generics.UpdateAPIView):
    queryset = Yutuq.objects.all()
    serializer_class = YutuqUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class YutuqDeleteView(generics.DestroyAPIView):
    queryset = Yutuq.objects.all()
    serializer_class = YutuqSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]


class FoydalanuvchiYutugiListView(generics.ListAPIView):
    serializer_class = FoydalanuvchiYutugiSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Foydalanuvchi yutuqlarini olish (faqat o'ziniki)"""
        user = self.request.user
        return FoydalanuvchiYutugi.objects.filter(foydalanuvchi=user)






class TestListView(generics.ListAPIView):
    serializer_class = TestListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Test.objects.filter(user=self.request.user)

class TestDetailView(generics.RetrieveAPIView):
    serializer_class = TestDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Test.objects.all()

class TestSubmitView(generics.GenericAPIView):
    serializer_class = TestResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, test_id):
        try:
            test = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            return Response({"error": "Test topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user_answers = serializer.validated_data['user_answers']
            # Natijalarni hisoblash logikasi
            correct_answers = 0
            for question_id, answer in user_answers.items():
                try:
                    question = Savol.objects.get(pk=question_id, test=test)
                    if question.togri_javob == answer:
                        correct_answers += 1
                except Savol.DoesNotExist:
                    return Response({"error": f"{question_id} idli savol topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

            # Natijalarni saqlash
            request.user.tests.add(test, through_defaults={'score': correct_answers})

            return Response({"message": "Test muvaffaqiyatli topshirildi", "correct_answers": correct_answers}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)







class MockTestListView(generics.ListAPIView):
    serializer_class = MockTestListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Test.objects.filter(user=self.request.user, is_mock=True)

class MockTestDetailView(generics.RetrieveAPIView):
    queryset = Test.objects.all()
    serializer_class = MockTestDetailSerializer
    permission_classes = [permissions.IsAuthenticated]




class KursListView(generics.ListAPIView):
    queryset = Kurs.objects.all()
    serializer_class = KursListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Kurs.objects.filter(oquvchi=self.request.user)

class KursDetailView(generics.RetrieveAPIView):
    queryset = Kurs.objects.all()
    serializer_class = KursDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

class KursCreateView(generics.CreateAPIView):
    queryset = Kurs.objects.all()
    serializer_class = KursCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class KursUpdateView(generics.UpdateAPIView):
    queryset = Kurs.objects.all()
    serializer_class = KursUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class KursDeleteView(generics.DestroyAPIView):
    queryset = Kurs.objects.all()
    serializer_class = KursDetailSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]


class JadvalListView(generics.ListAPIView):
    serializer_class = JadvalListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Jadval.objects.filter(oquvchi=self.request.user)

class JadvalDetailView(generics.RetrieveAPIView):
    queryset = Jadval.objects.all()
    serializer_class = JadvalDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

class JadvalCreateView(generics.CreateAPIView):
    queryset = Jadval.objects.all()
    serializer_class = JadvalCreateSerializer
    permission_classes = [permissions.IsAuthenticated] # Agar o'quvchi yaratishga huquqi bo'lsa permissions.IsAdminUser olib tashlash kk

    def perform_create(self, serializer):
        serializer.save(oquvchi=self.request.user)

class JadvalUpdateView(generics.UpdateAPIView):
    queryset = Jadval.objects.all()
    serializer_class = JadvalUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser] #admin bo'lmasa olib tashlash kk

class JadvalDeleteView(generics.DestroyAPIView):
    queryset = Jadval.objects.all()
    serializer_class = JadvalDetailSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser] #admin bo'lmasa olib tashlash kk











































