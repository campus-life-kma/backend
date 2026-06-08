from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("api", "0003_social_event_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="cancelled_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Користувач, який скасував бронювання",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cancelled_bookings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
