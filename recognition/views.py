from django.shortcuts import render

# Create your views here.

def index(request):
    context = {
        'title': 'FaceTrack lite App', 
        'message': 'Welcome to the Recognition App!'
        }
    return render(request, 'recognition/index.html', context)
