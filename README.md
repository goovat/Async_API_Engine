AsyncAPI Engine

Production-oriented asynchronous job processing API built with FastAPI, PostgreSQL, Redis, SQLAlchemy, and pytest.

AsyncAPI Engine is a backend engineering project demonstrating how to design and test a reliable asynchronous job-processing system with authentication, idempotency, retry control, Redis-backed queuing, worker processing, persistent job attempts, and automated tests.

The project focuses on the engineering problems that appear in real backend systems: duplicate requests, asynchronous processing, job state transitions, retry safety, failure handling, and concurrency-aware architecture.

Why This Project

Asynchronous systems must remain reliable when requests are duplicated, workers fail, jobs are retried, or processing does not complete successfully.

AsyncAPI Engine demonstrates a structured approach to these problems by separating:

- API routes
- business services
- repositories
- database models
- background workers
- Redis queue infrastructure
- authentication
- error handling
- observability
- automated tests

The goal is not simply to expose an API, but to demonstrate the engineering discipline required to build a maintainable backend processing system.

Core Features

Authentication

- User registration
- Password hashing with Argon2
- JWT authentication
- Protected API endpoints
- Current-user resolution
- Invalid credential handling

Asynchronous Job Processing

- Job creation through REST APIs
- Redis-backed job queue
- Dedicated worker implementation
- Job processor
- Persistent job state transitions
- Successful and failed execution handling

Idempotency

The API supports an "X-Idempotency-Key" request header to prevent duplicate processing of logically identical requests.

This demonstrates an important reliability pattern for APIs where clients may retry requests because of network failures or timeouts.

Retry Management

Failed jobs can be explicitly retried.

Retry handling includes:

- Only failed jobs can be retried
- Retry requests return the job to "pending"
- The job is re-enqueued
- Existing attempts are preserved
- Attempt numbers are tracked
- A maximum of three attempts is enforced
- Jobs that have reached the retry limit are rejected

Job Attempt Tracking

Each processing attempt is persisted separately.

An attempt records:

- Job ID
- Attempt number
- Processing status
- Error message
- Start timestamp
- Completion timestamp

This provides an auditable history of job execution rather than treating retries as invisible state changes.

Reliability-Oriented Worker Design

The worker:

1. Dequeues a job from Redis.
2. Creates a database session.
3. Passes the job to the processor.
4. Processes the job according to its current state.
5. Re-queues the job if an unexpected worker-level failure occurs.

The processor also prevents already-processing or completed jobs from being processed again.

API

Authentication

POST /auth/register
POST /auth/login
GET  /auth/me

Health

GET /health

Jobs

POST /jobs
GET  /jobs/{job_id}
GET  /jobs/{job_id}/status
POST /jobs/{job_id}/retry

Idempotent Job Creation

POST /jobs
X-Idempotency-Key: unique-request-key

The idempotency key allows clients to safely retry requests without unintentionally creating duplicate operations.

Architecture

                    ┌──────────────────┐
                    │      Client      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    FastAPI API   │
                    └────────┬─────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
        ┌───────────────┐        ┌────────────────┐
        │    Services   │        │ Authentication │
        └───────┬───────┘        └────────────────┘
                │
                ▼
        ┌───────────────┐
        │  Repositories │
        └───────┬───────┘
                │
        ┌───────┴────────┐
        ▼                ▼
 ┌──────────────┐  ┌──────────────┐
 │ PostgreSQL   │  │    Redis     │
 │              │  │    Queue     │
 └──────────────┘  └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    Worker    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ JobProcessor │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Job Attempts │
                    └──────────────┘

Request-to-Processing Flow

Client
  │
  │ POST /jobs
  ▼
FastAPI
  │
  ▼
JobService
  │
  ├── Idempotency check
  │
  ▼
PostgreSQL
  │
  ▼
Redis Queue
  │
  ▼
Worker
  │
  ▼
JobProcessor
  │
  ├── pending → processing
  │
  ├── success → completed
  │
  └── failure → failed
                  │
                  ▼
             RetryService
                  │
                  ▼
             pending → Redis

Technology Stack

