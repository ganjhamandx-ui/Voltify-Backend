from datetime import date, datetime, timedelta
from functools import wraps
import secrets

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login as auth_login,
    logout as auth_logout,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .forms import (
    ArtefactoForm,
    RegistroUsuarioForm,
    LoginUsuarioForm,
    RecuperarContrasenaForm,
    VerificarCodigoForm,
    NuevaContrasenaForm,
    ConfiguracionUsuarioForm,
    MetaMensualForm,
)

from .models import (
    Alerta,
    Artefacto,
    Consumo,
    MetaMensual,
    RecuperacionContrasena,
    Tarifa,
    Usuario,
)


# Los consumos historicos se conservan aunque el artefacto sea eliminado

COOKIE_PERIODO_DASHBOARD = 'voltify_periodo_dashboard'
PERIODOS_DASHBOARD_VALIDOS = {'day', 'week', 'month', '3months'}


# Exige autenticación nativa y comprueba que la sesión corresponda al perfil Voltify
def usuario_voltify_requerido(view_func):
    @login_required(
        login_url='/iniciar-sesion/'
    )
    @wraps(view_func)
    def wrapper(
        request,
        *args,
        **kwargs
    ):
        usuario_id = request.session.get(
            'usuario_id'
        )

        # Un administrador de Django no utiliza el panel privado del usuario final
        if not usuario_id:
            if request.user.is_staff:
                return redirect(
                    '/admin/'
                )

            auth_logout(request)

            return redirect(
                '/iniciar-sesion/'
            )

        try:
            usuario = Usuario.objects.only(
                'id_usuario',
                'correo'
            ).get(
                id_usuario=usuario_id
            )

        except Usuario.DoesNotExist:
            auth_logout(request)

            return redirect(
                '/iniciar-sesion/'
            )

        # Evita que una sesión válida pueda apuntar al perfil de otro usuario
        if (
            request.user.username.lower()
            !=
            usuario.correo.lower()
        ):
            auth_logout(request)

            return redirect(
                '/iniciar-sesion/'
            )

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


# Obtiene la tarifa manual o local configurada para el usuario
def obtener_tarifa_usuario(usuario):
    tarifa_info = {
        'disponible': False,
        'fuente': 'sin_configurar',
        'valor_kwh': None,
        'cargo_fijo_mensual': None,
        'tarifa_id': None,
        'empresa': (
            usuario.empresa.nombre_empresa
            if usuario.empresa
            else ''
        ),
        'comuna': (
            usuario.comuna.nombre_comuna
            if usuario.comuna
            else ''
        ),
    }

    # Usa la tarifa manual cuando el usuario la tiene activada
    if usuario.usar_tarifa_manual:
        if (
            usuario.valor_kwh_manual is not None
            and usuario.cargo_fijo_manual is not None
        ):
            tarifa_info['disponible'] = True
            tarifa_info['fuente'] = 'manual'
            tarifa_info['valor_kwh'] = usuario.valor_kwh_manual
            tarifa_info['cargo_fijo_mensual'] = usuario.cargo_fijo_manual

        return tarifa_info

    if not usuario.comuna_id or not usuario.empresa_id:
        return tarifa_info

    hoy = timezone.localdate()

    # Busca la tarifa local vigente según empresa y comuna
    tarifas = (
        Tarifa.objects.filter(
            empresa=usuario.empresa,
            comuna=usuario.comuna,
            fecha_inicio__lte=hoy
        )
        .order_by('-fecha_inicio')
    )

    for tarifa in tarifas:
        if tarifa.fecha_fin is None or tarifa.fecha_fin >= hoy:
            tarifa_info['disponible'] = True
            tarifa_info['fuente'] = 'automatica_local'
            tarifa_info['valor_kwh'] = tarifa.valor_kwh
            tarifa_info['cargo_fijo_mensual'] = tarifa.cargo_fijo_mensual
            tarifa_info['tarifa_id'] = tarifa.id_tarifa
            break

    return tarifa_info



# Prepara los datos principales que utiliza el dashboard
@never_cache
@usuario_voltify_requerido
def inicio(request):
    usuario_id = request.session.get('usuario_id')

    periodo_dashboard = request.COOKIES.get(
        COOKIE_PERIODO_DASHBOARD,
        'day'
    )

    if periodo_dashboard not in PERIODOS_DASHBOARD_VALIDOS:
        periodo_dashboard = 'day'

    dashboard_data = {
        'artefactos': [],
        'consumos': [],
        'tarifa': {
            'disponible': False,
            'fuente': 'sin_configurar',
            'valor_kwh': None,
            'cargo_fijo_mensual': None,
            'empresa': '',
            'comuna': '',
        },
        'meta': {
            'disponible': False,
            'meta_consumo_kwh': None,
            'meta_costo_clp': None,
            'mes': None,
            'anio': None,
        },
    }

    if usuario_id:
        try:
            usuario = Usuario.objects.get(
                id_usuario=usuario_id
            )

        except Usuario.DoesNotExist:
            request.session.pop(
                'usuario_id',
                None
            )

            request.session.pop(
                'usuario_nombre',
                None
            )

        else:
            # Obtiene la informacion tarifaria del usuario para el dashboard

            tarifa_info = obtener_tarifa_usuario(
                usuario
            )

            dashboard_data['tarifa'] = {
                'disponible': tarifa_info['disponible'],
                'fuente': tarifa_info['fuente'],
                'valor_kwh': (
                    float(tarifa_info['valor_kwh'])
                    if tarifa_info['valor_kwh'] is not None
                    else None
                ),
                'cargo_fijo_mensual': (
                    float(
                        tarifa_info[
                            'cargo_fijo_mensual'
                        ]
                    )
                    if tarifa_info[
                        'cargo_fijo_mensual'
                    ] is not None
                    else None
                ),
                'empresa': tarifa_info['empresa'],
                'comuna': tarifa_info['comuna'],
            }

            hoy = timezone.localdate()

            # Obtiene la meta correspondiente al mes actual
            meta_actual = (
                MetaMensual.objects.filter(
                    usuario=usuario,
                    mes=hoy.month,
                    anio=hoy.year
                )
                .first()
            )

            if meta_actual:
                dashboard_data['meta'] = {
                    'disponible': True,
                    'meta_consumo_kwh': (
                        float(
                            meta_actual.meta_consumo_kwh
                        )
                        if (
                            meta_actual.meta_consumo_kwh
                            is not None
                        )
                        else None
                    ),
                    'meta_costo_clp': (
                        float(
                            meta_actual.meta_costo_clp
                        )
                        if (
                            meta_actual.meta_costo_clp
                            is not None
                        )
                        else None
                    ),
                    'mes': meta_actual.mes,
                    'anio': meta_actual.anio,
                }

            # Obtiene solamente los artefactos activos del usuario
            artefactos = (
                Artefacto.objects.filter(
                    usuario=usuario,
                    activo=True
                )
                .select_related(
                    'categoria'
                )
                .order_by(
                    'nombre_artefacto'
                )
            )

            # Obtiene el historial de consumos asociado al usuario
            consumos = (
                Consumo.objects.filter(
                    usuario=usuario
                )
                .select_related(
                    'artefacto'
                )
                .order_by(
                    'fecha'
                )
            )

            dashboard_data['artefactos'] = [
                {
                    'id': artefacto.id_artefacto,
                    'nombre': artefacto.nombre_artefacto,
                    'categoria': (
                        artefacto.categoria.nombre_categoria
                        if artefacto.categoria
                        else 'Otros'
                    ),
                    'marca': artefacto.marca or '',
                    'modelo': artefacto.modelo or '',
                    'potencia_nominal_w': (
                        float(
                            artefacto.potencia_nominal_w
                        )
                        if (
                            artefacto.potencia_nominal_w
                            is not None
                        )
                        else None
                    ),
                    'monitoreando': artefacto.monitoreando,
                }
                for artefacto in artefactos
            ]

            dashboard_data['consumos'] = []

            for consumo in consumos:
                fecha_consumo = consumo.fecha

                if timezone.is_aware(
                    fecha_consumo
                ):
                    fecha_consumo = timezone.localtime(
                        fecha_consumo
                    )

                dashboard_data[
                    'consumos'
                ].append(
                    {
                        'id': consumo.id_consumo,
                        'artefacto_id': (
                            consumo.artefacto_id_historico
                        ),
                        'artefacto': (
                            consumo.artefacto_nombre
                            or 'Artefacto eliminado'
                        ),
                        'categoria': (
                            consumo.categoria_nombre
                            or 'Otros'
                        ),
                        'consumo_kwh': float(
                            consumo.consumo_kwh
                        ),
                        'fecha': fecha_consumo.isoformat(),
                    }
                )

    data = {
        'dashboard_data': dashboard_data,
        'periodo_dashboard': periodo_dashboard,
        'activa': 'dashboard',
    }

    return render(
        request,
        'index.html',
        data
    )


# Guarda en una cookie la preferencia de periodo del dashboard
@never_cache
@usuario_voltify_requerido
@require_POST
def guardar_preferencia_dashboard(request):
    periodo = request.POST.get(
        'periodo',
        ''
    ).strip()

    if periodo not in PERIODOS_DASHBOARD_VALIDOS:
        return JsonResponse(
            {
                'ok': False,
                'error': 'Periodo de dashboard no valido.',
            },
            status=400
        )

    response = JsonResponse(
        {
            'ok': True,
            'periodo': periodo,
        }
    )

    response.set_cookie(
        COOKIE_PERIODO_DASHBOARD,
        periodo,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite='Lax',
        secure=request.is_secure(),
        path='/'
    )

    return response


