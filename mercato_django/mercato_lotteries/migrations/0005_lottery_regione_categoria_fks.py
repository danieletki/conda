import django.db.models.deletion
from django.db import migrations, models


def set_existing_lotteries_regione_categoria(apps, schema_editor):
    Lottery = apps.get_model('mercato_lotteries', 'Lottery')
    Lottery.objects.all().update(regione_id=1, categoria_id=1)


class Migration(migrations.Migration):

    dependencies = [
        ('mercato_lotteries', '0004_regione_categoria_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='lottery',
            name='categoria',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                to='mercato_lotteries.categoria',
            ),
        ),
        migrations.AddField(
            model_name='lottery',
            name='regione',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                to='mercato_lotteries.regione',
            ),
        ),
        migrations.RunPython(set_existing_lotteries_regione_categoria, migrations.RunPython.noop),
    ]
