from django import forms
from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['full_name', 'registration_number', 'email', 'course', 'year_of_study']
