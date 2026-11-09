from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from .models import (
    Artefacto,
    MetaMensual,
    Usuario,
)


MENSAJE_CREDENCIALES_INVALIDAS = 'Correo o contraseña incorrectos.'


class LoginAdminForm(AdminAuthenticationForm):
    """Conserva la política nativa sin diferenciar cuentas en los errores."""
    error_messages = {
        **AdminAuthenticationForm.error_messages,
        'invalid_login': MENSAJE_CREDENCIALES_INVALIDAS,
        'inactive': MENSAJE_CREDENCIALES_INVALIDAS,
    }

    def confirm_login_allowed(self, user):
        try:
            super().confirm_login_allowed(user)
        except ValidationError:
            # authenticate() puede aceptar la clave de alguien que no es staff.
            # El rechazo de Admin también debe contar como intento fallido.
            if self.request is not None:
                self.request._voltify_login_result = False
            raise


# Formulario para registrar nuevos usuarios
class RegistroUsuarioForm(forms.ModelForm):
    contrasena = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Ingresa tu contraseña',
                'autocomplete': 'new-password',
            }
        )
    )

    confirmar_contrasena = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Repite tu contraseña',
                'autocomplete': 'new-password',
            }
        )
    )

    class Meta:
        model = Usuario

        fields = [
            'nombre',
            'correo',
            'telefono',
            'comuna',
            'empresa',
        ]

        labels = {
            'nombre': 'Nombre completo',
            'correo': 'Correo electrónico',
            'telefono': 'Celular',
            'comuna': 'Comuna',
            'empresa': 'Empresa eléctrica',
        }

        widgets = {
            'nombre': forms.TextInput(
                attrs={
                    'placeholder': 'Ej. Camila Rojas',
                    'autocomplete': 'off',
                }
            ),

            'correo': forms.EmailInput(
                attrs={
                    'placeholder': 'tu@correo.com',
                    'autocomplete': 'off',
                }
            ),

            'telefono': forms.TextInput(
                attrs={
                    'placeholder': '+56 9 1234 5678',
                    'autocomplete': 'off',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Muestra opciones vacías claras en los campos de selección
        self.fields['comuna'].empty_label = (
            'Selecciona tu comuna'
        )

        self.fields['empresa'].empty_label = (
            'Selecciona tu empresa eléctrica'
        )

        self.fields['empresa'].required = True

    def clean(self):
        cleaned_data = super().clean()

        contrasena = cleaned_data.get(
            'contrasena'
        )

        confirmar_contrasena = cleaned_data.get(
            'confirmar_contrasena'
        )

        # Valida que ambas contraseñas coincidan
        if contrasena and confirmar_contrasena:
            if contrasena != confirmar_contrasena:
                self.add_error(
                    'confirmar_contrasena',
                    'Las contraseñas no coinciden.'
                )

        return cleaned_data


# Formulario para iniciar sesión
class LoginUsuarioForm(forms.Form):
    correo = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(
            attrs={
                'placeholder': 'tu@correo.com',
                'autocomplete': 'off',
            }
        )
    )

    contrasena = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Ingresa tu contraseña',
                'autocomplete': 'new-password',
            }
        )
    )


# Formulario para solicitar la recuperación de contraseña
class RecuperarContrasenaForm(forms.Form):
    correo = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(
            attrs={
                'placeholder': 'tu@correo.com',
                'autocomplete': 'off',
            }
        )
    )


# Formulario para verificar el código de recuperación
class VerificarCodigoForm(forms.Form):
    codigo = forms.CharField(
        label='Código de recuperación',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Ingresa el código de 6 dígitos',
                'inputmode': 'numeric',
                'autocomplete': 'one-time-code',
            }
        )
    )

    def clean_codigo(self):
        codigo = self.cleaned_data.get(
            'codigo'
        )

        # Valida que el código contenga solamente números
        if codigo and not codigo.isdigit():
            raise forms.ValidationError(
                'El código debe contener solo números.'
            )

        return codigo


# Formulario para definir una nueva contraseña
class NuevaContrasenaForm(forms.Form):
    nueva_contrasena = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Ingresa tu nueva contraseña',
                'autocomplete': 'new-password',
            }
        )
    )

    confirmar_contrasena = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Repite tu nueva contraseña',
                'autocomplete': 'new-password',
            }
        )
    )

    def clean(self):
        cleaned_data = super().clean()

        nueva_contrasena = cleaned_data.get(
            'nueva_contrasena'
        )

        confirmar_contrasena = cleaned_data.get(
            'confirmar_contrasena'
        )

        # Valida que la nueva contraseña y su confirmación coincidan
        if nueva_contrasena and confirmar_contrasena:
            if nueva_contrasena != confirmar_contrasena:
                self.add_error(
                    'confirmar_contrasena',
                    'Las contraseñas no coinciden.'
                )

        return cleaned_data