# Registra un usuario nuevo y guarda su contraseña de forma segura
@never_cache
def registrar_usuario(request):
    if request.user.is_authenticated:
        if request.session.get('usuario_id'):
            return redirect('/')

        if request.user.is_staff:
            return redirect('/admin/')

        auth_logout(request)

    if request.method == 'POST':
        form = RegistroUsuarioForm(
            request.POST
        )

        # Valida los datos antes de crear ambos registros de usuario
        if form.is_valid():
            correo = (
                form.cleaned_data[
                    'correo'
                ]
                .strip()
                .lower()
            )

            contrasena = form.cleaned_data[
                'contrasena'
            ]

            User = get_user_model()

            # Evita duplicar el correo dentro del sistema nativo de Django
            if User.objects.filter(
                username__iexact=correo
            ).exists():
                form.add_error(
                    'correo',
                    'Ya existe una cuenta registrada con este correo.'
                )

            else:
                usuario_django_temporal = User(
                    username=correo,
                    email=correo
                )

                try:
                    # Aplica los validadores de contraseña configurados por Django
                    validate_password(
                        contrasena,
                        user=usuario_django_temporal
                    )

                except ValidationError as errores:
                    for error in errores.messages:
                        form.add_error(
                            'contrasena',
                            error
                        )

                else:
                    # Genera un único hash compatible con Django para ambos registros
                    contrasena_hash = make_password(
                        contrasena
                    )

                    # Crea Usuario y auth_user como una sola operación
                    with transaction.atomic():
                        usuario = form.save(
                            commit=False
                        )

                        usuario.correo = correo
                        usuario.contrasena_hash = (
                            contrasena_hash
                        )
                        usuario.fecha_registro = date.today()
                        usuario.save()

                        usuario_django = User(
                            username=correo,
                            email=correo,
                            is_active=True,
                            is_staff=False,
                            is_superuser=False,
                        )

                        usuario_django.password = (
                            contrasena_hash
                        )

                        usuario_django.save()

                    messages.success(
                        request,
                        'Cuenta creada correctamente. Ya puedes iniciar sesión.'
                    )

                    return redirect(
                        '/iniciar-sesion/'
                    )

    else:
        form = RegistroUsuarioForm()

    data = {
        'form': form
    }

    return render(
        request,
        'registrar_usuario.html',
        data
    )


# Autentica al usuario mediante el sistema nativo de Django
@never_cache
def iniciar_sesion(request):
    if request.user.is_authenticated:
        if request.session.get(
            'usuario_id'
        ):
            return redirect('/')

        if request.user.is_staff:
            return redirect('/admin/')

        auth_logout(request)

    if request.method == 'POST':
        form = LoginUsuarioForm(
            request.POST
        )

        # Procesa las credenciales solamente si el formulario es válido
        if form.is_valid():
            # Resultado explícito para el limitador, independiente del HTTP.
            request._voltify_login_result = False
            correo = (
                form.cleaned_data[
                    'correo'
                ]
                .strip()
                .lower()
            )

            contrasena = form.cleaned_data[
                'contrasena'
            ]

            try:
                # Obtiene el perfil de Voltify usando ORM, sin SQL construido manualmente
                usuario = Usuario.objects.get(
                    correo__iexact=correo
                )

            except Usuario.DoesNotExist:
                make_password(contrasena)
                form.add_error(
                    None,
                    'Correo o contraseña incorrectos.'
                )

            else:
                User = get_user_model()

                # Compatibilidad con cuentas creadas antes de integrar auth_user
                usuario_django = (
                    User.objects.filter(
                        username__iexact=usuario.correo
                    )
                    .first()
                )

                if usuario_django is None and not check_password(contrasena, usuario.contrasena_hash):
                    form.add_error(None, 'Correo o contraseña incorrectos.')
                    return render(request, 'iniciar_sesion.html', {'form': form})

                if usuario_django is None:
                    usuario_django = User(
                        username=usuario.correo.lower(),
                        email=usuario.correo.lower(),
                        is_active=True,
                        is_staff=False,
                        is_superuser=False,
                    )

                    usuario_django.password = (
                        usuario.contrasena_hash
                    )

                    usuario_django.save()

                # Django valida el hash y el estado de la cuenta mediante su backend
                usuario_autenticado = authenticate(
                    request,
                    username=usuario_django.username,
                    password=contrasena
                )

                if usuario_autenticado is not None:
                    # login() crea el estado de autenticación nativo y rota la sesión
                    auth_login(
                        request,
                        usuario_autenticado
                    )


                    # Mantiene la relación con el modelo de dominio de Voltify
                    request.session[
                        'usuario_id'
                    ] = usuario.id_usuario

                    request.session[
                        'usuario_nombre'
                    ] = usuario.nombre

                    return redirect('/')

                form.add_error(
                    None,
                    'Correo o contraseña incorrectos.'
                )

    else:
        form = LoginUsuarioForm()

    data = {
        'form': form
    }

    return render(
        request,
        'iniciar_sesion.html',
        data
    )


# Cierra la autenticación nativa y elimina los datos de la sesión
@never_cache
@login_required(
    login_url='/iniciar-sesion/'
)
def cerrar_sesion(request):
    # logout() elimina la autenticación y limpia la sesión completa
    auth_logout(request)

    return redirect(
        '/iniciar-sesion/'
    )


# Genera y envía un código temporal para recuperar la contraseña
@never_cache
def recuperar_contrasena(request):
    if request.method == 'POST':
        form = RecuperarContrasenaForm(
            request.POST
        )

        if form.is_valid():
            request._voltify_recovery_attempt = True
            request.session.pop('recuperacion_verificada', None)
            correo = form.cleaned_data[
                'correo'
            ]

            try:
                usuario = Usuario.objects.get(
                    correo__iexact=correo
                )

            except Usuario.DoesNotExist:
                # Misma navegación y coste de hash sin confirmar si existe la cuenta.
                make_password(secrets.token_hex(16))
                request.session['recuperacion_id'] = -1
                return redirect('/verificar-codigo/')

            else:
                # Invalida códigos de recuperación anteriores que sigan pendientes
                (
                    RecuperacionContrasena
                    .objects
                    .filter(
                        usuario=usuario,
                        utilizado=False
                    )
                    .update(
                        utilizado=True
                    )
                )

                # Genera un código numérico de seis dígitos
                codigo = str(
                    secrets.randbelow(
                        1000000
                    )
                ).zfill(6)

                fecha_solicitud = timezone.now()

                fecha_expiracion = (
                    fecha_solicitud
                    +
                    timedelta(
                        minutes=10
                    )
                )

                # Guarda el código como hash y define una vigencia de 10 minutos
                recuperacion = (
                    RecuperacionContrasena
                    .objects
                    .create(
                        usuario=usuario,
                        canal='correo',
                        token_hash=make_password(
                            codigo
                        ),
                        fecha_solicitud=fecha_solicitud,
                        fecha_expiracion=fecha_expiracion,
                        utilizado=False,
                    )
                )

                request.session[
                    'recuperacion_id'
                ] = recuperacion.id_recuperacion

                request.session.pop(
                    'recuperacion_verificada',
                    None
                )

                # Envía el código de recuperación al correo del usuario
                send_mail(
                    subject=(
                        'Código de recuperación '
                        'Voltify'
                    ),
                    message=(
                        'Tu código de recuperación '
                        f'es: {codigo}\n\n'
                        'El código tiene una '
                        'vigencia de 10 minutos.'
                    ),
                    from_email='no-reply@voltify.cl',
                    recipient_list=[
                        usuario.correo
                    ],
                    fail_silently=False,
                )

                return redirect(
                    '/verificar-codigo/'
                )

    else:
        form = RecuperarContrasenaForm()

    data = {
        'form': form
    }

    return render(
        request,
        'recuperar_contrasena.html',
        data
    )


# Verifica que el código de recuperación exista, no esté usado y siga vigente
@never_cache
def verificar_codigo(request):
    recuperacion_id = request.session.get(
        'recuperacion_id'
    )

    if not recuperacion_id:
        return redirect(
            '/recuperar-contrasena/'
        )

    try:
        recuperacion = (
            RecuperacionContrasena
            .objects
            .get(
                id_recuperacion=recuperacion_id,
                utilizado=False
            )
        )

    except RecuperacionContrasena.DoesNotExist:
        # La solicitud ficticia muestra el mismo formulario que una real.
        if recuperacion_id == -1:
            form = VerificarCodigoForm(request.POST if request.method == 'POST' else None)
            if request.method == 'POST' and form.is_valid():
                request._voltify_recovery_attempt = True
                make_password(form.cleaned_data['codigo'])
                form.add_error('codigo', 'El código ingresado no es correcto.')
            return render(request, 'verificar_codigo.html', {'form': form})
        request.session.pop(
            'recuperacion_id',
            None
        )

        return redirect(
            '/recuperar-contrasena/'
        )

    # Rechaza el código cuando ya superó su fecha de expiración
    if (
        timezone.now()
        >
        recuperacion.fecha_expiracion
    ):
        recuperacion.utilizado = True

        recuperacion.save(
            update_fields=[
                'utilizado'
            ]
        )

        request.session.pop(
            'recuperacion_id',
            None
        )

        return redirect(
            '/recuperar-contrasena/'
        )

    if request.method == 'POST':
        form = VerificarCodigoForm(
            request.POST
        )

        if form.is_valid():
            request._voltify_recovery_attempt = True
            codigo = form.cleaned_data[
                'codigo'
            ]

            # Compara el código ingresado con el hash almacenado
            if check_password(
                codigo,
                recuperacion.token_hash
            ):
                request.session[
                    'recuperacion_verificada'
                ] = True

                return redirect(
                    '/nueva-contrasena/'
                )

            form.add_error(
                'codigo',
                (
                    'El código ingresado '
                    'no es correcto.'
                )
            )

    else:
        form = VerificarCodigoForm()

    data = {
        'form': form
    }

    return render(
        request,
        'verificar_codigo.html',
        data
    )


