from django.shortcuts import render, redirect
from .forms import PersonForm
from .face_utils import  encode_face
import io
import pickle




# Create your views here.

def index(request):
    context = {
        'title': 'FaceTrack lite App', 
        'message': 'Welcome to the Recognition App!'
        }
    return render(request, 'recognition/index.html', context)

def enroll_view(request):
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES)
        if form.is_valid():
            person = form.save(commit=False)
            image_path = request.FILES['image'].temporary_file_path() \
                if hasattr(request.FILES['image'], 'temporary_file_path') else None

            if not image_path:
                # use BytesIO to handle in-memory files
                img_bytes = request.FILES['image'].read()
                image_path = io.BytesIO(img_bytes)

            encoding = encode_face(image_path)

            if encoding is not None:
                person.encoding = pickle.dumps(encoding)
                person.save()
                return redirect('recognition:enroll_success')
            else:
                form.add_error(None, 'No face detected. Try another image.')

    else:
        form = PersonForm()

    context = {
        'form':form
    }
    return render(request, 'recognition/enroll.html', context)

def enroll_success(request):
    return render(request, 'recognition/enroll_success.html')
