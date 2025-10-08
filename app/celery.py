from celery import Celery

from app.core.config import settings

app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Task Serialization
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.enable_utc = True

# Task Execution Settings
app.conf.task_track_started = True  # Track when tasks start
app.conf.task_time_limit = 600  # Hard timeout: 10 minutes
app.conf.task_soft_time_limit = 540  # Soft timeout: 9 minutes (raises exception)
app.conf.task_acks_late = True  # Acknowledge tasks after completion (safer)
app.conf.task_reject_on_worker_lost = True  # Reject tasks if worker dies
app.conf.worker_prefetch_multiplier = 1  # Process one task at a time

# Result Backend Settings
app.conf.result_expires = 3600  # Keep results for 1 hour
app.conf.result_extended = True  # Store more task metadata
app.conf.result_backend_transport_options = {
    "retry_on_timeout": True,
    "max_connections": 10,
}

# Broker Settings - CRITICAL FOR LONG-RUNNING TASKS
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_transport_options = {
    "visibility_timeout": 43200,  # 12 hours - tasks won't timeout in queue
    "max_connections": 10,
    "retry_on_timeout": True,
    "health_check_interval": 10,
}

# Redis Backend Settings - EXTENDED TIMEOUTS
# Note: These are applied via result_backend_transport_options instead
# to avoid connection issues

# Worker Settings
app.conf.worker_max_tasks_per_child = (
    50  # Restart worker after 50 tasks (memory cleanup)
)
app.conf.worker_disable_rate_limits = False
app.conf.worker_send_task_events = True  # Enable events for monitoring
app.conf.task_send_sent_event = True

# Event Settings (for monitoring with Flower)
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# Beat Settings (if using periodic tasks)
app.conf.beat_scheduler = "celery.beat:PersistentScheduler"

app.autodiscover_tasks(["app.tasks"])

from app.tasks import analysis_task  # noqa
