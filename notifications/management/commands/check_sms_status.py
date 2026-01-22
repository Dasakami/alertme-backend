from django.core.management.base import BaseCommand
from notifications.nikita_sms_service import NikitaSMSService


class Command(BaseCommand):
    help = 'Проверка статуса доставки SMS'

    def add_arguments(self, parser):
        parser.add_argument(
            'transaction_id',
            type=str,
            help='ID транзакции из отправки SMS'
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='Опционально: номер телефона для фильтрации'
        )

    def handle(self, *args, **options):
        transaction_id = options['transaction_id']
        phone = options.get('phone')
        
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(self.style.WARNING('📊 ПРОВЕРКА СТАТУСА SMS'))
        self.stdout.write(self.style.WARNING('='*60))
        
        self.stdout.write(f"\n🆔 Transaction ID: {transaction_id}")
        if phone:
            self.stdout.write(f"📱 Телефон: {phone}")
        
        # Создаём сервис
        sms_service = NikitaSMSService()
        
        if not sms_service.enabled:
            self.stdout.write(self.style.ERROR('\n❌ SMS сервис отключен!'))
            return
        
        # Получаем отчет
        self.stdout.write("\n📡 Запрос отчета о доставке...")
        result = sms_service.get_delivery_report(
            transaction_id=transaction_id,
            phone=phone
        )
        
        # Результат
        self.stdout.write('\n' + '='*60)
        if result['success']:
            self.stdout.write(self.style.SUCCESS('✅ ОТЧЕТ ПОЛУЧЕН'))
            self.stdout.write(f"\n📋 Отчет:\n{result['report']}")
        else:
            self.stdout.write(self.style.ERROR('❌ ОШИБКА ПОЛУЧЕНИЯ ОТЧЕТА'))
            self.stdout.write(f"\n🔴 Ошибка: {result.get('error', 'Unknown')}")
        
        self.stdout.write('='*60 + '\n')