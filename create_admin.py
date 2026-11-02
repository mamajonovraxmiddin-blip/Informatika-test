import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

if not username or not password:
    raise ValueError("Admin username yoki password sozlanmagan!")

user, created = User.objects.get_or_create(
    username=username,
    defaults={"email": email},
)

user.email = email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()

print("Admin muvaffaqiyatli yaratildi yoki yangilandi!")
