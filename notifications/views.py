from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

from sos.models import SOSAlert


def media_preview(request, sos_id):
	"""Минимальная страница для просмотра/скачивания медиа SOS"""
	sos = get_object_or_404(SOSAlert, id=sos_id)

	audio_url = sos.audio_file.url if sos.audio_file else None
	video_url = sos.video_file.url if sos.video_file else None

	return render(request, 'notifications/media_preview.html', {
		'sos': sos,
		'audio_url': audio_url,
		'video_url': video_url,
	})
