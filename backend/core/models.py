from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Greenhouse(models.Model):
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=200, blank=True, default="")
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Zone(models.Model):
    STATUS_IDLE = "idle"
    STATUS_GROWING = "growing"
    STATUS_FALLOW = "fallow"
    STATUS_CHOICES = [
        (STATUS_IDLE, "空闲"),
        (STATUS_GROWING, "在种"),
        (STATUS_FALLOW, "休耕"),
    ]

    greenhouse = models.ForeignKey(
        Greenhouse, on_delete=models.CASCADE, related_name="zones"
    )
    zone_code = models.CharField(max_length=40)
    crop_name = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_IDLE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["greenhouse_id", "zone_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["greenhouse", "zone_code"],
                name="uniq_zone_code_per_greenhouse",
            )
        ]

    def __str__(self):
        return f"{self.greenhouse.name}/{self.zone_code}"


class ClimateLog(models.Model):
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="climate_logs")
    recorded_at = models.DateTimeField()
    temp_c = models.DecimalField(max_digits=5, decimal_places=2)
    humidity_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(20), MaxValueValidator(100)],
    )
    par_umol = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    co2_ppm = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"Climate@{self.zone_id} {self.recorded_at}"


class IrrigationCycle(models.Model):
    STATUS_SCHEDULED = "scheduled"
    STATUS_RUNNING = "running"
    STATUS_DONE = "done"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "已排程"),
        (STATUS_RUNNING, "进行中"),
        (STATUS_DONE, "已完成"),
        (STATUS_SKIPPED, "已跳过"),
    ]

    zone = models.ForeignKey(
        Zone, on_delete=models.CASCADE, related_name="irrigation_cycles"
    )
    start_at = models.DateTimeField()
    duration_min = models.PositiveIntegerField(default=30)
    water_liters = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_at"]

    def __str__(self):
        return f"Irrig@{self.zone_id} {self.start_at} ({self.status})"


class MoistureBatch(models.Model):
    """土壤含水抽检批次：挂在温室下，同温室批次号唯一。"""

    greenhouse = models.ForeignKey(
        Greenhouse, on_delete=models.CASCADE, related_name="moisture_batches"
    )
    batch_no = models.CharField(max_length=40)
    # 开批日按东八区自然日（settings.TIME_ZONE = Asia/Shanghai）
    open_date = models.DateField(default=timezone.localdate)
    sealed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-open_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["greenhouse", "batch_no"],
                name="uniq_moisture_batch_no_per_greenhouse",
            )
        ]

    def __str__(self):
        return f"{self.greenhouse.name}/{self.batch_no}"


class MoistureReading(models.Model):
    """含水测点：挂在批次下，分区须属于批次所在温室。"""

    batch = models.ForeignKey(
        MoistureBatch, on_delete=models.CASCADE, related_name="readings"
    )
    zone = models.ForeignKey(
        Zone, on_delete=models.CASCADE, related_name="moisture_readings"
    )
    moisture_pct = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(5), MaxValueValidator(95)]
    )
    sampled_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["batch_id", "zone__zone_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "zone"],
                name="uniq_moisture_reading_zone_per_batch",
            ),
            models.CheckConstraint(
                check=models.Q(moisture_pct__gte=5) & models.Q(moisture_pct__lte=95),
                name="moisture_reading_pct_between_5_95",
            ),
        ]

    def __str__(self):
        return f"Moisture@{self.batch_id}/{self.zone_id} {self.moisture_pct}%"
