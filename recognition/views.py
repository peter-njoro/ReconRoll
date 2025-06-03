from django.shortcuts import render, redirect
from .forms import PersonForm
from .face_utils import  encode_face
import io
import pickle
from django.http import StreamingHttpResponse
import cv2
from .face_utils import detect_faces_from_frame




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

def gen_frames():
    cap = cv2.VideoCapture(0)

    while True:
        success, frame = cap.read()
        if not success:
            break

        faces = detect_faces_from_frame(frame)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        # Encode the frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        cap.release()

def face_detection_stream(request):
    return StreamingHttpResponse(gen_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

def face_detection_page(request):
    return render(request, 'recognition/face_detection.html')