# Permite definir una nueva contraseña después de verificar el código
@never_cache
def nueva_contrasena(request):
    recuperacion_id = request.session.get(
        'recuperacion_id'
    )

    recuperacion_verificada = request.session.get(
        'recuperacion_verificada'
    )

    if (
        not recuperacion_id
        or not recuperacion_verificada
    ):
        return redirect(
            '/recuperar-contrasena/'
        )

    try:
        recuperacion = (
            RecuperacionContrasena
            .objects
            .get(
                id_recuperacion=recuperacion_id,
                utilizado=False
            )
        )

    except RecuperacionContrasena.DoesNotExist:
        request.session.pop(
            'recuperacion_id',
            None
        )

        request.session.pop(
            'recuperacion_verificada',
            None
        )

        return redirect(
            '/recuperar-contrasena/'
        )

    # Impide cambiar la contraseña si el código ya venció
    if (
        timezone.now()
        >
        recuperacion.fecha_expiracion
    ):
        recuperacion.utilizado = True

        recuperacion.save(
            update_fields=[
                'utilizado'
            ]
        )

        request.session.pop(
            'recuperacion_id',
            None
        )

        request.session.pop(
            'recuperacion_verificada',
            None
        )

        return redirect(
            '/recuperar-contrasena/'
        )

    if request.method == 'POST':
        form = NuevaContrasenaForm(
            request.POST
        )

        if form.is_valid():
            nueva_contrasena = (
                form.cleaned_data[
                    'nueva_contrasena'
                ]
            )

            usuario = recuperacion.usuario
            correo = usuario.correo.strip().lower()
            User = get_user_model()

            usuario_django = (
                User.objects.filter(
                    username__iexact=correo
                )
                .first()
            )

            usuario_validacion = (
                usuario_django
                if usuario_django is not None
                else User(
                    username=correo,
                    email=correo
                )
            )

            try:
                # Exige las mismas reglas de contraseña del sistema nativo
                validate_password(
                    nueva_contrasena,
                    user=usuario_validacion
                )

            except ValidationError as errores:
                for error in errores.messages:
                    form.add_error(
                        'nueva_contrasena',
                        error
                    )

            else:
                nueva_contrasena_hash = (
                    make_password(
                        nueva_contrasena
                    )
                )

                # Actualiza ambas credenciales de forma atómica
                with transaction.atomic():
                    usuario.contrasena_hash = (
                        nueva_contrasena_hash
                    )

                    usuario.save(
                        update_fields=[
                            'contrasena_hash'
                        ]
                    )

                    if usuario_django is None:
                        usuario_django = User(
                            username=correo,
                            email=correo,
                            is_active=True,
                            is_staff=False,
                            is_superuser=False,
                        )

                    else:
                        usuario_django.email = correo

                    usuario_django.password = (
                        nueva_contrasena_hash
                    )

                    usuario_django.save()

                    recuperacion.utilizado = True

                    recuperacion.save(
                        update_fields=[
                            'utilizado'
                        ]
                    )

                # Invalida cualquier sesión previa después del cambio de clave
                auth_logout(request)

                return redirect(
                    '/iniciar-sesion/'
                )

    else:
        form = NuevaContrasenaForm()

    data = {
        'form': form
    }

    return render(
        request,
        'nueva_contrasena.html',
        data
    )


# Permite actualizar la configuración y mantiene sincronizado auth_user
@never_cache
@usuario_voltify_requerido
def configuracion(request):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        auth_logout(request)

        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        auth_logout(request)

        return redirect(
            '/iniciar-sesion/'
        )

    # Verifica que la sesión nativa corresponda al perfil de Voltify
    if (
        request.user.username.lower()
        !=
        usuario.correo.lower()
    ):
        auth_logout(request)

        return redirect(
            '/iniciar-sesion/'
        )


    # Procesa los cambios enviados desde el formulario de configuración
    if request.method == 'POST':
        form = ConfiguracionUsuarioForm(
            request.POST,
            instance=usuario
        )

        if form.is_valid():
            nuevo_correo = (
                form.cleaned_data[
                    'correo'
                ]
                .strip()
                .lower()
            )

            User = get_user_model()

            correo_en_uso = (
                User.objects.filter(
                    username__iexact=nuevo_correo
                )
                .exclude(
                    pk=request.user.pk
                )
                .exists()
            )

            if correo_en_uso:
                form.add_error(
                    'correo',
                    'Ya existe otra cuenta registrada con este correo.'
                )

            else:
                with transaction.atomic():
                    usuario = form.save(
                        commit=False
                    )

                    usuario.correo = nuevo_correo
                    usuario.save()

                    request.user.username = (
                        nuevo_correo
                    )

                    request.user.email = (
                        nuevo_correo
                    )

                    request.user.save(
                        update_fields=[
                            'username',
                            'email',
                        ]
                    )

                request.session[
                    'usuario_nombre'
                ] = usuario.nombre

                return redirect(
                    '/configuracion/'
                )

    else:
        form = ConfiguracionUsuarioForm(
            instance=usuario
        )

    # Obtiene la tarifa que corresponde a la configuración actual
    tarifa_info = obtener_tarifa_usuario(
        usuario
    )

    data = {
        'usuario': usuario,
        'form': form,
        'tarifa_actual': tarifa_info,
        'activa': 'configuracion',
    }

    return render(
        request,
        'configuracion.html',
        data
    )


# Elimina el perfil de Voltify y su cuenta nativa de Django
@never_cache
@usuario_voltify_requerido
def eliminar_cuenta(request):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        auth_logout(request)

        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        auth_logout(request)

        return redirect(
            '/iniciar-sesion/'
        )

    # Impide operar sobre un perfil distinto al usuario autenticado por Django
    if (
        request.user.username.lower()
        !=
        usuario.correo.lower()
    ):
        auth_logout(request)

        return redirect(
            '/iniciar-sesion/'
        )

    # La eliminación definitiva solo se ejecuta mediante POST
    if request.method == 'POST':
        confirmacion = request.POST.get(
            'confirmacion',
            ''
        ).strip()

        # Obliga al usuario a confirmar escribiendo ELIMINAR
        if confirmacion != 'ELIMINAR':
            messages.error(
                request,
                'Para eliminar tu cuenta debes escribir ELIMINAR.'
            )

        else:
            usuario_django_id = request.user.pk

            # Ejecuta todo el borrado como una sola operación
            with transaction.atomic():
                Alerta.objects.filter(
                    consumo__usuario=usuario
                ).delete()

                Consumo.objects.filter(
                    usuario=usuario
                ).delete()

                Artefacto.objects.filter(
                    usuario=usuario
                ).delete()

                MetaMensual.objects.filter(
                    usuario=usuario
                ).delete()

                RecuperacionContrasena.objects.filter(
                    usuario=usuario
                ).delete()

                usuario.delete()

                get_user_model().objects.filter(
                    pk=usuario_django_id
                ).delete()

            # Invalida la sesión nativa después de borrar ambas cuentas
            auth_logout(request)

            return redirect(
                '/iniciar-sesion/'
            )

    data = {
        'usuario': usuario,
        'activa': 'configuracion',
    }

    return render(
        request,
        'eliminar_cuenta.html',
        data
    )


@never_cache
@usuario_voltify_requerido
def lista_artefactos(request):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )


    # Consulta únicamente los artefactos que siguen activos
    artefactos = (
        Artefacto.objects.filter(
            usuario=usuario,
            activo=True
        )
        .order_by(
            'nombre_artefacto'
        )
    )

    data = {
        'usuario': usuario,
        'artefactos': artefactos,
        'activa': 'artefactos',
    }

    return render(
        request,
        'lista_artefactos.html',
        data
    )


# Registra un artefacto nuevo asociado al usuario autenticado
@never_cache
@usuario_voltify_requerido
def registrar_artefacto(request):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )

    if request.method == 'POST':
        form = ArtefactoForm(
            request.POST
        )

        # Valida el formulario antes de guardar el artefacto
        if form.is_valid():
            # Crea el objeto sin guardarlo para completar sus datos antes del save
            artefacto = form.save(
                commit=False
            )

            # Asocia el artefacto al usuario y define su estado inicial
            artefacto.usuario = usuario
            artefacto.activo = True
            artefacto.monitoreando = False
            artefacto.fecha_registro = timezone.now()

            artefacto.save()

            messages.success(
                request,
                'Artefacto registrado correctamente.'
            )

            return redirect(
                '/artefactos/'
            )

    else:
        form = ArtefactoForm()

    data = {
        'form': form,
        'usuario': usuario,
        'activa': 'artefactos',
    }

    return render(
        request,
        'registrar_artefacto.html',
        data
    )


