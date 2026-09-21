from django.contrib import admin

from .models import (
    ClimateLog,
    Greenhouse,
    IrrigationCycle,
    MoistureBatch,
    MoistureReading,
    Zone,
)


@admin.register(Greenhouse)
class GreenhouseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location", "area_m2")
    search_fields = ("name", "location")


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("id", "greenhouse", "zone_code", "crop_name", "status")
    list_filter = ("status", "greenhouse")
    search_fields = ("zone_code", "crop_name")


@admin.register(ClimateLog)
class ClimateLogAdmin(admin.ModelAdmin):
    list_display = ("id", "zone", "recorded_at", "temp_c", "humidity_pct", "par_umol", "co2_ppm")
    list_filter = ("zone",)


@admin.register(IrrigationCycle)
class IrrigationCycleAdmin(admin.ModelAdmin):
    list_display = ("id", "zone", "start_at", "duration_min", "water_liters", "status")
    list_filter = ("status", "zone")


@admin.register(MoistureBatch)
class MoistureBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "greenhouse", "batch_no", "open_date", "sealed_at")
    list_filter = ("greenhouse", "open_date")
    search_fields = ("batch_no",)


@admin.register(MoistureReading)
class MoistureReadingAdmin(admin.ModelAdmin):
    list_display = ("id", "batch", "zone", "moisture_pct", "sampled_at")
    list_filter = ("batch", "zone")
