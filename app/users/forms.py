from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'full_name', 'is_student', 'is_teacher')
        help_texts = {
            'username': None,
            'email': None,
            'full_name': None,
            'is_student': 'Are you a Student?',
            'is_teacher': 'Are you a teacher?',
        }

    # Override the password fields to remove Django's annoying help texts
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text="",  # <- empty string removes the default text
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text="",  # <- empty string removes the default text
    )


class CustomAuthenticationForm(AuthenticationForm):
    pass
