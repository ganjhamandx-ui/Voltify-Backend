# Generated for Voltify E3 - DELETE fisico de artefactos

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        (
            'consumos',
            '0011_consumo_historial_artefacto'
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE `consumo` "
                        "MODIFY COLUMN `ID_ARTEFACTO` "
                        "int(11) NULL;"
                    ),
                    reverse_sql=(
                        "ALTER TABLE `consumo` "
                        "MODIFY COLUMN `ID_ARTEFACTO` "
                        "int(11) NOT NULL;"
                    ),
                ),
            ],
            state_operations=[
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
            ],
        ),
    ]
