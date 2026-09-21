from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    ClimateLog,
    Greenhouse,
    IrrigationCycle,
    MoistureBatch,
    MoistureSample,
    Zone,
)

User = get_user_model()


class Command(BaseCommand):
    help = "初始化演示账号与温室气候/轮灌种子数据"

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@shadecanopy.local",
                "role": User.ROLE_ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password("123456")
        admin.role = User.ROLE_ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        self.stdout.write(self.style.SUCCESS(f"admin {'created' if created else 'updated'}"))

        grower, created = User.objects.get_or_create(
            username="grower",
            defaults={
                "email": "grower@shadecanopy.local",
                "role": User.ROLE_GROWER,
            },
        )
        grower.set_password("123456")
        grower.role = User.ROLE_GROWER
        grower.save()
        self.stdout.write(self.style.SUCCESS(f"grower {'created' if created else 'updated'}"))

        if Greenhouse.objects.exists():
            self.stdout.write("温室数据已存在，跳过业务种子写入。")
            self.seed_moisture_batches()
            return

        g1 = Greenhouse.objects.create(
            name="东坡一号棚",
            location="东区 A 排",
            area_m2=Decimal("1200.00"),
            notes="番茄与叶菜混作示范棚",
        )
        g2 = Greenhouse.objects.create(
            name="西篱二号棚",
            location="西区 B 排",
            area_m2=Decimal("860.50"),
            notes="草莓高架栽培",
        )

        z1 = Zone.objects.create(
            greenhouse=g1, zone_code="A-01", crop_name="樱桃番茄", status=Zone.STATUS_GROWING
        )
        z2 = Zone.objects.create(
            greenhouse=g1, zone_code="A-02", crop_name="油麦菜", status=Zone.STATUS_GROWING
        )
        z3 = Zone.objects.create(
            greenhouse=g1, zone_code="A-03", crop_name="", status=Zone.STATUS_IDLE
        )
        z4 = Zone.objects.create(
            greenhouse=g2, zone_code="B-01", crop_name="红颜草莓", status=Zone.STATUS_GROWING
        )
        z5 = Zone.objects.create(
            greenhouse=g2, zone_code="B-02", crop_name="章姬草莓", status=Zone.STATUS_FALLOW
        )

        now = timezone.now()
        ClimateLog.objects.bulk_create(
            [
                ClimateLog(
                    zone=z1,
                    recorded_at=now - timedelta(hours=2),
                    temp_c=Decimal("24.50"),
                    humidity_pct=Decimal("68.00"),
                    par_umol=Decimal("420.00"),
                    co2_ppm=Decimal("650.00"),
                ),
                ClimateLog(
                    zone=z1,
                    recorded_at=now - timedelta(hours=6),
                    temp_c=Decimal("22.10"),
                    humidity_pct=Decimal("72.50"),
                    par_umol=Decimal("180.00"),
                    co2_ppm=Decimal("700.00"),
                ),
                ClimateLog(
                    zone=z2,
                    recorded_at=now - timedelta(hours=3),
                    temp_c=Decimal("23.80"),
                    humidity_pct=Decimal("70.00"),
                    par_umol=Decimal("390.00"),
                    co2_ppm=Decimal("620.00"),
                ),
                ClimateLog(
                    zone=z4,
                    recorded_at=now - timedelta(hours=1),
                    temp_c=Decimal("21.20"),
                    humidity_pct=Decimal("75.00"),
                    par_umol=Decimal("350.00"),
                    co2_ppm=Decimal("580.00"),
                ),
                ClimateLog(
                    zone=z4,
                    recorded_at=now - timedelta(hours=20),
                    temp_c=Decimal("18.60"),
                    humidity_pct=Decimal("80.00"),
                    par_umol=Decimal("50.00"),
                    co2_ppm=Decimal("720.00"),
                ),
            ]
        )

        today = now.replace(hour=9, minute=0, second=0, microsecond=0)
        IrrigationCycle.objects.bulk_create(
            [
                IrrigationCycle(
                    zone=z1,
                    start_at=today + timedelta(hours=1),
                    duration_min=25,
                    water_liters=Decimal("180.00"),
                    status=IrrigationCycle.STATUS_SCHEDULED,
                ),
                IrrigationCycle(
                    zone=z2,
                    start_at=today + timedelta(hours=2),
                    duration_min=20,
                    water_liters=Decimal("120.00"),
                    status=IrrigationCycle.STATUS_SCHEDULED,
                ),
                IrrigationCycle(
                    zone=z4,
                    start_at=today - timedelta(hours=3),
                    duration_min=30,
                    water_liters=Decimal("95.00"),
                    status=IrrigationCycle.STATUS_DONE,
                ),
                IrrigationCycle(
                    zone=z1,
                    start_at=today - timedelta(days=1, hours=2),
                    duration_min=25,
                    water_liters=Decimal("175.00"),
                    status=IrrigationCycle.STATUS_DONE,
                ),
                IrrigationCycle(
                    zone=z5,
                    start_at=today + timedelta(hours=4),
                    duration_min=15,
                    water_liters=Decimal("40.00"),
                    status=IrrigationCycle.STATUS_SKIPPED,
                ),
            ]
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"种子完成：温室 {Greenhouse.objects.count()}，分区 {Zone.objects.count()}，"
                f"气候 {ClimateLog.objects.count()}，轮灌 {IrrigationCycle.objects.count()}"
            )
        )

        self.seed_moisture_batches()

    def seed_moisture_batches(self):
        """含水抽检种子幂等写入：同号批次两棚各一，一个可封一个不可封。"""
        g1 = Greenhouse.objects.filter(name="东坡一号棚").first()
        g2 = Greenhouse.objects.filter(name="西篱二号棚").first()
        if g1 is None or g2 is None:
            self.stdout.write("缺少示范温室，跳过含水抽检种子。")
            return
        z1 = Zone.objects.filter(greenhouse=g1, zone_code="A-01").first()
        z2 = Zone.objects.filter(greenhouse=g1, zone_code="A-02").first()
        z4 = Zone.objects.filter(greenhouse=g2, zone_code="B-01").first()
        if z1 is None or z2 is None or z4 is None:
            self.stdout.write("缺少示范分区，跳过含水抽检种子。")
            return

        now = timezone.now()
        opened_on = timezone.localdate()
        seeding_code = "SM-20260921-01"

        # 东坡一号棚同号批次：两个测点，可封批
        batch_seedable, created = MoistureBatch.objects.get_or_create(
            greenhouse=g1,
            batch_code=seeding_code,
            defaults={"opened_on": opened_on},
        )
        if created:
            MoistureSample.objects.bulk_create(
                [
                    MoistureSample(
                        batch=batch_seedable,
                        zone=z1,
                        moisture_pct=42,
                        sampled_at=now - timedelta(minutes=40),
                    ),
                    MoistureSample(
                        batch=batch_seedable,
                        zone=z2,
                        moisture_pct=57,
                        sampled_at=now - timedelta(minutes=30),
                    ),
                ]
            )

        # 西篱二号棚同号批次：仅一个测点，不可封批（封批接口应返回 409）
        batch_short, created = MoistureBatch.objects.get_or_create(
            greenhouse=g2,
            batch_code=seeding_code,
            defaults={"opened_on": opened_on},
        )
        if created:
            MoistureSample.objects.create(
                batch=batch_short,
                zone=z4,
                moisture_pct=38,
                sampled_at=now - timedelta(minutes=20),
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"含水抽检：批次 {MoistureBatch.objects.count()}，"
                f"测点 {MoistureSample.objects.count()}（同号批次 {seeding_code} 两棚各一）"
            )
        )
