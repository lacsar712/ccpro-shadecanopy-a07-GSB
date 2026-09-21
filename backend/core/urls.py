from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClimateLogViewSet,
    GreenhouseViewSet,
    IrrigationCycleViewSet,
    MoistureBatchViewSet,
    MoistureSampleViewSet,
    ZoneViewSet,
    dashboard_stats,
    moisture_reconciliation,
)

router = DefaultRouter()
router.register("greenhouses", GreenhouseViewSet, basename="greenhouse")
router.register("zones", ZoneViewSet, basename="zone")
router.register("climate-logs", ClimateLogViewSet, basename="climate-log")
router.register("irrigation-cycles", IrrigationCycleViewSet, basename="irrigation-cycle")
router.register("moisture-batches", MoistureBatchViewSet, basename="moisture-batch")
router.register("moisture-samples", MoistureSampleViewSet, basename="moisture-sample")

urlpatterns = [
    path("dashboard/", dashboard_stats, name="dashboard"),
    path("moisture-reconciliation/", moisture_reconciliation, name="moisture-reconciliation"),
    path("", include(router.urls)),
]
