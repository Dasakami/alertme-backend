from django.shortcuts import render
from django.views.decorators.http import require_http_methods


def base_temp(request):
    """Главная страница"""
    return render(request, 'base.html')


@require_http_methods(["GET"])
def account_deletion_view(request):
    """Страница удаления аккаунта"""
    return render(request, 'account_deletion.html')


@require_http_methods(["GET"])
def privacy_policy_view(request):
    """Политика конфиденциальности"""
    return render(request, 'privacy_policy.html')


def handler404(request, exception=None):
    """Обработчик ошибки 404"""
    return render(request, '404.html', status=404)


def handler500(request):
    """Обработчик ошибки 500"""
    return render(request, '500.html', status=500)


def handler403(request, exception=None):
    """Обработчик ошибки 403"""
    return render(request, '403.html', status=403)