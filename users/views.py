from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
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
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')
        user = authenticate(email=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            return Response({"error": "Noto'g'ri login yoki parol"}, status=status.HTTP_401_UNAUTHORIZED)



class DashboardView(generics.RetrieveAPIView):
    serializer_class = DashboardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


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
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    queryset = Reyting.objects.all()

class ReytingDetailView(generics.RetrieveAPIView):
    serializer_class = ReytingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Foydalanuvchi uchun o'z reytingini olish
        if self.request.user.is_staff:
            pk = self.kwargs['pk']
            try:
                return Reyting.objects.get(pk=pk)
            except Reyting.DoesNotExist:
                raise NotFound("Reyting topilmadi")

        queryset = self.get_queryset()
        try:
            return queryset.get(foydalanuvchi=self.request.user)
        except Reyting.DoesNotExist:
             #Reyting yo'q bo'lsa yangi reyting yaratish
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
































































