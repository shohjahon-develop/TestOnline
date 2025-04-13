from django.utils import timezone
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta # pip install python-dateutil
import pytz # Timezone handling uchun

def get_date_ranges(period='month', tz_name='Asia/Tashkent'):
    """
    Tanlangan davr uchun joriy va oldingi davr boshlanish/tugash sanalarini qaytaradi.
    Sanalar timezone-aware qilib qaytariladi.
    """
    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.utc # Agar timezone noto'g'ri bo'lsa UTC ishlatiladi

    now_aware = timezone.now().astimezone(tz) # Joriy vaqtni belgilangan timezone ga o'tkazish
    today = now_aware.date()
    # Datetime uchun tugash vaqti (kun oxiri)
    end_current_dt = now_aware

    if period == 'week':
        # Joriy hafta (Dushanbadan boshlab)
        start_current = today - timedelta(days=today.weekday())
        # Oldingi hafta
        start_previous = start_current - timedelta(days=7)
        end_previous = start_current # Eksklyuziv tugash sanasi
    elif period == 'quarter':
        # Joriy chorak
        current_quarter = (today.month - 1) // 3 + 1
        first_month_current = (current_quarter - 1) * 3 + 1
        start_current = today.replace(month=first_month_current, day=1)
        # Oldingi chorak
        # Joriy chorakning birinchi kuni
        first_day_current_quarter = start_current
        # Oldingi chorakning oxirgi kuni = joriy chorak boshlanishidan 1 kun oldin
        last_day_prev_quarter = first_day_current_quarter - timedelta(days=1)
        # Oldingi chorakning birinchi kuni
        start_previous = last_day_prev_quarter.replace(day=1) - relativedelta(months=2)
        end_previous = start_current # Eksklyuziv tugash sanasi
    elif period == 'year':
        # Joriy yil
        start_current = today.replace(month=1, day=1)
        # Oldingi yil
        start_previous = start_current.replace(year=start_current.year - 1)
        end_previous = start_current # Eksklyuziv tugash sanasi
    else: # Default: 'month'
        # Joriy oy
        start_current = today.replace(day=1)
        # Oldingi oy
        start_previous = (start_current - relativedelta(months=1))
        end_previous = start_current # Eksklyuziv tugash sanasi

    # Vaqt zonasi bilan datetime obyektlarini yaratish
    start_current_dt = tz.localize(timezone.datetime.combine(start_current, timezone.datetime.min.time()))
    start_previous_dt = tz.localize(timezone.datetime.combine(start_previous, timezone.datetime.min.time()))
    # Oldingi davr tugashi uchun (eksklyuziv)
    end_previous_dt = tz.localize(timezone.datetime.combine(end_previous, timezone.datetime.min.time()))

    return start_current_dt, end_current_dt, start_previous_dt, end_previous_dt