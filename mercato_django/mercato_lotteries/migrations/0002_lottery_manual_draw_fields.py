from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mercato_lotteries', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='lottery',
            name='can_manually_draw',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='lottery',
            name='min_draw_delay_hours',
            field=models.PositiveIntegerField(default=24),
        ),
    ]
