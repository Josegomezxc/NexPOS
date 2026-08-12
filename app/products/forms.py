"""Formularios para gestionar el catálogo del menú."""
from django import forms
from django.core.exceptions import ValidationError

from app.orders.validators import errores_monto, errores_nombre, normalizar_nombre

from .models import Category, Product, normalizar_nombre_catalogo


IMAGEN_EXTENSIONES = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
IMAGEN_MAX_MB = 5
PRECIO_MAX_INT = 8  # max_digits=10 en el modelo -> 8 enteros + 2 decimales


def _validar_nombre_unico(modelo, campo, nombre, pk_actual, tipo):
    """Rechaza nombres duplicados sin importar mayúsculas/minúsculas o
    espacios (el guardado normaliza, pero el mensaje debe ser amigable)."""
    nombre = ' '.join((nombre or '').split()).capitalize()
    qs = modelo.objects.filter(**{f'{campo}__iexact': nombre})
    if pk_actual:
        qs = qs.exclude(pk=pk_actual)
    if qs.exists():
        raise forms.ValidationError(
            f'Ya existe un {tipo} llamado "{nombre}".',
        )
    return nombre


class CategoryForm(forms.ModelForm):
    """Formulario de categorías.

    El campo `cate_orden` NO se pide: se asigna automáticamente en
    Category.save() (siguiente posición disponible).
    """

    class Meta:
        model = Category
        fields = ['cate_nombre', 'cate_descripcion', 'cate_icono', 'cate_color', 'cate_imagen', 'cate_active']
        widgets = {
            'cate_nombre': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': '80', 'data-validar': 'requerido',
            }),
            'cate_descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cate_icono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fas fa-hamburger', 'maxlength': '60'}),
            'cate_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'cate_imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control', 'accept': 'image/*',
                'data-validar': 'imagen',
                'data-validar-imagen-ext': 'jpg,jpeg,png,webp,gif',
                'data-validar-imagen-max': '5',
            }),
            'cate_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Los nombres con solo espacios deben llegar a clean_cate_nombre
        # (que los rechaza con el mensaje personalizado).
        self.fields['cate_nombre'].strip = False
        self.fields['cate_nombre'].error_messages['required'] = 'El nombre es obligatorio.'

    def clean_cate_nombre(self):
        nombre = self.cleaned_data.get('cate_nombre')
        errores = errores_nombre(nombre)
        if errores:
            raise forms.ValidationError(errores[0])
        pk = self.instance.pk if self.instance else None
        return _validar_nombre_unico(
            Category, 'cate_nombre', normalizar_nombre(nombre), pk, 'categoría',
        )

    def clean_cate_imagen(self):
        imagen = self.cleaned_data.get('cate_imagen')
        if not imagen:
            return imagen
        nombre = (imagen.name or '').lower()
        extension = nombre.rsplit('.', 1)[-1] if '.' in nombre else ''
        if extension not in IMAGEN_EXTENSIONES:
            raise ValidationError(
                f'Formato de imagen no permitido. Usá: {", ".join(sorted(IMAGEN_EXTENSIONES))}.'
            )
        if imagen.size > IMAGEN_MAX_MB * 1024 * 1024:
            raise ValidationError(f'La imagen supera el máximo de {IMAGEN_MAX_MB} MB.')
        return imagen


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['prod_nombre', 'prod_descripcion', 'prod_categoria', 'prod_precio', 'prod_imagen', 'prod_active']
        widgets = {
            'prod_nombre': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': '140', 'data-validar': 'requerido',
            }),
            'prod_descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                      'placeholder': 'Ej: Incluye carne, queso cheddar laminado, lechuga, tomate...'}),
            'prod_categoria': forms.Select(attrs={'class': 'form-control'}),
            'prod_precio': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
                'data-validar': 'numero',
                'data-validar-max-int': str(PRECIO_MAX_INT),
                'data-validar-max-dec': '2',
            }),
            'prod_imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control', 'accept': 'image/*',
                'data-validar': 'imagen',
                'data-validar-imagen-ext': 'jpg,jpeg,png,webp,gif',
                'data-validar-imagen-max': '5',
            }),
            'prod_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['prod_precio'].error_messages.update({
            'invalid': 'Ingresá un precio válido.',
            'max_digits': 'El precio no puede superar los 8 dígitos enteros.',
            'max_whole_digits': 'El precio no puede superar los 8 dígitos enteros.',
            'max_decimal_places': 'El precio no puede tener más de 2 decimales.',
        })

    def clean_prod_nombre(self):
        nombre = self.cleaned_data.get('prod_nombre')
        errores = errores_nombre(nombre)
        if errores:
            raise forms.ValidationError(errores[0])
        pk = self.instance.pk if self.instance else None
        return _validar_nombre_unico(
            Product, 'prod_nombre', normalizar_nombre(nombre), pk, 'producto',
        )

    def clean_prod_precio(self):
        precio = self.cleaned_data.get('prod_precio')
        errores = errores_monto(precio, max_int=PRECIO_MAX_INT)
        if errores:
            raise forms.ValidationError(errores[0])
        return precio

    def clean_prod_imagen(self):
        imagen = self.cleaned_data.get('prod_imagen')
        if not imagen:
            return imagen
        nombre = (imagen.name or '').lower()
        extension = nombre.rsplit('.', 1)[-1] if '.' in nombre else ''
        if extension not in IMAGEN_EXTENSIONES:
            raise ValidationError(
                f'Formato de imagen no permitido. Usá: {", ".join(sorted(IMAGEN_EXTENSIONES))}.'
            )
        if imagen.size > IMAGEN_MAX_MB * 1024 * 1024:
            raise ValidationError(f'La imagen supera el máximo de {IMAGEN_MAX_MB} MB.')
        return imagen