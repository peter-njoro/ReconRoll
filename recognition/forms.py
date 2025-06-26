from django import forms
from .models import Student

class PersonForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['full_name', 'face_encoding_path']

        