# Edita un artefacto existente sin crear un registro nuevo
@never_cache
@usuario_voltify_requerido
def editar_artefacto(
    request,
    id_artefacto
):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )

    # Comprueba que el artefacto pertenezca al usuario y siga activo
    try:
        artefacto = Artefacto.objects.get(
            id_artefacto=id_artefacto,
            usuario=usuario,
            activo=True
        )

    except Artefacto.DoesNotExist:
        return redirect(
            '/artefactos/'
        )

    # Procesa los cambios enviados desde el formulario de edición
    if request.method == 'POST':
        form = ArtefactoForm(
            request.POST,
            instance=artefacto
        )

        # Valida los nuevos datos antes de actualizar el mismo registro
        if form.is_valid():
            artefacto = form.save(
                commit=False
            )

            artefacto.usuario = usuario
            artefacto.save()

            messages.success(
                request,
                'Artefacto actualizado correctamente.'
            )

            return redirect(
                '/artefactos/'
            )

    else:
        form = ArtefactoForm(
            instance=artefacto
        )

    data = {
        'form': form,
        'usuario': usuario,
        'artefacto': artefacto,
        'activa': 'artefactos',
    }

    return render(
        request,
        'editar_artefacto.html',
        data
    )


# Activa el monitoreo de un artefacto registrado
@never_cache
@usuario_voltify_requerido
def iniciar_monitoreo(
    request,
    id_artefacto
):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )

    # El monitoreo solo se modifica mediante una solicitud POST
    if request.method != 'POST':
        return redirect(
            '/artefactos/'
        )

    try:
        artefacto = Artefacto.objects.get(
            id_artefacto=id_artefacto,
            usuario=usuario,
            activo=True
        )

    except Artefacto.DoesNotExist:
        return redirect(
            '/artefactos/'
        )

    # Cambia únicamente el estado de monitoreo
    artefacto.monitoreando = True

    artefacto.save(
        update_fields=[
            'monitoreando'
        ]
    )

    messages.success(
        request,
        (
            'Monitoreo iniciado correctamente para '
            f'{artefacto.nombre_artefacto}.'
        )
    )

    return redirect(
        '/artefactos/'
    )


# Detiene el monitoreo sin eliminar el artefacto
@never_cache
@usuario_voltify_requerido
def detener_monitoreo(
    request,
    id_artefacto
):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )

    # El monitoreo solo se modifica mediante una solicitud POST
    if request.method != 'POST':
        return redirect(
            '/artefactos/'
        )

    try:
        artefacto = Artefacto.objects.get(
            id_artefacto=id_artefacto,
            usuario=usuario,
            activo=True
        )

    except Artefacto.DoesNotExist:
        return redirect(
            '/artefactos/'
        )

    # Mantiene el artefacto registrado y solo detiene su monitoreo
    artefacto.monitoreando = False

    artefacto.save(
        update_fields=[
            'monitoreando'
        ]
    )

    messages.success(
        request,
        (
            'Monitoreo detenido correctamente para '
            f'{artefacto.nombre_artefacto}.'
        )
    )

    return redirect(
        '/artefactos/'
    )


# Elimina fisicamente un artefacto y conserva su historial de consumo
@never_cache
@usuario_voltify_requerido
def eliminar_artefacto(
    request,
    id_artefacto
):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )

    try:
        artefacto = Artefacto.objects.get(
            id_artefacto=id_artefacto,
            usuario=usuario,
            activo=True
        )

    except Artefacto.DoesNotExist:
        return redirect(
            '/artefactos/'
        )

    # El borrado solo se ejecuta despues de la confirmacion por POST.
    # Los consumos historicos permanecen asociados directamente al usuario.
    if request.method == 'POST':
        with transaction.atomic():
            artefacto.delete()

        messages.success(
            request,
            (
                'Artefacto eliminado correctamente. '
                'Su historial de consumo se conserva.'
            )
        )

        return redirect(
            '/artefactos/'
        )

    data = {
        'usuario': usuario,
        'artefacto': artefacto,
        'activa': 'artefactos',
    }

    return render(
        request,
        'eliminar_artefacto.html',
        data
    )


# Muestra y filtra el historial de consumos del usuario
@never_cache
@usuario_voltify_requerido
def lista_consumos(request):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )


    # Obtiene los filtros enviados desde la interfaz
    periodo = request.GET.get(
        'periodo',
        'mes'
    )

    estado = request.GET.get(
        'estado',
        'todos'
    )

    buscar = request.GET.get(
        'buscar',
        ''
    ).strip()

    periodos_validos = {
        'hoy',
        'semana',
        'mes',
        'tres_meses',
        'todos',
    }

    estados_validos = {
        'todos',
        'activos',
        'retirados',
    }

    if periodo not in periodos_validos:
        periodo = 'mes'

    if estado not in estados_validos:
        estado = 'todos'

    hoy = timezone.localdate()

    zona_horaria = (
        timezone.get_current_timezone()
    )

    # Crea fechas conscientes de la zona horaria para filtrar correctamente
    def crear_fecha_local(
        anio,
        mes,
        dia
    ):
        return timezone.make_aware(
            datetime(
                anio,
                mes,
                dia,
                0,
                0,
                0
            ),
            zona_horaria
        )

    # Permite retroceder o avanzar meses sin usar fechas fijas
    def mover_inicio_mes(
        fecha_inicio,
        cantidad_meses
    ):
        indice_mes = (
            fecha_inicio.year
            *
            12
            +
            fecha_inicio.month
            -
            1
            +
            cantidad_meses
        )

        nuevo_anio = (
            indice_mes
            //
            12
        )

        nuevo_mes = (
            indice_mes
            %
            12
            +
            1
        )

        return crear_fecha_local(
            nuevo_anio,
            nuevo_mes,
            1
        )

    inicio_hoy = crear_fecha_local(
        hoy.year,
        hoy.month,
        hoy.day
    )

    fin_hoy = (
        inicio_hoy
        +
        timedelta(
            days=1
        )
    )

    # Consulta solamente los consumos pertenecientes al usuario
    consumos = (
        Consumo.objects.filter(
            usuario=usuario
        )
        .select_related(
            'artefacto'
        )
    )

    # Aplica el rango de fechas según el período seleccionado
    if periodo == 'hoy':
        consumos = consumos.filter(
            fecha__gte=inicio_hoy,
            fecha__lt=fin_hoy
        )

        periodo_texto = 'Hoy'

    elif periodo == 'semana':
        inicio_periodo = (
            inicio_hoy
            -
            timedelta(
                days=6
            )
        )

        consumos = consumos.filter(
            fecha__gte=inicio_periodo,
            fecha__lt=fin_hoy
        )

        periodo_texto = (
            'Últimos 7 días'
        )

    elif periodo == 'tres_meses':
        inicio_mes_actual = (
            crear_fecha_local(
                hoy.year,
                hoy.month,
                1
            )
        )

        inicio_periodo = (
            mover_inicio_mes(
                inicio_mes_actual,
                -2
            )
        )

        consumos = consumos.filter(
            fecha__gte=inicio_periodo,
            fecha__lt=fin_hoy
        )

        periodo_texto = (
            'Últimos 3 meses'
        )

    elif periodo == 'todos':
        periodo_texto = (
            'Historial completo'
        )

    else:
        periodo = 'mes'

        inicio_periodo = (
            crear_fecha_local(
                hoy.year,
                hoy.month,
                1
            )
        )

        consumos = consumos.filter(
            fecha__gte=inicio_periodo,
            fecha__lt=fin_hoy
        )

        periodo_texto = (
            'Mes actual'
        )

    # Filtra consumos segun artefactos existentes o eliminados
    if estado == 'activos':
        consumos = consumos.filter(
            artefacto__isnull=False,
            artefacto__activo=True
        )

    elif estado == 'retirados':
        consumos = consumos.filter(
            Q(
                artefacto__isnull=True
            )
            |
            Q(
                artefacto__activo=False
            )
        )

    # Busca coincidencias por nombre, categoría, marca o modelo
    if buscar:
        consumos = consumos.filter(
            Q(
                artefacto_nombre__icontains=buscar
            )
            |
            Q(
                categoria_nombre__icontains=buscar
            )
            |
            Q(
                marca_artefacto__icontains=buscar
            )
            |
            Q(
                modelo_artefacto__icontains=buscar
            )
        )

    consumos = consumos.order_by(
        '-fecha',
        '-id_consumo'
    )

    cantidad_registros = (
        consumos.count()
    )

    # Calcula el consumo total del período seleccionado
    consumo_total = (
        consumos.aggregate(
            total=Sum(
                'consumo_kwh'
            )
        )[
            'total'
        ]
        or
        0
    )

    artefactos_con_mediciones = (
        consumos
        .values(
            'artefacto_id_historico'
        )
        .distinct()
        .count()
    )

    ultima_medicion = (
        consumos.first()
    )

    tarifa_info = obtener_tarifa_usuario(
        usuario
    )

    tarifa_disponible = (
        tarifa_info[
            'disponible'
        ]
    )

    valor_kwh = (
        tarifa_info[
            'valor_kwh'
        ]
        if tarifa_disponible
        else None
    )

    costo_energia_total = None

    if tarifa_disponible:
        costo_energia_total = (
            consumo_total
            *
            valor_kwh
        )

    # Divide el historial en páginas de 30 registros
    paginador = Paginator(
        consumos,
        30
    )

    pagina_consumos = (
        paginador.get_page(
            request.GET.get(
                'pagina'
            )
        )
    )

    # Calcula datos adicionales para cada consumo mostrado
    for consumo in pagina_consumos:
        consumo.costo_energia_estimado = None
        consumo.fecha_eliminacion_historial = None

        if tarifa_disponible:
            consumo.costo_energia_estimado = (
                consumo.consumo_kwh
                *
                valor_kwh
            )

        # Identifica si el artefacto asociado ya fue eliminado
        consumo.artefacto_eliminado = (
            consumo.artefacto_id is None
            or not consumo.artefacto.activo
        )

    data = {
        'usuario': usuario,
        'consumos': pagina_consumos,
        'pagina_consumos': pagina_consumos,
        'periodo': periodo,
        'periodo_texto': periodo_texto,
        'estado': estado,
        'buscar': buscar,
        'cantidad_registros': (
            cantidad_registros
        ),
        'consumo_total': consumo_total,
        'artefactos_con_mediciones': (
            artefactos_con_mediciones
        ),
        'ultima_medicion': (
            ultima_medicion
        ),
        'tarifa_disponible': (
            tarifa_disponible
        ),
        'tarifa_actual': tarifa_info,
        'costo_energia_total': (
            costo_energia_total
        ),
        'activa': 'consumos',
    }

    return render(
        request,
        'lista_consumos.html',
        data
    )


