# Ajusta la relación del consumo mediante el esquema de migraciones de Django.
# Compatible con nuevas instalaciones sobre MySQL sin SQL manual específico.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('consumos', '0011_consumo_historial_artefacto'),
    ]

    operations = [
        migrations.AlterField(
            model_name='consumo',
            name='artefacto',
            field=models.ForeignKey(
                blank=True,
                db_column='ID_ARTEFACTO',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='consumos.artefacto',
            ),
        ),
    ]
