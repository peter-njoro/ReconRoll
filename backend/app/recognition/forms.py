from django import forms
from .models import Person, Session, Roster

class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'identification_number',
            'date_of_birth',
            'status',
            'notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'identification_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# Backwards compatibility
StudentForm = PersonForm

class RosterForm(forms.ModelForm):
    """Form for creating and editing rosters"""
    people = forms.ModelMultipleChoiceField(
        queryset=Person.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        help_text='Select people to include in this roster'
    )

    class Meta:
        model = Roster
        fields = [
            'name',
            'description',
            'people'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Class A, Team 1'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            'name',
            'description',
            'roster',
            'session_type',
            'start_time',
            'end_time',
            'expected_count',
            'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'roster': forms.Select(attrs={'class': 'form-control'}),
            'session_type': forms.TextInput(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'expected_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
