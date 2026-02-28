import os
import django
import sys

def init_db():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    from django.contrib.auth import get_user_model
    from rest_framework.authtoken.models import Token

    User = get_user_model()

    try:
        print("Starting user initialization...", flush=True)

        # Superuser
        admin_user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com'})
        admin_user.set_password('admin123')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        if created:
            print("Superuser 'admin' created successfully.", flush=True)
        else:
            print("Superuser 'admin' already exists (password reset to default).", flush=True)

        Token.objects.get_or_create(user=admin_user)
        print("Token ensured for 'admin'.", flush=True)

        # Regular user
        regular_user, created = User.objects.get_or_create(username='user1', defaults={'email': 'user1@example.com'})
        regular_user.set_password('user123')
        regular_user.save()
        if created:
            print("User 'user1' created successfully.", flush=True)
        else:
            print("User 'user1' already exists (password reset to default).", flush=True)

        Token.objects.get_or_create(user=regular_user)
        print("Token ensured for 'user1'.", flush=True)

    except Exception as e:
        print(f"CRITICAL ERROR during user initialization: {e}", flush=True)
        sys.exit(1)

if __name__ == '__main__':
    init_db()