# Genera consejos según consumos, metas y estado de monitoreo
@never_cache
@usuario_voltify_requerido
def consejos(request):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )


    hoy = timezone.localdate()

    zona_horaria = (
        timezone.get_current_timezone()
    )

    # Define el inicio del mes actual usando la zona horaria del proyecto
    inicio_mes = timezone.make_aware(
        datetime(
            hoy.year,
            hoy.month,
            1,
            0,
            0,
            0
        ),
        zona_horaria
    )

    if hoy.month == 12:
        fin_mes = timezone.make_aware(
            datetime(
                hoy.year + 1,
                1,
                1,
                0,
                0,
                0
            ),
            zona_horaria
        )

    else:
        fin_mes = timezone.make_aware(
            datetime(
                hoy.year,
                hoy.month + 1,
                1,
                0,
                0,
                0
            ),
            zona_horaria
        )

    artefactos = (
        Artefacto.objects.filter(
            usuario=usuario,
            activo=True
        )
        .select_related(
            'categoria'
        )
        .order_by(
            'nombre_artefacto'
        )
    )

    # Consulta los consumos correspondientes al mes actual
    consumos_mes = (
        Consumo.objects.filter(
            usuario=usuario,
            fecha__gte=inicio_mes,
            fecha__lt=fin_mes
        )
    )

    cantidad_artefactos = artefactos.count()

    cantidad_monitoreando = (
        artefactos.filter(
            monitoreando=True
        ).count()
    )

    # Acumula el consumo mensual total y el consumo por artefacto
    consumo_total_mes = 0
    consumo_por_artefacto = {}

    for consumo in consumos_mes:
        consumo_total_mes = (
            consumo_total_mes
            +
            consumo.consumo_kwh
        )

        clave = consumo.artefacto_id_historico

        if clave not in consumo_por_artefacto:
            consumo_por_artefacto[
                clave
            ] = {
                'nombre': (
                    consumo.artefacto_nombre
                    or 'Artefacto eliminado'
                ),
                'categoria': (
                    consumo.categoria_nombre
                    or 'Otros'
                ),
                'consumo': 0,
            }

        consumo_por_artefacto[
            clave
        ][
            'consumo'
        ] = (
            consumo_por_artefacto[
                clave
            ][
                'consumo'
            ]
            +
            consumo.consumo_kwh
        )

    # Busca el artefacto con mayor consumo del mes
    mayor_consumidor = None

    for item in consumo_por_artefacto.values():
        if (
            mayor_consumidor is None
            or
            item['consumo']
            >
            mayor_consumidor['consumo']
        ):
            mayor_consumidor = item

    porcentaje_mayor_consumidor = 0

    if (
        mayor_consumidor
        and consumo_total_mes > 0
    ):
        porcentaje_mayor_consumidor = round(
            (
                float(
                    mayor_consumidor[
                        'consumo'
                    ]
                )
                /
                float(
                    consumo_total_mes
                )
                *
                100
            ),
            1
        )

    # Obtiene la tarifa para calcular el costo estimado mensual
    tarifa_info = obtener_tarifa_usuario(
        usuario
    )

    tarifa_disponible = tarifa_info[
        'disponible'
    ]

    costo_energia = None
    costo_total_mes = None

    if tarifa_disponible:
        costo_energia = (
            consumo_total_mes
            *
            tarifa_info[
                'valor_kwh'
            ]
        )

        costo_total_mes = (
            costo_energia
            +
            tarifa_info[
                'cargo_fijo_mensual'
            ]
        )

    try:
        # Busca la meta correspondiente al mes actual
        meta = MetaMensual.objects.get(
            usuario=usuario,
            mes=hoy.month,
            anio=hoy.year
        )

    except MetaMensual.DoesNotExist:
        meta = None

    porcentaje_meta_consumo = None
    porcentaje_meta_consumo_barra = 0

    if (
        meta
        and
        meta.meta_consumo_kwh is not None
        and
        meta.meta_consumo_kwh > 0
    ):
        porcentaje_meta_consumo = round(
            (
                float(
                    consumo_total_mes
                )
                /
                float(
                    meta.meta_consumo_kwh
                )
                *
                100
            ),
            1
        )

        porcentaje_meta_consumo_barra = min(
            porcentaje_meta_consumo,
            100
        )

    porcentaje_meta_costo = None

    if (
        meta
        and
        meta.meta_costo_clp is not None
        and
        meta.meta_costo_clp > 0
        and
        costo_total_mes is not None
    ):
        porcentaje_meta_costo = round(
            (
                float(
                    costo_total_mes
                )
                /
                float(
                    meta.meta_costo_clp
                )
                *
                100
            ),
            1
        )

    # Construye recomendaciones personalizadas según los datos del usuario
    consejos_personalizados = []

    if mayor_consumidor:
        nombre_top = mayor_consumidor[
            'nombre'
        ]

        categoria_top = mayor_consumidor[
            'categoria'
        ]

        texto_busqueda = (
            f'{nombre_top} {categoria_top}'
        ).lower()

        nivel_top = 'informativo'

        if porcentaje_mayor_consumidor >= 50:
            nivel_top = 'alta'

        elif porcentaje_mayor_consumidor >= 30:
            nivel_top = 'media'

        if (
            'refrig' in texto_busqueda
            or
            'freezer' in texto_busqueda
        ):
            accion_top = (
                'Como es un equipo de funcionamiento '
                'continuo, no se recomienda desconectarlo. '
                'Revisa el cierre de la puerta, la '
                'temperatura configurada y que tenga '
                'ventilación suficiente.'
            )

        elif (
            'calef' in texto_busqueda
            or
            'estufa' in texto_busqueda
        ):
            accion_top = (
                'Revisa el tiempo que permanece encendido '
                'y evita utilizar una temperatura mayor a '
                'la necesaria. Los equipos de calefacción '
                'pueden concentrar una parte importante '
                'del consumo del hogar.'
            )

        elif (
            'hervidor' in texto_busqueda
            or
            'tetera' in texto_busqueda
        ):
            accion_top = (
                'Calienta solamente la cantidad de agua '
                'que necesitas y evita repetir ciclos de '
                'calentamiento innecesarios.'
            )

        elif (
            'lavadora' in texto_busqueda
            or
            'lavado' in texto_busqueda
        ):
            accion_top = (
                'Intenta agrupar las cargas de ropa y '
                'utilizar ciclos adecuados para evitar '
                'lavados pequeños innecesarios.'
            )

        elif (
            'ampolleta' in texto_busqueda
            or
            'ilumin' in texto_busqueda
            or
            'luz' in texto_busqueda
        ):
            accion_top = (
                'Mantén apagadas las luces que no estés '
                'utilizando y prioriza iluminación LED '
                'cuando corresponda.'
            )

        elif (
            'televisor' in texto_busqueda
            or
            'tv' in texto_busqueda
        ):
            accion_top = (
                'Evita dejar el televisor funcionando '
                'cuando nadie lo está utilizando y revisa '
                'sus opciones de ahorro o suspensión.'
            )

        elif (
            'computador' in texto_busqueda
            or
            'notebook' in texto_busqueda
            or
            'pc' in texto_busqueda
        ):
            accion_top = (
                'Utiliza suspensión cuando el equipo no '
                'esté en uso y evita mantener periféricos '
                'encendidos sin necesidad.'
            )

        else:
            accion_top = (
                'Revisa sus horarios y tiempo de uso para '
                'determinar si existen períodos en que '
                'pueda reducirse el consumo sin afectar '
                'su funcionamiento normal.'
            )

        consejos_personalizados.append(
            {
                'titulo': (
                    f'Revisa {nombre_top}'
                ),
                'descripcion': (
                    f'Este artefacto representa '
                    f'{porcentaje_mayor_consumidor}% '
                    f'del consumo registrado durante '
                    f'el mes.'
                ),
                'accion': accion_top,
                'nivel': nivel_top,
                'etiqueta': 'Mayor consumidor',
                'icono': '⚡',
            }
        )

    if porcentaje_meta_consumo is not None:
        if porcentaje_meta_consumo >= 100:
            consejos_personalizados.append(
                {
                    'titulo': (
                        'Meta de consumo superada'
                    ),
                    'descripcion': (
                        f'Has utilizado '
                        f'{porcentaje_meta_consumo}% '
                        f'de tu meta mensual de consumo.'
                    ),
                    'accion': (
                        'Revisa principalmente los '
                        'artefactos con mayor consumo y '
                        'reduce usos que no sean necesarios '
                        'durante el resto del mes.'
                    ),
                    'nivel': 'alta',
                    'etiqueta': 'Meta mensual',
                    'icono': '◎',
                }
            )

        elif porcentaje_meta_consumo >= 80:
            consejos_personalizados.append(
                {
                    'titulo': (
                        'Estás cerca de tu meta mensual'
                    ),
                    'descripcion': (
                        f'Ya has utilizado '
                        f'{porcentaje_meta_consumo}% '
                        f'de tu límite de consumo.'
                    ),
                    'accion': (
                        'Conviene vigilar el consumo de '
                        'los próximos días y priorizar los '
                        'equipos realmente necesarios.'
                    ),
                    'nivel': 'media',
                    'etiqueta': 'Meta mensual',
                    'icono': '◎',
                }
            )

        else:
            consejos_personalizados.append(
                {
                    'titulo': (
                        'Tu meta sigue bajo control'
                    ),
                    'descripcion': (
                        f'Actualmente llevas '
                        f'{porcentaje_meta_consumo}% '
                        f'de tu meta mensual de energía.'
                    ),
                    'accion': (
                        'Mantén tus hábitos actuales y '
                        'continúa revisando qué equipos '
                        'concentran el mayor consumo.'
                    ),
                    'nivel': 'positiva',
                    'etiqueta': 'Meta mensual',
                    'icono': '◎',
                }
            )

    if porcentaje_meta_costo is not None:
        if porcentaje_meta_costo >= 100:
            nivel_costo = 'alta'

            accion_costo = (
                'Tu costo estimado ya superó la meta '
                'económica del mes. Revisa los consumos '
                'de mayor impacto antes de realizar '
                'nuevos usos intensivos.'
            )

        elif porcentaje_meta_costo >= 80:
            nivel_costo = 'media'

            accion_costo = (
                'Estás cerca del límite económico que '
                'definiste. Controla especialmente los '
                'artefactos de mayor consumo.'
            )

        else:
            nivel_costo = 'positiva'

            accion_costo = (
                'El costo estimado permanece dentro de '
                'la meta económica definida para el mes.'
            )

        consejos_personalizados.append(
            {
                'titulo': (
                    'Seguimiento de tu presupuesto'
                ),
                'descripcion': (
                    f'Has utilizado aproximadamente '
                    f'{porcentaje_meta_costo}% '
                    f'de tu meta económica mensual.'
                ),
                'accion': accion_costo,
                'nivel': nivel_costo,
                'etiqueta': 'Costo mensual',
                'icono': '$',
            }
        )

    if (
        cantidad_artefactos > 0
        and
        cantidad_monitoreando
        <
        cantidad_artefactos
    ):
        faltantes = (
            cantidad_artefactos
            -
            cantidad_monitoreando
        )

        consejos_personalizados.append(
            {
                'titulo': (
                    'Amplía tu cobertura de monitoreo'
                ),
                'descripcion': (
                    f'Tienes '
                    f'{cantidad_monitoreando} de '
                    f'{cantidad_artefactos} artefactos '
                    f'en monitoreo actualmente.'
                ),
                'accion': (
                    f'Hay {faltantes} artefacto(s) '
                    f'registrado(s) sin monitoreo. '
                    f'Actívalos cuando quieras incluir '
                    f'su consumo en el seguimiento.'
                ),
                'nivel': 'informativo',
                'etiqueta': 'Monitoreo',
                'icono': '◉',
            }
        )

    if (
        not consejos_personalizados
        and
        consumo_total_mes == 0
    ):
        consejos_personalizados.append(
            {
                'titulo': (
                    'Aún no tenemos datos suficientes'
                ),
                'descripcion': (
                    'Voltify necesita mediciones de '
                    'consumo para generar recomendaciones '
                    'personalizadas.'
                ),
                'accion': (
                    'Activa el monitoreo de tus artefactos '
                    'y vuelve cuando existan registros.'
                ),
                'nivel': 'informativo',
                'etiqueta': 'Datos',
                'icono': '◉',
            }
        )

    # Mantiene recomendaciones generales disponibles para todos los usuarios
    consejos_generales = [
        {
            'titulo': (
                'Reduce consumos innecesarios'
            ),
            'texto': (
                'Apaga los equipos que no necesites '
                'mantener funcionando y evita dejar '
                'dispositivos activos sin uso.'
            ),
            'icono': '⚡',
        },
        {
            'titulo': (
                'Observa primero los equipos de mayor impacto'
            ),
            'texto': (
                'Una reducción pequeña en un artefacto '
                'que consume mucho puede ser más relevante '
                'que varios cambios en equipos de consumo bajo.'
            ),
            'icono': '◉',
        },
        {
            'titulo': (
                'Usa las metas como referencia'
            ),
            'texto': (
                'Una meta mensual permite detectar con '
                'anticipación si tu consumo o gasto está '
                'creciendo más rápido de lo esperado.'
            ),
            'icono': '◎',
        },
        {
            'titulo': (
                'No desconectes equipos esenciales por defecto'
            ),
            'texto': (
                'Equipos como refrigeradores necesitan '
                'funcionar de forma continua. En esos casos '
                'conviene buscar anomalías o cambios de consumo '
                'en vez de simplemente apagarlos.'
            ),
            'icono': '✓',
        },
    ]

    meses = [
        'Enero',
        'Febrero',
        'Marzo',
        'Abril',
        'Mayo',
        'Junio',
        'Julio',
        'Agosto',
        'Septiembre',
        'Octubre',
        'Noviembre',
        'Diciembre',
    ]

    data = {
        'usuario': usuario,
        'activa': 'consejos',
        'nombre_mes': meses[
            hoy.month - 1
        ],
        'anio': hoy.year,
        'cantidad_artefactos': cantidad_artefactos,
        'cantidad_monitoreando': cantidad_monitoreando,
        'consumo_total_mes': consumo_total_mes,
        'tarifa_disponible': tarifa_disponible,
        'costo_total_mes': costo_total_mes,
        'mayor_consumidor': mayor_consumidor,
        'porcentaje_mayor_consumidor': (
            porcentaje_mayor_consumidor
        ),
        'meta': meta,
        'porcentaje_meta_consumo': (
            porcentaje_meta_consumo
        ),
        'porcentaje_meta_consumo_barra': (
            porcentaje_meta_consumo_barra
        ),
        'porcentaje_meta_costo': (
            porcentaje_meta_costo
        ),
        'consejos_personalizados': (
            consejos_personalizados
        ),
        'consejos_generales': (
            consejos_generales
        ),
    }

    return render(
        request,
        'consejos.html',
        data
    )


