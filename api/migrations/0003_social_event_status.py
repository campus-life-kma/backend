from django.db import migrations, models
import django.db.models.deletion


def fill_event_status(apps, schema_editor):
    SocialEvent = apps.get_model("api", "SocialEvent")
    SocialSharingStatus = apps.get_model("api", "SocialSharingStatus")
    active_status, _ = SocialSharingStatus.objects.get_or_create(status="ACTIVE")
    SocialEvent.objects.filter(status__isnull=True).update(status=active_status)


def clear_event_status(apps, schema_editor):
    SocialEvent = apps.get_model("api", "SocialEvent")
    SocialEvent.objects.update(status=None)


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_seed"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialevent",
            name="status",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="events",
                to="api.socialsharingstatus",
                help_text="Поточний статус івенту",
            ),
        ),
        migrations.RunPython(fill_event_status, clear_event_status),
        migrations.AlterField(
            model_name="socialevent",
            name="status",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="events",
                to="api.socialsharingstatus",
                help_text="Поточний статус івенту",
            ),
        ),
    ]
