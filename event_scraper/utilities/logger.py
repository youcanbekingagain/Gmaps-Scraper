import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class ProjectLogger:
    _instance: Optional["ProjectLogger"] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if not ProjectLogger._initialized:
            # Create logs directory if it doesn't exist
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)

            # Create log filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file = log_dir / f"scraper_{timestamp}.log"

            # Create formatter
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            # File handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)

            # Configure root logger
            root_logger = logging.getLogger("event_scraper")
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

            ProjectLogger._initialized = True

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for the specified module.

        Args:
            name: Usually __name__ from the calling module

        Returns:
            A configured logger instance
        """
        # Create logger with the full path (event_scraper.module.submodule)
        if name == "__main__":
            logger_name = "event_scraper"
        else:
            logger_name = f"event_scraper.{name}"

        return logging.getLogger(logger_name)


# Global instance
project_logger = ProjectLogger()