# Crea o actualiza la meta mensual de consumo y costo del usuario
@never_cache
@usuario_voltify_requerido
def metas(request):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )


    hoy = timezone.localdate()
    mes = hoy.month
    anio = hoy.year

    # Busca si el usuario ya tiene una meta para el mes actual
    try:
        meta = MetaMensual.objects.get(
            usuario=usuario,
            mes=mes,
            anio=anio
        )

    except MetaMensual.DoesNotExist:
        meta = None

    # Si la meta existe la actualiza; si no existe crea una nueva
    if request.method == 'POST':
        if meta:
            form = MetaMensualForm(
                request.POST,
                instance=meta
            )

        else:
            form = MetaMensualForm(
                request.POST
            )

        if form.is_valid():
            meta_guardada = form.save(
                commit=False
            )

            meta_guardada.usuario = usuario
            meta_guardada.mes = mes
            meta_guardada.anio = anio
            meta_guardada.fecha_actualizacion = (
                timezone.now()
            )

            meta_guardada.save()

            return redirect(
                '/metas/'
            )

    else:
        if meta:
            form = MetaMensualForm(
                instance=meta
            )

        else:
            form = MetaMensualForm()

    zona_horaria = (
        timezone.get_current_timezone()
    )

    # Define el rango exacto del mes actual
    inicio_mes = timezone.make_aware(
        datetime(
            anio,
            mes,
            1,
            0,
            0,
            0
        ),
        zona_horaria
    )

    if mes == 12:
        fin_mes = timezone.make_aware(
            datetime(
                anio + 1,
                1,
                1,
                0,
                0,
                0
            ),
            zona_horaria
        )

    else:
        fin_mes = timezone.make_aware(
            datetime(
                anio,
                mes + 1,
                1,
                0,
                0,
                0
            ),
            zona_horaria
        )

    # Obtiene los consumos del mes para medir el avance de la meta
    consumos_mes = (
        Consumo.objects.filter(
            usuario=usuario,
            fecha__gte=inicio_mes,
            fecha__lt=fin_mes
        )
    )

    consumo_total = 0

    for consumo in consumos_mes:
        consumo_total = (
            consumo_total
            +
            consumo.consumo_kwh
        )

    tarifa_info = obtener_tarifa_usuario(
        usuario
    )

    tarifa_disponible = tarifa_info[
        'disponible'
    ]

    costo_energia = None
    cargo_fijo_aplicado = None
    costo_total = None

    # Calcula el costo de energía y suma el cargo fijo una sola vez
    if tarifa_disponible:
        costo_energia = (
            consumo_total
            *
            tarifa_info[
                'valor_kwh'
            ]
        )

        cargo_fijo_aplicado = tarifa_info[
            'cargo_fijo_mensual'
        ]

        costo_total = (
            costo_energia
            +
            cargo_fijo_aplicado
        )

    # Comprueba qué tipos de meta fueron definidos por el usuario
    meta_consumo_definida = (
        meta is not None
        and
        meta.meta_consumo_kwh is not None
    )

    meta_costo_definida = (
        meta is not None
        and
        meta.meta_costo_clp is not None
    )

    porcentaje_consumo = None
    porcentaje_costo = None

    if meta_consumo_definida:
        porcentaje_consumo = (
            float(
                consumo_total
            )
            /
            float(
                meta.meta_consumo_kwh
            )
            *
            100
        )

        porcentaje_consumo = round(
            porcentaje_consumo,
            1
        )

    if (
        meta_costo_definida
        and
        costo_total is not None
    ):
        porcentaje_costo = (
            float(
                costo_total
            )
            /
            float(
                meta.meta_costo_clp
            )
            *
            100
        )

        porcentaje_costo = round(
            porcentaje_costo,
            1
        )

    meses = [
        'Enero',
        'Febrero',
        'Marzo',
        'Abril',
        'Mayo',
        'Junio',
        'Julio',
        'Agosto',
        'Septiembre',
        'Octubre',
        'Noviembre',
        'Diciembre',
    ]

    nombre_mes = meses[
        mes - 1
    ]

    data = {
        'usuario': usuario,
        'form': form,
        'meta': meta,
        'meta_consumo_definida': (
            meta_consumo_definida
        ),
        'meta_costo_definida': (
            meta_costo_definida
        ),
        'consumo_total': consumo_total,
        'costo_energia': costo_energia,
        'cargo_fijo_aplicado': (
            cargo_fijo_aplicado
        ),
        'costo_total': costo_total,
        'tarifa_actual': tarifa_info,
        'tarifa_disponible': (
            tarifa_disponible
        ),
        'porcentaje_consumo': (
            porcentaje_consumo
        ),
        'porcentaje_costo': (
            porcentaje_costo
        ),
        'nombre_mes': nombre_mes,
        'anio': anio,
        'activa': 'metas',
    }

    return render(
        request,
        'metas.html',
        data
    )


