from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClimateLogViewSet,
    GreenhouseViewSet,
    IrrigationCycleViewSet,
    MoistureBatchViewSet,
    MoistureReadingViewSet,
    ZoneViewSet,
    dashboard_stats,
)

router = DefaultRouter()
router.register("greenhouses", GreenhouseViewSet, basename="greenhouse")
router.register("zones", ZoneViewSet, basename="zone")
router.register("climate-logs", ClimateLogViewSet, basename="climate-log")
router.register("irrigation-cycles", IrrigationCycleViewSet, basename="irrigation-cycle")
router.register("moisture-batches", MoistureBatchViewSet, basename="moisture-batch")
router.register("moisture-readings", MoistureReadingViewSet, basename="moisture-reading")

urlpatterns = [
    path("dashboard/", dashboard_stats, name="dashboard"),
    path("", include(router.urls)),
]
