# notifications/management/commands/test_email.py
from django.core.management.base import BaseCommand
from notifications.email_service import EmailService


class Command(BaseCommand):
    help = 'Тест отправки email уведомлений'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='dendasakami@gmail.com',
            help='Email для отправки тестового сообщения'
        )

    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write(self.style.WARNING(f'📧 Отправка тестового email на {email}...'))
        
        email_service = EmailService()
        success = email_service.send_test_email(email)
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'✅ Email успешно отправлен!'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка отправки email'))