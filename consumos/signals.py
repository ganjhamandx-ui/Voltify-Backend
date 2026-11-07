"""Mantiene el hash de perfiles existentes al cambiar claves en Django Admin."""
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Usuario


@receiver(post_save, sender=get_user_model(), dispatch_uid='voltify_sync_password')
def sincronizar_password(sender, instance, raw=False, using='default', **kwargs):
    if raw:
        return
    Usuario.objects.using(using).filter(correo__iexact=instance.username).exclude(
        contrasena_hash=instance.password
    ).update(contrasena_hash=instance.password)
