import logging
from sys import stdout


class ITDFormatter(logging.Formatter):
    def __init__(
        self, fmt: str | None = None, colorful: bool = True
    ) -> None:
        super().__init__(fmt, "%Y-%m-%d %H:%M:%S")
        self.colorful = colorful

    def format(self, record):
        if self.colorful:
            record.display_name = f"[bold]{record.name}:[/bold] "
        else:
            record.display_name = f"{record.name}: "
        return super().format(record)


def setup_logging(level: str = "INFO", colorful: bool | None = None) -> logging.Logger:
    level = level.upper()

    base_logger = logging.getLogger("itd")
    base_logger.propagate = False

    for h in list(base_logger.handlers):
        base_logger.removeHandler(h)

    RichHandler = None
    if colorful is not False:
        try:
            from rich.logging import RichHandler
        except ImportError:
            pass

    if RichHandler is not None:
        handler = RichHandler(rich_tracebacks=True, markup=True, enable_link_path=False)
        formatter = ITDFormatter("%(display_name)s%(message)s")
    else:
        handler = logging.StreamHandler(stream=stdout)
        formatter = ITDFormatter("%(asctime)s [%(levelname)s] %(display_name)s%(message)s", False)

    handler.setFormatter(formatter)

    base_logger.setLevel(level)
    base_logger.addHandler(handler)

    return base_logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f'itd.{name}')
