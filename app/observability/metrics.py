from prometheus_client import Counter, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "asyncapi_http_requests_total",
    "Total number of HTTP requests.",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "asyncapi_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
)

JOBS_PROCESSED_TOTAL = Counter(
    "asyncapi_jobs_processed_total",
    "Total number of jobs processed.",
    ["status"],
)

JOB_ATTEMPTS_TOTAL = Counter(
    "asyncapi_job_attempts_total",
    "Total number of job attempts.",
    ["status"],
)