# Formulario para registrar y editar artefactos
class ArtefactoForm(forms.ModelForm):
    class Meta:
        model = Artefacto

        fields = [
            'nombre_artefacto',
            'categoria',
            'marca',
            'modelo',
            'potencia_nominal_w',
        ]

        labels = {
            'nombre_artefacto': 'Nombre del artefacto',
            'categoria': 'Categoría',
            'marca': 'Marca',
            'modelo': 'Modelo',
            'potencia_nominal_w': 'Potencia nominal (W)',
        }

        widgets = {
            'nombre_artefacto': forms.TextInput(
                attrs={
                    'placeholder': 'Ej. Televisor living',
                    'autocomplete': 'off',
                }
            ),

            'marca': forms.TextInput(
                attrs={
                    'placeholder': 'Ej. Samsung',
                    'autocomplete': 'off',
                }
            ),

            'modelo': forms.TextInput(
                attrs={
                    'placeholder': 'Ej. UN55CU7000',
                    'autocomplete': 'off',
                }
            ),

            'potencia_nominal_w': forms.NumberInput(
                attrs={
                    'placeholder': 'Ej. 120',
                    'min': '0.01',
                    'step': '0.01',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Obliga al usuario a seleccionar una categoría
        self.fields['categoria'].empty_label = (
            'Selecciona una categoría'
        )

        self.fields['categoria'].required = True


# Formulario para actualizar los datos y la tarifa del usuario
class ConfiguracionUsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario

        fields = [
            'nombre',
            'correo',
            'telefono',
            'comuna',
            'empresa',
            'usar_tarifa_manual',
            'valor_kwh_manual',
            'cargo_fijo_manual',
        ]

        labels = {
            'nombre': 'Nombre completo',
            'correo': 'Correo electrónico',
            'telefono': 'Celular',
            'comuna': 'Comuna',
            'empresa': 'Empresa eléctrica',

            'usar_tarifa_manual': (
                'Usar tarifa manual'
            ),

            'valor_kwh_manual': (
                'Precio variable de electricidad ($/kWh)'
            ),

            'cargo_fijo_manual': (
                'Cargo fijo mensual ($)'
            ),
        }

        widgets = {
            'nombre': forms.TextInput(
                attrs={
                    'placeholder': 'Ingresa tu nombre',
                    'autocomplete': 'off',
                }
            ),

            'correo': forms.EmailInput(
                attrs={
                    'placeholder': 'tu@correo.com',
                    'autocomplete': 'off',
                }
            ),

            'telefono': forms.TextInput(
                attrs={
                    'placeholder': '+56 9 1234 5678',
                    'autocomplete': 'off',
                }
            ),

            'usar_tarifa_manual': forms.CheckboxInput(),

            'valor_kwh_manual': forms.NumberInput(
                attrs={
                    'placeholder': 'Ej. 185',
                    'min': '0.01',
                    'step': '0.01',
                    'autocomplete': 'off',
                }
            ),

            'cargo_fijo_manual': forms.NumberInput(
                attrs={
                    'placeholder': 'Ej. 2200',
                    'min': '0',
                    'step': '0.01',
                    'autocomplete': 'off',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['comuna'].empty_label = (
            'Selecciona tu comuna'
        )

        self.fields['empresa'].empty_label = (
            'Selecciona tu empresa eléctrica'
        )

        self.fields['empresa'].required = True

        # Los valores manuales solo son obligatorios si se activa la tarifa manual
        self.fields[
            'usar_tarifa_manual'
        ].required = False

        self.fields[
            'valor_kwh_manual'
        ].required = False

        self.fields[
            'cargo_fijo_manual'
        ].required = False

    def clean(self):
        cleaned_data = super().clean()

        usar_tarifa_manual = cleaned_data.get(
            'usar_tarifa_manual'
        )

        valor_kwh_manual = cleaned_data.get(
            'valor_kwh_manual'
        )

        cargo_fijo_manual = cleaned_data.get(
            'cargo_fijo_manual'
        )

        # Valida los valores cuando el usuario activa la tarifa manual
        if usar_tarifa_manual:
            if valor_kwh_manual is None:
                self.add_error(
                    'valor_kwh_manual',
                    (
                        'Ingresa el precio variable '
                        'de electricidad por kWh.'
                    )
                )

            if cargo_fijo_manual is None:
                self.add_error(
                    'cargo_fijo_manual',
                    (
                        'Ingresa el cargo fijo mensual.'
                    )
                )

        return cleaned_data


# Formulario para crear o actualizar la meta mensual
class MetaMensualForm(forms.ModelForm):
    class Meta:
        model = MetaMensual

        fields = [
            'meta_consumo_kwh',
            'meta_costo_clp',
        ]

        labels = {
            'meta_consumo_kwh': (
                'Meta mensual de consumo (kWh)'
            ),

            'meta_costo_clp': (
                'Meta mensual de costo (CLP)'
            ),
        }

        widgets = {
            'meta_consumo_kwh': forms.NumberInput(
                attrs={
                    'placeholder': 'Ej. 150',
                    'min': '0.01',
                    'step': '0.01',
                    'autocomplete': 'off',
                }
            ),

            'meta_costo_clp': forms.NumberInput(
                attrs={
                    'placeholder': 'Ej. 30000',
                    'min': '1',
                    'step': '1',
                    'autocomplete': 'off',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Permite usar una meta de consumo, una meta de costo o ambas
        self.fields[
            'meta_consumo_kwh'
        ].required = False

        self.fields[
            'meta_costo_clp'
        ].required = False

    def clean(self):
        cleaned_data = super().clean()

        meta_consumo_kwh = cleaned_data.get(
            'meta_consumo_kwh'
        )

        meta_costo_clp = cleaned_data.get(
            'meta_costo_clp'
        )

        # Exige que al menos una de las dos metas tenga un valor
        if (
            meta_consumo_kwh is None
            and meta_costo_clp is None
        ):
            raise forms.ValidationError(
                (
                    'Debes ingresar al menos una meta '
                    'de consumo o de costo.'
                )
            )

        return cleaned_data
