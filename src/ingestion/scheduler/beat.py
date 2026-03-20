"""
Celery Beat Schedule Configuration

Defines periodic task schedules for automated weather data ingestion.
"""

from celery.schedules import crontab

# GFS schedule: poll at expected release times
# GFS 00Z data available ~04:30Z, poll starting at 04:00Z
GFS_SCHEDULE = {
    "00": crontab(hour=4, minute=0),
    "06": crontab(hour=10, minute=0),
    "12": crontab(hour=16, minute=0),
    "18": crontab(hour=22, minute=0),
}

# HRRR schedule: poll ~15 minutes past each hour
HRRR_SCHEDULE = crontab(minute=15)

# GOES schedule: poll every 5 minutes
GOES_SCHEDULE = crontab(minute="*/5")

# NEXRAD schedule: poll every 5 minutes
NEXRAD_SCHEDULE = crontab(minute="*/5")

# ASOS schedule: poll hourly
ASOS_SCHEDULE = crontab(minute=0)


def get_beat_schedule():
    """
    Generate Celery Beat schedule for all data sources.

    Returns:
        dict: Celery Beat schedule configuration
    """
    from .config import CELERY_BEAT_SCHEDULE

    return CELERY_BEAT_SCHEDULE


if __name__ == "__main__":
    # Print schedule
    print("GFS Schedule:")
    for cycle, schedule in GFS_SCHEDULE.items():
        print(f"  {cycle}Z: {schedule}")

    print(f"\nHRRR Schedule: {HRRR_SCHEDULE}")
    print(f"GOES Schedule: {GOES_SCHEDULE}")
    print(f"NEXRAD Schedule: {NEXRAD_SCHEDULE}")
    print(f"ASOS Schedule: {ASOS_SCHEDULE}")
