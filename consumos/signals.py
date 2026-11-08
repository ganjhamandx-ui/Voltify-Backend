"""Mantiene el hash de perfiles existentes al cambiar claves en Django Admin."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Artefacto, Consumo, RetencionArtefacto, Usuario


@receiver(post_save, sender=get_user_model(), dispatch_uid='voltify_sync_password')
def sincronizar_password(sender, instance, raw=False, using='default', **kwargs):
    if raw:
        return
    Usuario.objects.using(using).filter(correo__iexact=instance.username).exclude(
        contrasena_hash=instance.password
    ).update(contrasena_hash=instance.password)


@receiver(pre_delete, sender=Artefacto, dispatch_uid='voltify_snapshot_delete')
def conservar_identidad_consumos(sender, instance, using='default', **kwargs):
    # La transacción de delete() también cubre estas actualizaciones y el control.
    Artefacto.objects.using(using).select_for_update().get(pk=instance.pk)
    consumos = Consumo.objects.using(using).filter(artefacto_id=instance.pk)
    if consumos.exclude(usuario_id=instance.usuario_id).exclude(usuario__isnull=True).exists():
        raise ValidationError('El propietario del historial no coincide. No se eliminó el artefacto.')
    consumos.update(usuario_id=instance.usuario_id, artefacto_id_historico=instance.pk)
    datos = {
        'artefacto_nombre': instance.nombre_artefacto,
        'categoria_nombre': instance.categoria.nombre_categoria if instance.categoria else None,
        'marca_artefacto': instance.marca,
        'modelo_artefacto': instance.modelo,
    }
    for campo, valor in datos.items():
        consumos.filter(Q(**{campo + '__isnull': True}) | Q(**{campo: ''})).update(**{campo: valor})


@receiver(post_delete, sender=Artefacto, dispatch_uid='voltify_retention_delete')
def registrar_eliminacion_fisica(sender, instance, using='default', **kwargs):
    RetencionArtefacto.objects.using(using).create(
        usuario_id=instance.usuario_id,
        artefacto_id_historico=instance.pk,
        fecha_eliminacion=timezone.now(),
    )
