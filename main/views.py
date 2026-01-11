from django.shortcuts import render, get_object_or_404

def base_temp(request):
    return render(request, 'test.html')