from django.core.management.color import no_style
from django.db import migrations, models


def create_initial_regione_categoria(apps, schema_editor):
    Regione = apps.get_model('mercato_lotteries', 'Regione')
    Categoria = apps.get_model('mercato_lotteries', 'Categoria')

    Regione.objects.create(id=1, name='Non Specificato')

    regioni = [
        'Abruzzo',
        'Basilicata',
        'Calabria',
        'Campania',
        'Emilia-Romagna',
        'Friuli-Venezia Giulia',
        'Lazio',
        'Liguria',
        'Lombardia',
        'Marche',
        'Molise',
        'Piemonte',
        'Puglia',
        'Sardegna',
        'Sicilia',
        'Toscana',
        'Trentino-Alto Adige',
        'Umbria',
        "Valle d'Aosta",
        'Veneto',
    ]

    for idx, name in enumerate(regioni, start=2):
        Regione.objects.create(id=idx, name=name)

    Categoria.objects.create(id=1, name='Generico')

    for statement in schema_editor.connection.ops.sequence_reset_sql(
        no_style(),
        [Regione, Categoria],
    ):
        schema_editor.execute(statement)


class Migration(migrations.Migration):

    dependencies = [
        ('mercato_lotteries', '0003_stabilize_index_names'),
        ('mercato_lotteries', '0002_winnerdrawing_shipping'),
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Regione',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.RunPython(create_initial_regione_categoria, migrations.RunPython.noop),
    ]
