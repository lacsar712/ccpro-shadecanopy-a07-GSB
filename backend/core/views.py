from datetime import timedelta

from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ClimateLog, Greenhouse, IrrigationCycle, MoistureBatch, MoistureSample, Zone
from .serializers import (
    ClimateLogSerializer,
    GreenhouseSerializer,
    IrrigationCycleSerializer,
    MoistureBatchSerializer,
    MoistureSampleSerializer,
    ZoneSerializer,
)


class GreenhouseViewSet(viewsets.ModelViewSet):
    queryset = Greenhouse.objects.annotate(zone_count=Count("zones")).all()
    serializer_class = GreenhouseSerializer


class ZoneViewSet(viewsets.ModelViewSet):
    serializer_class = ZoneSerializer

    def get_queryset(self):
        qs = Zone.objects.select_related("greenhouse").all()
        greenhouse_id = self.request.query_params.get("greenhouseId")
        status = self.request.query_params.get("status")
        if greenhouse_id:
            qs = qs.filter(greenhouse_id=greenhouse_id)
        if status:
            qs = qs.filter(status=status)
        return qs


class ClimateLogViewSet(viewsets.ModelViewSet):
    serializer_class = ClimateLogSerializer

    def get_queryset(self):
        qs = ClimateLog.objects.select_related("zone", "zone__greenhouse").all()
        zone_id = self.request.query_params.get("zoneId")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        return qs


class IrrigationCycleViewSet(viewsets.ModelViewSet):
    serializer_class = IrrigationCycleSerializer

    def get_queryset(self):
        qs = IrrigationCycle.objects.select_related("zone", "zone__greenhouse").all()
        zone_id = self.request.query_params.get("zoneId")
        status = self.request.query_params.get("status")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        if status:
            qs = qs.filter(status=status)
        return qs


class MoistureBatchViewSet(viewsets.ModelViewSet):
    serializer_class = MoistureBatchSerializer

    def get_queryset(self):
        qs = (
            MoistureBatch.objects.select_related("greenhouse")
            .annotate(sample_count=Count("samples"))
            .order_by("-opened_on", "-id")
            .all()
        )
        greenhouse_id = self.request.query_params.get("greenhouseId")
        if greenhouse_id:
            qs = qs.filter(greenhouse_id=greenhouse_id)
        return qs

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """封批：箱内至少两个测点，否则 409 且封批时刻保持为空。"""
        with transaction.atomic():
            batch = get_object_or_404(
                MoistureBatch.objects.select_for_update(), pk=pk
            )
            if batch.closed_at is not None:
                return Response(MoistureBatchSerializer(batch).data)
            point_count = batch.samples.count()
            if point_count < 2:
                return Response(
                    {
                        "detail": f"封批失败：箱内至少需要 2 个测点，当前 {point_count} 个",
                        "sampleCount": point_count,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            batch.closed_at = timezone.now()
            batch.save(update_fields=["closed_at"])
        batch = self.get_queryset().get(pk=pk)
        return Response(MoistureBatchSerializer(batch).data)


class MoistureSampleViewSet(viewsets.ModelViewSet):
    serializer_class = MoistureSampleSerializer

    def get_queryset(self):
        qs = MoistureSample.objects.select_related(
            "batch", "zone", "zone__greenhouse"
        ).all()
        batch_id = self.request.query_params.get("batchId")
        zone_id = self.request.query_params.get("zoneId")
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def moisture_reconciliation(request):
    """按温室对账：批次数、点数与明细实际计数，差额须为 0。"""
    greenhouse_id = request.query_params.get("greenhouseId")
    greenhouses = Greenhouse.objects.all()
    if greenhouse_id:
        greenhouses = greenhouses.filter(pk=greenhouse_id)

    # 批次侧聚合：批次数 + 经批次关联数出的点数
    batch_rows = MoistureBatch.objects.values("greenhouse_id").annotate(
        batch_count=Count("id", distinct=True),
        sample_count=Count("samples"),
    )
    batch_agg = {row["greenhouse_id"]: row for row in batch_rows}

    # 明细侧聚合：直接数测点记录
    detail_rows = MoistureSample.objects.values("batch__greenhouse_id").annotate(
        detail_count=Count("id")
    )
    detail_agg = {row["batch__greenhouse_id"]: row["detail_count"] for row in detail_rows}

    results = []
    for g in greenhouses.order_by("id"):
        agg = batch_agg.get(g.id)
        sample_count = agg["sample_count"] if agg else 0
        detail_count = detail_agg.get(g.id, 0)
        results.append(
            {
                "greenhouseId": g.id,
                "greenhouseName": g.name,
                "batchCount": agg["batch_count"] if agg else 0,
                "sampleCount": sample_count,
                "detailSampleCount": detail_count,
                "diff": sample_count - detail_count,
            }
        )
    return Response({"results": results})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    now = timezone.now()
    since_24h = now - timedelta(hours=24)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    data = {
        "greenhouseCount": Greenhouse.objects.count(),
        "growingZoneCount": Zone.objects.filter(status=Zone.STATUS_GROWING).count(),
        "climateLogLast24h": ClimateLog.objects.filter(
            recorded_at__gte=since_24h
        ).count(),
        "irrigationScheduledToday": IrrigationCycle.objects.filter(
            status=IrrigationCycle.STATUS_SCHEDULED,
            start_at__gte=today_start,
            start_at__lt=today_end,
        ).count(),
    }
    return Response(data)
