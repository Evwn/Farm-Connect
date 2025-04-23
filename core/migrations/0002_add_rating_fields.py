from django.db import migrations, models
from django.db.models import Avg

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='average_rating',
            field=models.DecimalField(decimal_places=2, max_digits=3, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='total_ratings',
            field=models.PositiveIntegerField(default=0),
        ),
    ] 