Technology| Purpose
Python| Backend language
FastAPI| REST API framework
SQLAlchemy| Database ORM
PostgreSQL| Persistent relational database
Redis| Asynchronous job queue
Pydantic| Data validation and schemas
JWT| API authentication
Argon2| Password hashing
Alembic| Database migrations
pytest| Automated testing
pytest-asyncio| Async test support
Docker| Containerization

Project Structure

Async_API_Engine/
│
├── app/
│   ├── api/
│   │   ├── dependencies/
│   │   └── routes/
│   │
│   ├── config/
│   ├── database/
│   ├── exceptions/
│   ├── middleware/
│   ├── models/
│   ├── observability/
│   ├── redis/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── workers/
│   └── main.py
│
├── alembic/
├── tests/
│   ├── api/
│   ├── concurrency/
│   ├── integration/
│   ├── services/
│   └── workers/
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── pytest.ini
├── requirements.txt
└── README.md

Testing

The project currently has a comprehensive automated test suite covering API behavior, services, workers, concurrency, idempotency, authentication, job processing, and retry behavior.

Current verification:

53 passed

Run the complete test suite with:

pytest -q

Expected result:

53 passed

Focused test suites can also be executed independently:

pytest -q tests/services/test_retry_service.py
pytest -q tests/api/test_jobs.py
pytest -q tests/workers/test_job_processor.py

Reliability Guarantees Demonstrated

The project specifically tests and demonstrates:

- Duplicate-request protection
- Idempotency-key handling
- Job ownership checks
- Valid job state transitions
- Duplicate processing prevention
- Failed-job retry restrictions
- Maximum retry enforcement
- Attempt-number tracking
- Failed attempt recording
- Successful attempt recording
- Worker re-queue behavior
- Authentication failures
- Missing-resource handling
- Concurrent job behavior

Configuration

Configuration is provided through environment variables.

Example:

APP_NAME=AsyncAPI Engine
APP_VERSION=0.1.0
DEBUG=false

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/asyncapi_engine
REDIS_URL=redis://localhost:6379/0

JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

Copy the example configuration:

cp .env.example .env

Replace the development credentials and secrets before running the application.

Local Development

Create and activate a virtual environment:

python -m venv venv
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Run database migrations:

alembic upgrade head

Start the API:

uvicorn app.main:app --reload

The FastAPI application exposes interactive API documentation through its standard OpenAPI interface.

Engineering Principles

This project follows several backend engineering principles:

Separation of Concerns

API routes are kept thin while business logic lives inside dedicated services.

Repository Pattern

Database access is isolated behind repository classes instead of being scattered throughout the API layer.

Explicit State Management

Jobs move through explicit processing states:

pending
   │
   ▼
processing
   │
   ├──────────────► completed
   │
   └──────────────► failed
                         │
                         ▼
                      pending

Failure-Aware Processing

Failures are persisted rather than silently discarded.

Idempotent API Design

Requests that may be retried by clients are protected against accidental duplication.

Test-Driven Reliability

Important failure paths are covered by automated tests rather than relying exclusively on manual verification.

Portfolio Relevance

AsyncAPI Engine is designed as a backend engineering portfolio project demonstrating practical experience with:

- Python backend development
- FastAPI
- asynchronous programming
- REST API design
- PostgreSQL
- SQLAlchemy
- Redis
- background workers
- authentication
- JWT
- idempotency
- retry systems
- concurrency
- failure handling
- database persistence
- repository/service architecture
- automated testing
- API reliability

The project is particularly relevant to backend roles involving distributed systems, financial technology, payment infrastructure, APIs, asynchronous processing, and reliability engineering.

Project Status

Status: Active portfolio project

Core asynchronous job processing, authentication, idempotency, retry handling, Redis queue integration, worker processing, and automated testing are implemented.

The project is being developed incrementally with a focus on maintaining a verified test baseline as new reliability features are introduced.

Author

Ovie Godday Atadede

Python Backend / Software Engineer

Primary focus:

Python
FastAPI
Django
Django REST Framework
PostgreSQL
Redis
Async Systems
REST APIs
Payment Infrastructure
Idempotency
Concurrency
Automated Testing

---

Portfolio Note

This repository is intended to demonstrate engineering ability through working code, architecture, tests, and reliability patterns rather than simply listing technologies.

The strongest evidence in the repository is the combination of:

architecture + implementation + failure handling + automated tests + incremental Git history.