from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name')
        help_texts = {
            'email': None,
            'username': None,
            'first_name': None,
            'last_name': None,
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
