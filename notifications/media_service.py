import logging
import os
from django.conf import settings
from django.core.files.storage import default_storage
from typing import Optional,  Tuple
import uuid

logger = logging.getLogger(__name__)

class MediaService:
    SUPPORTED_AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm']
    SUPPORTED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/x-msvideo']
    MAX_AUDIO_SIZE = 10 * 1024 * 1024  
    MAX_VIDEO_SIZE = 50 * 1024 * 1024  
    
    @staticmethod
    def save_media(
        file_obj,
        media_type: str, 
        sos_alert_id: int,
        user_id: int
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            if media_type not in ['audio', 'video']:
                return False, None, "Invalid media type"
            file_size = file_obj.size
            max_size = MediaService.MAX_AUDIO_SIZE if media_type == 'audio' else MediaService.MAX_VIDEO_SIZE
            
            if file_size > max_size:
                return False, None, f"File too large: {file_size / 1024 / 1024:.1f}MB"
            file_ext = os.path.splitext(file_obj.name)[1].lower()
            if not file_ext:
                file_ext = '.m4a' if media_type == 'audio' else '.mp4'
            
            unique_id = str(uuid.uuid4())[:8]
            filename = f"sos/{media_type}s/{user_id}/{sos_alert_id}_{unique_id}{file_ext}"
            path = default_storage.save(filename, file_obj)
            media_url = default_storage.url(path)
            
            logger.info(f" {media_type.upper()} сохранен: {path}")
            return True, media_url, None
            
        except Exception as e:
            logger.error(f" Ошибка сохранения медиа: {e}", exc_info=True)
            return False, None, str(e)
    
    @staticmethod
    def generate_media_link(
        sos_alert_id: int,
        request=None
    ) -> str:
        if request:
            base_url = request.build_absolute_uri('/')
        else:
            base_url = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'
            if not base_url.startswith('http'):
                base_url = f"https://{base_url}"
        
        media_link = f"{base_url}api/media/sos/{sos_alert_id}/"
        
        logger.info(f"📎 Ссылка на медиа: {media_link}")
        return media_link
    
    @staticmethod
    def create_media_token(
        sos_alert_id: int,
        user_id: int,
        expires_hours: int = 24
    ) -> str:
        from django.utils import timezone
        from datetime import timedelta
        from notifications.models import MediaAccessToken
        
        try:
            token = str(uuid.uuid4())
            
            MediaAccessToken.objects.create(
                token=token,
                sos_alert_id=sos_alert_id,
                user_id=user_id,
                expires_at=timezone.now() + timedelta(hours=expires_hours)
            )
            
            return token
        except Exception as e:
            logger.error(f" Ошибка создания токена: {e}")
            return ""
    
    @staticmethod
    def verify_access(token: str, sos_alert_id: int) -> bool:
        from django.utils import timezone
        from notifications.models import MediaAccessToken
        
        try:
            access = MediaAccessToken.objects.get(
                token=token,
                sos_alert_id=sos_alert_id,
                expires_at__gt=timezone.now()
            )
            return True
        except:
            return False
