from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    ClimateLog,
    Greenhouse,
    IrrigationCycle,
    MoistureBatch,
    MoistureReading,
    Zone,
)
from .serializers import (
    ClimateLogSerializer,
    GreenhouseSerializer,
    IrrigationCycleSerializer,
    MoistureBatchSerializer,
    MoistureReadingSerializer,
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


class MoistureBatchViewSet(viewsets.ModelViewSet):
    serializer_class = MoistureBatchSerializer

    def get_queryset(self):
        qs = (
            MoistureBatch.objects.select_related("greenhouse")
            .annotate(reading_count=Count("readings"))
            .order_by("-open_date", "-id")
        )
        greenhouse_id = self.request.query_params.get("greenhouseId")
        sealed = self.request.query_params.get("sealed")
        if greenhouse_id:
            qs = qs.filter(greenhouse_id=greenhouse_id)
        if sealed in ("true", "false"):
            qs = qs.filter(sealed_at__isnull=(sealed == "false"))
        return qs

    @action(detail=True, methods=["post"])
    def seal(self, request, pk=None):
        """封批：箱内至少两个测点，否则 409 且封批时刻保持为空。"""
        batch = self.get_object()
        if batch.sealed_at is not None:
            return Response(self.get_serializer(batch).data)
        point_count = batch.readings.count()
        if point_count < 2:
            return Response(
                {
                    "detail": "箱内测点不足两点，无法封批",
                    "pointCount": point_count,
                    "sealedAt": None,
                },
                status=status.HTTP_409_CONFLICT,
            )
        batch.sealed_at = timezone.now()
        batch.save(update_fields=["sealed_at", "updated_at"])
        return Response(self.get_serializer(batch).data)

    @action(detail=False, methods=["get"])
    def reconcile(self, request):
        """按温室对账：汇总口径与明细口径分别计数，差值须为 0。"""
        greenhouse_id = request.query_params.get("greenhouseId")
        greenhouses = Greenhouse.objects.all().order_by("id")
        if greenhouse_id:
            greenhouses = greenhouses.filter(pk=greenhouse_id)

        # 汇总口径：批次表 SQL 聚合
        summary_batches = {
            row["greenhouse_id"]: row["c"]
            for row in MoistureBatch.objects.values("greenhouse_id").annotate(
                c=Count("id")
            )
        }
        summary_points = {
            row["greenhouse_id"]: row["c"]
            for row in MoistureBatch.objects.values("greenhouse_id").annotate(
                c=Count("readings")
            )
        }
        # 明细口径：逐行清点批次、直查明细表计数
        detail_batches = {}
        for batch in MoistureBatch.objects.all():
            detail_batches[batch.greenhouse_id] = (
                detail_batches.get(batch.greenhouse_id, 0) + 1
            )
        detail_points = {
            row["batch__greenhouse_id"]: row["c"]
            for row in MoistureReading.objects.values(
                "batch__greenhouse_id"
            ).annotate(c=Count("id"))
        }

        results = []
        for g in greenhouses:
            batch_count = summary_batches.get(g.id, 0)
            point_count = summary_points.get(g.id, 0)
            detail_batch_count = detail_batches.get(g.id, 0)
            detail_point_count = detail_points.get(g.id, 0)
            results.append(
                {
                    "greenhouseId": g.id,
                    "greenhouseName": g.name,
                    "batchCount": batch_count,
                    "pointCount": point_count,
                    "detailBatchCount": detail_batch_count,
                    "detailPointCount": detail_point_count,
                    "batchDiff": batch_count - detail_batch_count,
                    "pointDiff": point_count - detail_point_count,
                }
            )
        return Response(results)


class MoistureReadingViewSet(viewsets.ModelViewSet):
    serializer_class = MoistureReadingSerializer

    def get_queryset(self):
        qs = MoistureReading.objects.select_related(
            "batch", "batch__greenhouse", "zone"
        ).all()
        batch_id = self.request.query_params.get("batchId")
        zone_id = self.request.query_params.get("zoneId")
        greenhouse_id = self.request.query_params.get("greenhouseId")
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        if greenhouse_id:
            qs = qs.filter(batch__greenhouse_id=greenhouse_id)
        return qs

    def create(self, request, *args, **kwargs):
        batch = MoistureBatch.objects.filter(pk=request.data.get("batchId")).first()
        if batch is not None and batch.sealed_at is not None:
            return Response(
                {"detail": "批次已封批，禁止加点"},
                status=status.HTTP_409_CONFLICT,
            )
        return super().create(request, *args, **kwargs)
