from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile


class CustomRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    # user_type = forms.ChoiceField(
    #     choices=[("standard", "Standard"), ("admin", "Admin")]
    # )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["user_type", "token"]