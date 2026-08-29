import asyncio

from app.workers.worker import Worker


def main() -> None:
    asyncio.run(Worker().run_forever())


if __name__ == "__main__":
    main()
