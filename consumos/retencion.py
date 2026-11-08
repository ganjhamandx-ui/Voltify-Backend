"""Selección inequívoca por propietario e ID histórico, nunca por nombre."""
from datetime import timedelta, timezone as datetime_timezone

from django.db.models import Exists, OuterRef
from django.utils import timezone

from .models import Alerta, Consumo, RetencionArtefacto


def consumos_vencidos(usuario_id=None, ahora=None):
    ahora = ahora or timezone.now()
    limite = ahora.astimezone(datetime_timezone.utc) - timedelta(days=90)
    controles = RetencionArtefacto.objects.filter(
        usuario_id=OuterRef('usuario_id'),
        artefacto_id_historico=OuterRef('artefacto_id_historico'),
        fecha_eliminacion__lte=limite,
    )
    candidatos = Consumo.objects.filter(artefacto__isnull=True).annotate(
        retencion_vencida=Exists(controles),
        tiene_alertas=Exists(Alerta.objects.filter(consumo_id=OuterRef('pk'))),
    ).filter(retencion_vencida=True)
    if usuario_id is not None:
        candidatos = candidatos.filter(usuario_id=usuario_id)
    return candidatos
