from django.contrib import admin
from .models import *

# admin.py
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('full_name', 'email', 'phone_number')



@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'fan', 'savol_soni', 'qiyinlik', 'status', 'user')
    list_filter = ('fan', 'qiyinlik', 'status', 'user')
    search_fields = ('title', 'fan')

@admin.register(Savol)
class SavolAdmin(admin.ModelAdmin):
    list_display = ('savol_matni', 'test', 'qiyinlik', 'togri_javob')
    list_filter = ('test', 'qiyinlik')
    search_fields = ('savol_matni',)






@admin.register(OquvMaterial)
class OquvMaterialAdmin(admin.ModelAdmin):
    list_display = ('material_nomi', 'fan', 'tur', 'format', 'yuklab_olish_imkoniyati', 'status')
    list_filter = ('fan', 'tur', 'format', 'status')
    search_fields = ('material_nomi', 'fan')

@admin.register(IELTSUmumiy)
class IELTSUmumiyAdmin(admin.ModelAdmin):
    list_display = ('foydalanuvchi', 'joriy_baho', 'maqsad_baho')
    list_filter = ('foydalanuvchi',)
    search_fields = ('foydalanuvchi__full_name',)

@admin.register(IELTSTest)
class IELTSTestAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'ielts_umumiy', 'til', 'baho')
    list_filter = ('ielts_umumiy', 'til')
    search_fields = ('nomi',)

@admin.register(IELTSMaterial)
class IELTSMaterialAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'ielts_umumiy')
    list_filter = ('ielts_umumiy',)
    search_fields = ('nomi',)

@admin.register(Universitet)
class UniversitetAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'hudud')
    list_filter = ('hudud',)
    search_fields = ('nomi',)

@admin.register(Yutuq)
class YutuqAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'tur', 'ball')
    list_filter = ('tur',)
    search_fields = ('nomi',)

@admin.register(FoydalanuvchiYutugi)
class FoydalanuvchiYutugiAdmin(admin.ModelAdmin):
    list_display = ('foydalanuvchi', 'yutuq', 'olingan_sana')
    list_filter = ('foydalanuvchi', 'yutuq')
    raw_id_fields = ('foydalanuvchi', 'yutuq') # Qo'shildi


admin.site.register(Jadval)
admin.site.register(Kurs)