# Elimina físicamente la meta mensual después de la confirmación
@never_cache
@usuario_voltify_requerido
def eliminar_meta(request):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )


    hoy = timezone.localdate()

    # Obtiene la meta del mes actual antes de eliminarla
    try:
        meta = MetaMensual.objects.get(
            usuario=usuario,
            mes=hoy.month,
            anio=hoy.year
        )

    except MetaMensual.DoesNotExist:
        return redirect(
            '/metas/'
        )

    # La eliminación física se ejecuta únicamente mediante POST
    if request.method == 'POST':
        # Elimina el registro MetaMensual directamente de MariaDB/MySQL
        meta.delete()

        return redirect(
            '/metas/'
        )

    meses = [
        'Enero',
        'Febrero',
        'Marzo',
        'Abril',
        'Mayo',
        'Junio',
        'Julio',
        'Agosto',
        'Septiembre',
        'Octubre',
        'Noviembre',
        'Diciembre',
    ]

    data = {
        'usuario': usuario,
        'meta': meta,
        'nombre_mes': meses[
            hoy.month - 1
        ],
        'anio': hoy.year,
        'activa': 'metas',
    }

    return render(
        request,
        'eliminar_meta.html',
        data
    )


# Genera reportes de consumo, costos, comparaciones y alertas
@never_cache
@usuario_voltify_requerido
def reportes(request):
    usuario_id = request.session.get(
        'usuario_id'
    )

    if not usuario_id:
        return redirect(
            '/iniciar-sesion/'
        )

    try:
        usuario = Usuario.objects.get(
            id_usuario=usuario_id
        )

    except Usuario.DoesNotExist:
        request.session.pop(
            'usuario_id',
            None
        )

        request.session.pop(
            'usuario_nombre',
            None
        )

        return redirect(
            '/iniciar-sesion/'
        )


    # Obtiene el período seleccionado para construir el reporte
    periodo = request.GET.get(
        'periodo',
        'mes'
    )

    zona_horaria = (
        timezone.get_current_timezone()
    )

    hoy = timezone.localdate()

    # Crea fechas locales conscientes de la zona horaria
    def crear_fecha_local(
        anio,
        mes,
        dia
    ):
        return timezone.make_aware(
            datetime(
                anio,
                mes,
                dia,
                0,
                0,
                0
            ),
            zona_horaria
        )

    def mover_inicio_mes(
        fecha_inicio,
        cantidad_meses
    ):
        indice_mes = (
            fecha_inicio.year
            *
            12
            +
            fecha_inicio.month
            -
            1
            +
            cantidad_meses
        )

        nuevo_anio = (
            indice_mes
            //
            12
        )

        nuevo_mes = (
            indice_mes
            %
            12
            +
            1
        )

        return crear_fecha_local(
            nuevo_anio,
            nuevo_mes,
            1
        )

    inicio_hoy = crear_fecha_local(
        hoy.year,
        hoy.month,
        hoy.day
    )

    fin_hoy = (
        inicio_hoy
        +
        timedelta(
            days=1
        )
    )

    # Prepara la consulta base de consumos del usuario
    consumos_base = (
        Consumo.objects.filter(
            usuario=usuario
        )
        .select_related(
            'artefacto'
        )
        .order_by(
            '-fecha'
        )
    )

    # Prepara la consulta base de alertas relacionadas con el usuario
    alertas_base = (
        Alerta.objects.filter(
            consumo__usuario=usuario
        )
        .select_related(
            'consumo',
            'consumo__artefacto'
        )
        .order_by(
            '-fecha_alerta'
        )
    )

    # Define el período actual y el período anterior para compararlos
    if periodo == 'hoy':
        inicio_periodo = inicio_hoy
        fin_periodo = fin_hoy

        inicio_anterior = (
            inicio_periodo
            -
            timedelta(
                days=1
            )
        )

        fin_anterior = inicio_periodo

        periodo_texto = 'Hoy'

        comparacion_texto = (
            'Comparado con ayer'
        )

        dias_periodo = 1
        meses_cargo_fijo = 0

    elif periodo == 'semana':
        inicio_periodo = (
            inicio_hoy
            -
            timedelta(
                days=6
            )
        )

        fin_periodo = fin_hoy

        inicio_anterior = (
            inicio_periodo
            -
            timedelta(
                days=7
            )
        )

        fin_anterior = inicio_periodo

        periodo_texto = (
            'Últimos 7 días'
        )

        comparacion_texto = (
            'Comparado con los '
            '7 días anteriores'
        )

        dias_periodo = 7
        meses_cargo_fijo = 0

    elif periodo == 'tres_meses':
        inicio_mes_actual = crear_fecha_local(
            hoy.year,
            hoy.month,
            1
        )

        inicio_periodo = mover_inicio_mes(
            inicio_mes_actual,
            -2
        )

        fin_periodo = fin_hoy

        dias_periodo = max(
            (
                fin_periodo.date()
                -
                inicio_periodo.date()
            ).days,
            1
        )

        inicio_anterior = mover_inicio_mes(
            inicio_periodo,
            -3
        )

        fin_anterior = (
            inicio_anterior
            +
            timedelta(
                days=dias_periodo
            )
        )

        periodo_texto = (
            'Últimos 3 meses'
        )

        comparacion_texto = (
            'Comparado con un período '
            'equivalente anterior'
        )

        meses_cargo_fijo = 3

    else:
        periodo = 'mes'

        inicio_periodo = crear_fecha_local(
            hoy.year,
            hoy.month,
            1
        )

        fin_periodo = fin_hoy

        dias_periodo = max(
            (
                fin_periodo.date()
                -
                inicio_periodo.date()
            ).days,
            1
        )

        inicio_anterior = mover_inicio_mes(
            inicio_periodo,
            -1
        )

        fin_mes_anterior = inicio_periodo

        fin_anterior_estimado = (
            inicio_anterior
            +
            timedelta(
                days=dias_periodo
            )
        )

        fin_anterior = min(
            fin_anterior_estimado,
            fin_mes_anterior
        )

        periodo_texto = (
            'Mes actual'
        )

        comparacion_texto = (
            'Comparado con el mismo '
            'avance del mes anterior'
        )

        meses_cargo_fijo = 1

    # Filtra los consumos del período actual
    consumos = (
        consumos_base.filter(
            fecha__gte=inicio_periodo,
            fecha__lt=fin_periodo
        )
    )

    consumos_anterior = (
        consumos_base.filter(
            fecha__gte=inicio_anterior,
            fecha__lt=fin_anterior
        )
    )

    alertas = (
        alertas_base.filter(
            fecha_alerta__gte=inicio_periodo,
            fecha_alerta__lt=fin_periodo
        )
    )

    # Comprueba si existen datos suficientes para realizar la comparación
    comparacion_disponible = (
        consumos_anterior.exists()
    )

    if not comparacion_disponible:
        comparacion_texto = (
            'Sin datos suficientes '
            'en el período anterior'
        )

    # Obtiene la tarifa necesaria para calcular costos
    tarifa_info = obtener_tarifa_usuario(
        usuario
    )

    tarifa_disponible = tarifa_info[
        'disponible'
    ]

    valor_kwh = (
        tarifa_info[
            'valor_kwh'
        ]
        if tarifa_disponible
        else None
    )

    cargo_fijo_mensual = (
        tarifa_info[
            'cargo_fijo_mensual'
        ]
        if tarifa_disponible
        else None
    )

    consumo_total = 0

    costo_energia = (
        0
        if tarifa_disponible
        else None
    )

    cargo_fijo_aplicado = None
    costo_total = None
    cantidad_registros = 0

    # Prepara el detalle y el resumen de consumo por artefacto
    detalle_consumos = []
    resumen_artefactos = {}

    for consumo in consumos:
        consumo_total = (
            consumo_total
            +
            consumo.consumo_kwh
        )

        cantidad_registros = (
            cantidad_registros
            +
            1
        )

        costo_consumo = None

        if tarifa_disponible:
            costo_consumo = (
                consumo.consumo_kwh
                *
                valor_kwh
            )

            costo_energia = (
                costo_energia
                +
                costo_consumo
            )

        categoria = (
            consumo.categoria_nombre
            or 'Otros'
        )

        nombre_artefacto = (
            consumo.artefacto_nombre
            or 'Artefacto eliminado'
        )

        if (
            nombre_artefacto
            not in resumen_artefactos
        ):
            resumen_artefactos[
                nombre_artefacto
            ] = {
                'consumo_total': 0,
                'costo_total': (
                    0
                    if tarifa_disponible
                    else None
                ),
            }

        resumen_artefactos[
            nombre_artefacto
        ][
            'consumo_total'
        ] = (
            resumen_artefactos[
                nombre_artefacto
            ][
                'consumo_total'
            ]
            +
            consumo.consumo_kwh
        )

        if tarifa_disponible:
            resumen_artefactos[
                nombre_artefacto
            ][
                'costo_total'
            ] = (
                resumen_artefactos[
                    nombre_artefacto
                ][
                    'costo_total'
                ]
                +
                costo_consumo
            )

        detalle_consumos.append(
            {
                'fecha': consumo.fecha,
                'artefacto': nombre_artefacto,
                'categoria': categoria,
                'consumo_kwh': consumo.consumo_kwh,
                'costo_estimado': costo_consumo,
            }
        )

    # Aplica el cargo fijo según la cantidad de meses del período
    if tarifa_disponible:
        cargo_fijo_aplicado = (
            cargo_fijo_mensual
            *
            meses_cargo_fijo
        )

        costo_total = (
            costo_energia
            +
            cargo_fijo_aplicado
        )

    consumo_total_anterior = None
    costo_energia_anterior = None
    cargo_fijo_anterior = None
    costo_total_anterior = None

    # Calcula los totales correspondientes al período anterior
    if comparacion_disponible:
        consumo_total_anterior = 0

        if tarifa_disponible:
            costo_energia_anterior = 0

        for consumo in consumos_anterior:
            consumo_total_anterior = (
                consumo_total_anterior
                +
                consumo.consumo_kwh
            )

            if tarifa_disponible:
                costo_energia_anterior = (
                    costo_energia_anterior
                    +
                    (
                        consumo.consumo_kwh
                        *
                        valor_kwh
                    )
                )

        if tarifa_disponible:
            cargo_fijo_anterior = (
                cargo_fijo_mensual
                *
                meses_cargo_fijo
            )

            costo_total_anterior = (
                costo_energia_anterior
                +
                cargo_fijo_anterior
            )

    # Identifica el artefacto con mayor consumo y mayor costo
    mayor_consumidor_nombre = (
        'Sin datos'
    )

    mayor_consumidor_kwh = 0

    mayor_costo_nombre = (
        'Sin datos'
    )

    mayor_costo_total = (
        0
        if tarifa_disponible
        else None
    )

    for (
        nombre_artefacto,
        resumen
    ) in resumen_artefactos.items():

        if (
            resumen[
                'consumo_total'
            ]
            >
            mayor_consumidor_kwh
        ):
            mayor_consumidor_nombre = (
                nombre_artefacto
            )

            mayor_consumidor_kwh = (
                resumen[
                    'consumo_total'
                ]
            )

        if (
            tarifa_disponible
            and
            resumen[
                'costo_total'
            ]
            >
            mayor_costo_total
        ):
            mayor_costo_nombre = (
                nombre_artefacto
            )

            mayor_costo_total = (
                resumen[
                    'costo_total'
                ]
            )

    # Calcula el promedio diario del período seleccionado
    promedio_diario = 0

    if dias_periodo > 0:
        promedio_diario = round(
            float(
                consumo_total
            )
            /
            dias_periodo,
            2
        )

    # Calcula la variación porcentual de consumo respecto al período anterior
    variacion_consumo = None

    estado_variacion_consumo = (
        'sin_datos'
    )

    if comparacion_disponible:
        variacion_consumo = 0

        estado_variacion_consumo = (
            'igual'
        )

        if consumo_total_anterior > 0:
            variacion_consumo = (
                (
                    float(
                        consumo_total
                    )
                    -
                    float(
                        consumo_total_anterior
                    )
                )
                /
                float(
                    consumo_total_anterior
                )
                *
                100
            )

            variacion_consumo = round(
                variacion_consumo,
                1
            )

            if variacion_consumo > 0:
                estado_variacion_consumo = (
                    'subio'
                )

            elif variacion_consumo < 0:
                estado_variacion_consumo = (
                    'bajo'
                )

        elif consumo_total > 0:
            variacion_consumo = 100

            estado_variacion_consumo = (
                'subio'
            )

    # Calcula la variación porcentual del costo cuando existe tarifa
    variacion_costo = None

    estado_variacion_costo = (
        'sin_datos'
    )

    if (
        tarifa_disponible
        and
        comparacion_disponible
    ):
        variacion_costo = 0

        estado_variacion_costo = (
            'igual'
        )

        if (
            costo_total_anterior is not None
            and
            costo_total_anterior > 0
        ):
            variacion_costo = (
                (
                    float(
                        costo_total
                    )
                    -
                    float(
                        costo_total_anterior
                    )
                )
                /
                float(
                    costo_total_anterior
                )
                *
                100
            )

            variacion_costo = round(
                variacion_costo,
                1
            )

            if variacion_costo > 0:
                estado_variacion_costo = (
                    'subio'
                )

            elif variacion_costo < 0:
                estado_variacion_costo = (
                    'bajo'
                )

        elif (
            costo_total is not None
            and
            costo_total > 0
        ):
            variacion_costo = 100

            estado_variacion_costo = (
                'subio'
            )

    # Prepara el detalle de alertas que se mostrará en el reporte
    alertas_detalle = []
    cantidad_alertas = 0

    for alerta in alertas:
        cantidad_alertas = (
            cantidad_alertas
            +
            1
        )

        costo_alerta = None

        if tarifa_disponible:
            costo_alerta = (
                alerta
                .consumo
                .consumo_kwh
                *
                valor_kwh
            )

        alertas_detalle.append(
            {
                'fecha_alerta': alerta.fecha_alerta,
                'tipo_alerta': alerta.tipo_alerta,
                'mensaje': alerta.mensaje,
                'artefacto': (
                    alerta
                    .consumo
                    .artefacto
                    .nombre_artefacto
                ),
                'consumo_kwh': (
                    alerta
                    .consumo
                    .consumo_kwh
                ),
                'costo_estimado': costo_alerta,
                'leida': alerta.leida,
            }
        )

    # Envía al template todos los resultados calculados del reporte
    data = {
        'usuario': usuario,
        'periodo': periodo,
        'periodo_texto': periodo_texto,
        'comparacion_texto': comparacion_texto,
        'comparacion_disponible': (
            comparacion_disponible
        ),
        'consumo_total': consumo_total,
        'costo_energia': costo_energia,
        'cargo_fijo_aplicado': (
            cargo_fijo_aplicado
        ),
        'meses_cargo_fijo': meses_cargo_fijo,
        'costo_total': costo_total,
        'tarifa_actual': tarifa_info,
        'tarifa_disponible': tarifa_disponible,
        'cantidad_registros': cantidad_registros,
        'promedio_diario': promedio_diario,
        'mayor_consumidor_nombre': (
            mayor_consumidor_nombre
        ),
        'mayor_consumidor_kwh': (
            mayor_consumidor_kwh
        ),
        'mayor_costo_nombre': (
            mayor_costo_nombre
        ),
        'mayor_costo_total': mayor_costo_total,
        'consumo_total_anterior': (
            consumo_total_anterior
        ),
        'costo_energia_anterior': (
            costo_energia_anterior
        ),
        'cargo_fijo_anterior': (
            cargo_fijo_anterior
        ),
        'costo_total_anterior': (
            costo_total_anterior
        ),
        'variacion_consumo': variacion_consumo,
        'estado_variacion_consumo': (
            estado_variacion_consumo
        ),
        'variacion_costo': variacion_costo,
        'estado_variacion_costo': (
            estado_variacion_costo
        ),
        'detalle_consumos': detalle_consumos,
        'cantidad_alertas': cantidad_alertas,
        'alertas_detalle': alertas_detalle,
        'activa': 'reportes',
    }

    return render(
        request,
        'reportes.html',
        data
    )
