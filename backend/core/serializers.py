from rest_framework import serializers

from .models import (
    ClimateLog,
    Greenhouse,
    IrrigationCycle,
    MoistureBatch,
    MoistureReading,
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
    batchNo = serializers.CharField(source="batch_no")
    openDate = serializers.DateField(source="open_date", required=False)
    sealedAt = serializers.DateTimeField(source="sealed_at", read_only=True)
    greenhouseName = serializers.CharField(source="greenhouse.name", read_only=True)
    readingCount = serializers.SerializerMethodField()

    class Meta:
        model = MoistureBatch
        fields = (
            "id",
            "greenhouseId",
            "greenhouseName",
            "batchNo",
            "openDate",
            "sealedAt",
            "readingCount",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "greenhouseName",
            "sealedAt",
            "readingCount",
            "created_at",
            "updated_at",
        )

    def get_readingCount(self, obj):
        if hasattr(obj, "reading_count"):
            return obj.reading_count
        return obj.readings.count()

    def validate(self, attrs):
        greenhouse = attrs.get("greenhouse") or getattr(self.instance, "greenhouse", None)
        batch_no = attrs.get("batch_no") or getattr(self.instance, "batch_no", None)
        if greenhouse and batch_no:
            qs = MoistureBatch.objects.filter(greenhouse=greenhouse, batch_no=batch_no)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"batchNo": "同一温室内批次号必须唯一"}
                )
        return attrs


class MoistureReadingSerializer(serializers.ModelSerializer):
    batchId = serializers.PrimaryKeyRelatedField(
        source="batch", queryset=MoistureBatch.objects.all()
    )
    zoneId = serializers.PrimaryKeyRelatedField(
        source="zone", queryset=Zone.objects.all()
    )
    moisturePct = serializers.IntegerField(source="moisture_pct")
    sampledAt = serializers.DateTimeField(source="sampled_at")
    batchNo = serializers.CharField(source="batch.batch_no", read_only=True)
    zoneCode = serializers.CharField(source="zone.zone_code", read_only=True)
    greenhouseName = serializers.CharField(
        source="batch.greenhouse.name", read_only=True
    )

    class Meta:
        model = MoistureReading
        fields = (
            "id",
            "batchId",
            "batchNo",
            "zoneId",
            "zoneCode",
            "greenhouseName",
            "moisturePct",
            "sampledAt",
            "created_at",
        )
        read_only_fields = (
            "id",
            "batchNo",
            "zoneCode",
            "greenhouseName",
            "created_at",
        )

    def validate_moisturePct(self, value):
        if value < 5 or value > 95:
            raise serializers.ValidationError("含水百分数须为 5～95 的整数")
        return value

    def validate(self, attrs):
        batch = attrs.get("batch") or getattr(self.instance, "batch", None)
        zone = attrs.get("zone") or getattr(self.instance, "zone", None)
        if batch and batch.sealed_at is not None:
            raise serializers.ValidationError({"batchId": "批次已封批，禁止加点"})
        if batch and zone and zone.greenhouse_id != batch.greenhouse_id:
            raise serializers.ValidationError(
                {"zoneId": "分区不属于该批次所在温室，禁止串棚"}
            )
        if batch and zone:
            qs = MoistureReading.objects.filter(batch=batch, zone=zone)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"zoneId": "该批次内此分区已有测点"}
                )
        return attrs
