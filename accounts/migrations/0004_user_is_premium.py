# Generated migration for is_premium field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_telegram_username_alter_user_phone_number_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_premium',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Is Premium'),
        ),
    ]
