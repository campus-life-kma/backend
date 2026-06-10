import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_booking_cancelled_by"),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='education_level',
            field=models.CharField(
                choices=[("BACHELOR", "Бакалавр"), ("MASTER", "Магістр"), ("PHD", "Аспірант")],
                default="BACHELOR",
                help_text="Рівень навчання користувача: бакалаврат, магістратура або аспірантура",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="year",
            field=models.SmallIntegerField(
                blank=True,
                help_text="Курс або рік навчання (від 1 до 4; для магістратури доступні 1-2)",
                null=True,
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(4)],
            ),
        ),
    ]
