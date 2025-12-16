import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AlertMe.settings')

app = Celery('AlertMe')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-expired-timers': {
        'task': 'sos.tasks.check_expired_timers',
        'schedule': 60.0,  
    },
    'cleanup-old-locations': {
        'task': 'geolocation.tasks.cleanup_old_location_history',
        'schedule': crontab(hour=3, minute=0),  
    },
}