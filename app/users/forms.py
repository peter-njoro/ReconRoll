from django import forms 
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'full_name', 'is_student', 'is_teacher')


class CustomAuthenticationForm(AuthenticationForm):
    pass
