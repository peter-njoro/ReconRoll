from django import forms
from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['full_name', 'registration_number', 'email', 'course', 'year_of_study']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Registration Number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'course': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Course'
            }),
            'year_of_study': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Year of Study',
                'min': 1
            }),
        }
        labels = {
            'full_name': 'Full Name',
            'registration_number': 'Registration Number',
            'email': 'Email',
            'course': 'Course',
            'year_of_study': 'Year of Study',
        }
