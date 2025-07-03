from django import forms
from .models import Student

class StudentForm(forms.ModelForm):
    face_image = forms.ImageField(required=False)

    class Meta:
        model = Student
        fields = ['full_name', 'registration_number', 'email', 'course', 'year_of_study', 'face_image']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Full Name'}),
            'registration_number': forms.TextInput(attrs={'placeholder': 'Regustration Number'})
        }
        