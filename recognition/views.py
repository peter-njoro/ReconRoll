from django.shortcuts import render, redirect
import face_recognition
from face_recognition import face_encodings
from .forms import PersonForm
from .face_utils import  encode_face
import io
import pickle
import os
from django.conf import settings




# Create your views here.

def index(request):
    context = {
        'title': 'FaceTrack lite App', 
        'message': 'Welcome to the Recognition App!'
        }
    return render(request, 'recognition/index.html', context)

def enroll_view(request):
    # to get multiple images for enrollment in json formart or CSV formart as python script needs to be written here for this.
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


def face_detection_page(request):
    return render(request, 'recognition/face_detection.html')

def load_known_faces():
    faces_dir = os.path.join(settings.BASE_DIR, 'recognition', 'uploads', 'faces')
    known_encodings = []
    known_names = []

    for filename in os.listdir(faces_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(faces_dir, filename)
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_encodings.append(encodings[0])
                known_names.append(os.path.splitext(filename)[0])

    return known_encodings, known_names

    # SHOW THE CARD IN THE WEB BROWSER, THE CAMERA LIVE FEED OPTION TO BE COMPLETELY OPTIONAl


def live_recognition_page(request):
    return render(request, 'recognition/live_recognition.html')



