from django.core.management.base import BaseCommand
from notifications.nikita_sms_service import NikitaSMSService


class Command(BaseCommand):
    help = 'Тестирование отправки SMS через Nikita API'

    def add_arguments(self, parser):
        parser.add_argument(
            'phone',
            type=str,
            help='Номер телефона (996XXXXXXXXX)'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Тестовая отправка (без тарификации)'
        )
        parser.add_argument(
            '--message',
            type=str,
            default='Тестовое сообщение из AlertMe! 🚨',
            help='Текст сообщения'
        )

    def handle(self, *args, **options):
        phone = options['phone']
        test_mode = options['test']
        message = options['message']
        
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(self.style.WARNING('📱 ТЕСТ SMS ЧЕРЕЗ NIKITA API'))
        self.stdout.write(self.style.WARNING('='*60))
        
        self.stdout.write(f"\n📞 Телефон: {phone}")
        self.stdout.write(f"📨 Сообщение: {message}")
        self.stdout.write(f"🧪 Тестовый режим: {'Да (не тарифицируется)' if test_mode else 'НЕТ (реальная отправка)'}\n")
        
        # Создаём сервис
        sms_service = NikitaSMSService()
        
        if not sms_service.enabled:
            self.stdout.write(self.style.ERROR('❌ SMS сервис отключен!'))
            self.stdout.write('Проверьте настройки NIKITA_SMS_LOGIN и NIKITA_SMS_PASSWORD в .env')
            return
        
        self.stdout.write(self.style.SUCCESS(f"✅ SMS сервис активен (отправитель: {sms_service.sender})"))
        
        # Подтверждение
        if not test_mode:
            confirm = input("\n⚠️  ВНИМАНИЕ: Это реальная отправка! Продолжить? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('❌ Отменено пользователем'))
                return
        
        # Отправка
        self.stdout.write("\n📤 Отправка SMS...")
        result = sms_service.send_sms(
            to_phone=phone,
            message=message,
            test=test_mode
        )
        
        # Результат
        self.stdout.write('\n' + '='*60)
        if result['success']:
            self.stdout.write(self.style.SUCCESS('✅ SMS ОТПРАВЛЕН УСПЕШНО!'))
            self.stdout.write(f"\n🆔 Transaction ID: {result['transaction_id']}")
            self.stdout.write(f"📱 Номер: {result['phone']}")
            
            if test_mode:
                self.stdout.write(self.style.WARNING('\n🧪 Это была тестовая отправка (не тарифицировано)'))
            else:
                self.stdout.write(self.style.SUCCESS('\n✅ Реальная отправка выполнена'))
            
            self.stdout.write(f"\n📋 Ответ сервера:\n{result.get('response', 'N/A')}")
            
            # Предложение проверить статус
            self.stdout.write('\n' + '-'*60)
            self.stdout.write('💡 Для проверки статуса доставки используйте:')
            self.stdout.write(f"   python manage.py check_sms_status {result['transaction_id']}")
        else:
            self.stdout.write(self.style.ERROR('❌ ОШИБКА ОТПРАВКИ SMS'))
            self.stdout.write(f"\n🔴 Ошибка: {result.get('error', 'Unknown')}")
            
            if 'phone' in result:
                self.stdout.write(f"📱 Номер: {result['phone']}")
        
        self.stdout.write('='*60 + '\n')