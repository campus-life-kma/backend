from django.db import migrations, models


def set_floor_notices(apps, schema_editor):
    Floor = apps.get_model("api", "Floor")
    Floor.objects.filter(dormitory__name="Маккейна", number=2, notice="").update(
        notice="2-й поверх не належить гуртожитку, це звичайний житловий будинок."
    )


def clear_floor_notices(apps, schema_editor):
    Floor = apps.get_model("api", "Floor")
    Floor.objects.filter(
        dormitory__name="Маккейна",
        number=2,
        notice="2-й поверх не належить гуртожитку, це звичайний житловий будинок.",
    ).update(notice="")


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_seed"),
    ]

    operations = [
        migrations.AddField(
            model_name="floor",
            name="notice",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Коротке попередження для відображення на мапі цього поверху, якщо воно потрібне",
            ),
        ),
        migrations.RunPython(set_floor_notices, clear_floor_notices),
    ]
