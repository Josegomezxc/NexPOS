"""Formularios de usuarios."""
from django import forms
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse

from .models import Profile


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Usuario',
            'autofocus': True,
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Contraseña',
        })


class EmpleadoCreateForm(forms.Form):
    """Formulario de alta de usuario por parte del administrador."""

    username = forms.CharField(
        label='Nombre de Usuario',
        min_length=3,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario',
            'autocomplete': 'off',
            'data-validar': 'requerido usuario',
        }),
    )
    password = forms.CharField(
        label='Contraseña',
        min_length=8,
        widget=forms.PasswordInput(render_value=True, attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres',
            'autocomplete': 'new-password',
            'data-validar': 'requerido password',
        }),
        help_text='Mínimo 8 caracteres. No uses solo números.',
    )
    first_name = forms.CharField(
        label='Nombre',
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
    )
    last_name = forms.CharField(
        label='Apellido',
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
    )
    email = forms.EmailField(
        label='Correo Electrónico',
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
    )
    perf_rol = forms.ChoiceField(
        choices=[
            (Profile.ROL_EMPLEADO, 'Empleado'),
            (Profile.ROL_ADMIN, 'Administrador'),
        ],
        initial=Profile.ROL_EMPLEADO,
        label='Rol',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['data-validar-disponible'] = \
            reverse('users:verificar_usuario')

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Ese nombre de usuario ya está en uso.')
        reserved = ['owner', 'superowner', 'root', 'admin', 'administrator']
        if username.lower() in reserved:
            raise ValidationError('Ese nombre de usuario está reservado.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if password.isdigit():
            raise ValidationError('La contraseña no puede ser solo números.')
        return password

    def save(self):
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        perf_rol = self.cleaned_data['perf_rol']

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
            email=self.cleaned_data.get('email', ''),
        )
        profile = user.profile
        profile.perf_rol = perf_rol
        profile.save()
        return user


class EmpleadoEditForm(forms.ModelForm):
    """Formulario de edición de usuario por parte del administrador."""

    password = forms.CharField(
        label='Cambiar contraseña',
        required=False,
        min_length=8,
        widget=forms.PasswordInput(render_value=True, attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña',
            'autocomplete': 'new-password',
        }),
        help_text='Toca el ojito para ver la contraseña que escribas. Dejá en blanco si no querés cambiarla.',
    )
    perf_rol = forms.ChoiceField(
        choices=[
            (Profile.ROL_EMPLEADO, 'Empleado'),
            (Profile.ROL_ADMIN, 'Administrador'),
        ],
        label='Rol',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '150', 'data-validar': 'requerido usuario'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '150'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '150'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'username': 'Nombre de Usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Email',
            'is_active': 'Cuenta activa',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            profile = getattr(self.instance, 'profile', None)
            if profile:
                self.fields['perf_rol'].initial = profile.perf_rol

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        qs = User.objects.exclude(pk=self.instance.pk).filter(username__iexact=username)
        if qs.exists():
            raise ValidationError('Ese nombre de usuario ya está en uso por otro empleado.')
        reserved = ['owner', 'superowner', 'root', 'admin', 'administrator']
        if username.lower() in reserved and self.instance.username.lower() not in reserved:
            raise ValidationError('Ese nombre de usuario está reservado.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '').strip()
        if password:
            if len(password) < 8:
                raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
            if password.isdigit():
                raise ValidationError('La contraseña no puede ser solo números.')
            return password
        return ''

    def save(self, commit=True):
        user = super().save(commit=commit)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
            user.save()
        profile = user.profile
        profile.perf_rol = self.cleaned_data['perf_rol']
        profile.perf_active = user.is_active
        if commit:
            profile.save()
        return user


class PerfilForm(forms.ModelForm):
    """Formulario para la autoedición del perfil propio (incluye usuario y cambio opcional de contraseña)."""

    password = forms.CharField(
        label='Cambiar contraseña',
        required=False,
        min_length=8,
        widget=forms.PasswordInput(render_value=True, attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña',
            'autocomplete': 'new-password',
        }),
        help_text='Toca el ojito para ver la contraseña que escribas. Dejá en blanco si no querés cambiarla.',
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': '150', 'data-validar': 'requerido usuario',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': '150',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': '150',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 'data-validar': 'email',
            }),
        }
        labels = {
            'username': 'Nombre de Usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo Electrónico',
        }

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        qs = User.objects.exclude(pk=self.instance.pk).filter(username__iexact=username)
        if qs.exists():
            raise ValidationError('Ese nombre de usuario ya pertenece a otra cuenta.')
        reserved = ['owner', 'superowner', 'root', 'admin', 'administrator']
        if username.lower() in reserved and self.instance.username.lower() not in reserved:
            raise ValidationError('Ese nombre de usuario está reservado.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '').strip()
        if password:
            if len(password) < 8:
                raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
            if password.isdigit():
                raise ValidationError('La contraseña no puede ser solo números.')
            return password
        return ''

    def save(self, commit=True):
        user = super().save(commit=commit)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
            user.save()
        return user
