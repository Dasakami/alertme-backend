from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from sos.models import SOSAlert


def media_preview(request, sos_id):
    sos = get_object_or_404(SOSAlert, id=sos_id)

    audio_url = None
    video_url = None
    
    if sos.audio_file:
        try:
            audio_url = sos.audio_file.url
        except:
            pass
    
    if sos.video_file:
        try:
            video_url = sos.video_file.url
        except:
            pass
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚨 SOS #{sos.id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .content {{
            padding: 40px;
        }}
        .info-card {{
            background: #f9fafb;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .info-item {{
            padding: 12px;
            background: white;
            border-radius: 8px;
            margin-bottom: 10px;
        }}
        .label {{
            font-weight: 600;
            color: #6b7280;
            margin-right: 10px;
        }}
        .media-section {{
            margin-top: 30px;
        }}
        .media-card {{
            background: #1f2937;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
        }}
        .media-card h3 {{
            color: white;
            margin-bottom: 20px;
        }}
        audio, video {{
            width: 100%;
            border-radius: 8px;
            margin-bottom: 15px;
        }}
        .download-btn {{
            display: inline-block;
            padding: 12px 24px;
            background: #0891b2;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
        }}
        .download-btn:hover {{
            background: #0e7490;
        }}
        .no-media {{
            text-align: center;
            padding: 60px 20px;
            color: #6b7280;
        }}
        .status-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }}
        .status-active {{
            background: #dc2626;
            color: white;
        }}
        .map-btn {{
            display: inline-block;
            padding: 12px 24px;
            background: #059669;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            margin-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="font-size: 64px; margin-bottom: 15px;">🚨</div>
            <h1>SOS Сигнал #{sos.id}</h1>
            <p>Экстренное оповещение</p>
        </div>

        <div class="content">
            <div class="info-card">
                <h2 style="margin-bottom: 15px;">📋 Информация</h2>
                
                <div class="info-item">
                    <span class="label">Пользователь:</span>
                    {sos.user.phone_number}
                </div>
                
                <div class="info-item">
                    <span class="label">Статус:</span>
                    <span class="status-badge status-{sos.status}">
                        {'🔴 Активен' if sos.status == 'active' else sos.status}
                    </span>
                </div>
                
                <div class="info-item">
                    <span class="label">Время:</span>
                    {sos.created_at.strftime('%d.%m.%Y %H:%M')}
                </div>
                
                {f'''
                <div class="info-item">
                    <span class="label">Адрес:</span>
                    {sos.address}
                </div>
                ''' if sos.address else ''}
                
                {f'''
                <div class="info-item">
                    <span class="label">Координаты:</span>
                    {sos.latitude}, {sos.longitude}
                </div>
                <div style="text-align: center;">
                    <a href="https://www.google.com/maps/search/?api=1&query={sos.latitude},{sos.longitude}" 
                       class="map-btn" target="_blank">
                        🗺️ Открыть на карте
                    </a>
                </div>
                ''' if sos.latitude and sos.longitude else ''}
            </div>

            <div class="media-section">
                {f'''
                <div class="media-card">
                    <h3>🎤 Аудиозапись</h3>
                    <audio controls preload="metadata">
                        <source src="{audio_url}" type="audio/aac">
                        <source src="{audio_url}" type="audio/mpeg">
                        Ваш браузер не поддерживает воспроизведение аудио.
                    </audio>
                    <a href="{audio_url}" download class="download-btn">
                        ⬇️ Скачать аудио
                    </a>
                </div>
                ''' if audio_url else ''}
                
                {f'''
                <div class="media-card">
                    <h3>🎬 Видеозапись</h3>
                    <video controls preload="metadata">
                        <source src="{video_url}" type="video/mp4">
                        <source src="{video_url}" type="video/webm">
                        Ваш браузер не поддерживает воспроизведение видео.
                    </video>
                    <a href="{video_url}" download class="download-btn">
                        ⬇️ Скачать видео
                    </a>
                </div>
                ''' if video_url else ''}
                
                {'''
                <div class="no-media">
                    <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.5;">📭</div>
                    <h3>Медиафайлы не загружены</h3>
                    <p>К этому SOS сигналу не прикреплены аудио или видео записи</p>
                </div>
                ''' if not audio_url and not video_url else ''}
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    return HttpResponse(html, content_type='text/html')
