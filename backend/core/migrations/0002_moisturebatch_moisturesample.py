# Generated for A08: 土壤含水抽检批次与测点
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MoistureBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("batch_code", models.CharField(max_length=40)),
                ("opened_on", models.DateField()),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "greenhouse",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="moisture_batches",
                        to="core.greenhouse",
                    ),
                ),
            ],
            options={
                "ordering": ["-opened_on", "-id"],
            },
        ),
        migrations.CreateModel(
            name="MoistureSample",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "moisture_pct",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(5),
                            django.core.validators.MaxValueValidator(95),
                        ]
                    ),
                ),
                ("sampled_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="samples",
                        to="core.moisturebatch",
                    ),
                ),
                (
                    "zone",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="moisture_samples",
                        to="core.zone",
                    ),
                ),
            ],
            options={
                "ordering": ["-sampled_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="moisturebatch",
            constraint=models.UniqueConstraint(
                fields=("greenhouse", "batch_code"),
                name="uniq_moisture_batch_code_per_greenhouse",
            ),
        ),
        migrations.AddConstraint(
            model_name="moisturesample",
            constraint=models.UniqueConstraint(
                fields=("batch", "zone"),
                name="uniq_moisture_zone_per_batch",
            ),
        ),
    ]
