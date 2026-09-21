from rest_framework import serializers

from .models import (
    ClimateLog,
    Greenhouse,
    IrrigationCycle,
    MoistureBatch,
    MoistureSample,
    Zone,
)


class GreenhouseSerializer(serializers.ModelSerializer):
    areaM2 = serializers.DecimalField(
        source="area_m2", max_digits=10, decimal_places=2
    )
    zoneCount = serializers.SerializerMethodField()

    class Meta:
        model = Greenhouse
        fields = (
            "id",
            "name",
            "location",
            "areaM2",
            "notes",
            "zoneCount",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "zoneCount", "created_at", "updated_at")

    def get_zoneCount(self, obj):
        if hasattr(obj, "zone_count"):
            return obj.zone_count
        return obj.zones.count()


class ZoneSerializer(serializers.ModelSerializer):
    greenhouseId = serializers.PrimaryKeyRelatedField(
        source="greenhouse", queryset=Greenhouse.objects.all()
    )
    zoneCode = serializers.CharField(source="zone_code")
    cropName = serializers.CharField(source="crop_name", allow_blank=True, required=False)
    greenhouseName = serializers.CharField(source="greenhouse.name", read_only=True)

    class Meta:
        model = Zone
        fields = (
            "id",
            "greenhouseId",
            "greenhouseName",
            "zoneCode",
            "cropName",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "greenhouseName", "created_at", "updated_at")

    def validate(self, attrs):
        greenhouse = attrs.get("greenhouse") or getattr(self.instance, "greenhouse", None)
        zone_code = attrs.get("zone_code") or getattr(self.instance, "zone_code", None)
        if greenhouse and zone_code:
            qs = Zone.objects.filter(greenhouse=greenhouse, zone_code=zone_code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"zoneCode": "同一温室内分区编码必须唯一"}
                )
        return attrs


class ClimateLogSerializer(serializers.ModelSerializer):
    zoneId = serializers.PrimaryKeyRelatedField(
        source="zone", queryset=Zone.objects.all()
    )
    recordedAt = serializers.DateTimeField(source="recorded_at")
    tempC = serializers.DecimalField(source="temp_c", max_digits=5, decimal_places=2)
    humidityPct = serializers.DecimalField(
        source="humidity_pct", max_digits=5, decimal_places=2
    )
    parUmol = serializers.DecimalField(
        source="par_umol", max_digits=8, decimal_places=2, required=False
    )
    co2Ppm = serializers.DecimalField(
        source="co2_ppm", max_digits=8, decimal_places=2, required=False
    )
    zoneCode = serializers.CharField(source="zone.zone_code", read_only=True)
    greenhouseName = serializers.CharField(
        source="zone.greenhouse.name", read_only=True
    )

    class Meta:
        model = ClimateLog
        fields = (
            "id",
            "zoneId",
            "zoneCode",
            "greenhouseName",
            "recordedAt",
            "tempC",
            "humidityPct",
            "parUmol",
            "co2Ppm",
            "created_at",
        )
        read_only_fields = ("id", "zoneCode", "greenhouseName", "created_at")

    def validate_humidityPct(self, value):
        if value < 20 or value > 100:
            raise serializers.ValidationError("湿度须在 20～100 之间")
        return value


class IrrigationCycleSerializer(serializers.ModelSerializer):
    zoneId = serializers.PrimaryKeyRelatedField(
        source="zone", queryset=Zone.objects.all()
    )
    startAt = serializers.DateTimeField(source="start_at")
    durationMin = serializers.IntegerField(source="duration_min")
    waterLiters = serializers.DecimalField(
        source="water_liters", max_digits=10, decimal_places=2
    )
    zoneCode = serializers.CharField(source="zone.zone_code", read_only=True)
    greenhouseName = serializers.CharField(
        source="zone.greenhouse.name", read_only=True
    )

    class Meta:
        model = IrrigationCycle
        fields = (
            "id",
            "zoneId",
            "zoneCode",
            "greenhouseName",
            "startAt",
            "durationMin",
            "waterLiters",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "zoneCode",
            "greenhouseName",
            "created_at",
            "updated_at",
        )


class MoistureBatchSerializer(serializers.ModelSerializer):
    greenhouseId = serializers.PrimaryKeyRelatedField(
        source="greenhouse", queryset=Greenhouse.objects.all()
    )
    batchCode = serializers.CharField(source="batch_code")
    openedOn = serializers.DateField(source="opened_on")
    closedAt = serializers.DateTimeField(source="closed_at", read_only=True)
    greenhouseName = serializers.CharField(source="greenhouse.name", read_only=True)
    sampleCount = serializers.SerializerMethodField()

    class Meta:
        model = MoistureBatch
        fields = (
            "id",
            "greenhouseId",
            "greenhouseName",
            "batchCode",
            "openedOn",
            "closedAt",
            "sampleCount",
            "created_at",
        )
        read_only_fields = ("id", "greenhouseName", "closedAt", "sampleCount", "created_at")

    def get_sampleCount(self, obj):
        if hasattr(obj, "sample_count"):
            return obj.sample_count
        return obj.samples.count()

    def validate(self, attrs):
        greenhouse = attrs.get("greenhouse") or getattr(self.instance, "greenhouse", None)
        batch_code = attrs.get("batch_code") or getattr(self.instance, "batch_code", None)
        if greenhouse and batch_code:
            qs = MoistureBatch.objects.filter(greenhouse=greenhouse, batch_code=batch_code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"batchCode": "同一温室内批次号必须唯一（跨温室可重复）"}
                )
        return attrs


class MoistureSampleSerializer(serializers.ModelSerializer):
    batchId = serializers.PrimaryKeyRelatedField(
        source="batch", queryset=MoistureBatch.objects.all()
    )
    zoneId = serializers.PrimaryKeyRelatedField(
        source="zone", queryset=Zone.objects.all()
    )
    moisturePct = serializers.IntegerField(source="moisture_pct", min_value=5, max_value=95)
    sampledAt = serializers.DateTimeField(source="sampled_at")
    zoneCode = serializers.CharField(source="zone.zone_code", read_only=True)
    greenhouseName = serializers.CharField(
        source="zone.greenhouse.name", read_only=True
    )

    class Meta:
        model = MoistureSample
        fields = (
            "id",
            "batchId",
            "zoneId",
            "zoneCode",
            "greenhouseName",
            "moisturePct",
            "sampledAt",
            "created_at",
        )
        read_only_fields = ("id", "zoneCode", "greenhouseName", "created_at")

    def validate(self, attrs):
        batch = attrs.get("batch") or getattr(self.instance, "batch", None)
        zone = attrs.get("zone") or getattr(self.instance, "zone", None)
        if batch and zone:
            if zone.greenhouse_id != batch.greenhouse_id:
                raise serializers.ValidationError(
                    {"zoneId": "分区不属于该批次所属温室，不得串棚"}
                )
            if batch.closed_at is not None:
                raise serializers.ValidationError(
                    {"batchId": "批次已封批，禁止再添加测点"}
                )
            qs = MoistureSample.objects.filter(batch=batch, zone=zone)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"zoneId": "未封批次内同一分区只允许一个测点"}
                )
        return attrs
