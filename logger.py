import os
import logging
import pathlib
from datetime import datetime, timedelta

class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[38;5;159m",    # Blue
        logging.INFO: "\033[38;5;113m",     # Green
        logging.WARNING: "\033[38;5;172m",  # Yellow
        logging.ERROR: "\033[38;5;1m",    # Red
        logging.CRITICAL: "\033[38;5;13m"  # Magenta
    }

    RESET = "\033[0m"

    def format(self, record):
        # Apply color based on log level
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

class DateRotatingFileHandler(logging.FileHandler):
    DATE_FORMAT = "%Y-%m-%d"
    def __init__(self, log_path, log_file_path, fallback_log_path=None, mode='a', encoding=None, delay=False, *args, **kwargs):
        self._in_rollover = False  # Add a flag to track rollover state
        self.fallback_log_path = fallback_log_path
        self.logger = None
        self.log_path = log_path
        self.current_date = datetime.now().strftime(self.DATE_FORMAT)

        # Call the parent class constructor
        super().__init__(log_file_path, mode, encoding, delay)

    def emit(self, record):
        try:
            today = datetime.now().strftime(self.DATE_FORMAT)
            if today != self.current_date:
                self.doRollover(today)
                self.current_date = today
            super().emit(record)
        except Exception as e:
            self.log_to_fallback_file("[ERROR] Error during emit.", e)

    def doRollover(self, today):
        if self._in_rollover:
            self.log_to_fallback_file(f"Exiting re-entrant rollover.")
            return  # Prevent re-entrant rollovers

        self._in_rollover = True
        try:
            if self.stream:
                self.log_to_fallback_file("[INFO] Closing current log stream.")
                self.stream.close()
                self.stream = None

            # Update base filename to the new date-based filename
            log_file_path = DateRotatingFileHandler.get_log_filename(self.log_path, today)
            self.baseFilename = log_file_path
            self.stream = self._open()

            # Clean up old logs
            self.delete_old_logs()
            self.current_date = today

            # Log to test and indicate successful rollover
            self.log_to_fallback_file(f"[INFO] Opening new logger stream @ {log_file_path}.")
        except Exception as e:
            self.log_to_fallback_file(f"[ERROR] Error during rollover: ", e)
        finally:
            self._in_rollover = False

    def delete_old_logs(self):
        cutoff_date = datetime.now() - timedelta(weeks=1)
        fallback_name = pathlib.Path(self.fallback_log_path).name  # "rollover_logs.txt"
        for log_file in pathlib.Path(self.log_path).glob("*.log"):
            if log_file.name == fallback_name:
                continue  # sla het fallback-bestand over
            try:
                file_date = datetime.strptime(log_file.stem, self.DATE_FORMAT)
                if file_date < cutoff_date:
                    self.log_to_fallback_file(f"[INFO] Deleting old log file: {log_file}")
                    log_file.unlink()
            except ValueError:
                self.log_to_fallback_file(f"[WARN] Not deleting non-matching file: {log_file}")
            except Exception as e:
                self.log_to_fallback_file(f"[ERROR] Error deleting file {log_file}.", e)

    def create_log_directory(self):
        try:
            # alleen loggen als de map nog niet bestaat
            if not os.path.exists(self.log_path):
                os.makedirs(self.log_path)
                self.log_to_fallback_file(f"[INFO] Created log directory: {self.log_path}")
        except Exception as e:
            # bij fouten (bijv. permissies) log je die
            self.log_to_fallback_file("[ERROR] Error creating log directory.", e)

    def log_to_fallback_file(self, message, exception=None):
        """
        Write a fallback log message directly to a file, bypassing the logging framework.
        """
        try:
            with open(self.fallback_log_path, "a") as error_log:
                error_log.write(f"{datetime.now()} - {message}\n")
                if exception:
                    error_log.write(f"Exception: {exception}\n")
        except Exception as e:
            # If even the fallback logging fails, print to console as a last resort
            print(f"Critical error: Failed to write to fallback log: {e}")

    @staticmethod
    def get_log_filename(log_path, date=None):
        try:
            date_str = date or datetime.now().strftime(DateRotatingFileHandler.DATE_FORMAT)
            filename = os.path.join(log_path, f"{date_str}.log")
            return filename
        except Exception as e:
            DateRotatingFileHandler.log_to_fallback_file(f"Error generating log filename: ", e)
            return None

def _test_logging_setup(logger, log_path):
    """
    Test the logging setup and handle potential issues with the configuration.
    """
    logger.info("Testing logging setup...")
    
    # Check if the log handlers are correctly attached
    date_handler = next((h for h in logger.handlers if isinstance(h, DateRotatingFileHandler)), None)
    if not date_handler:
        logger.error("DateRotatingFileHandler is not properly attached.")
    else:
        logger.info("DateRotatingFileHandler is properly attached.")

        # Simulate a rollover test
        test_date = (datetime.now() + timedelta(days=1)).strftime(DateRotatingFileHandler.DATE_FORMAT)
        logger.info(f"Simulating log rollover for date: {test_date}")
        date_handler.doRollover(test_date)

        # Verify that the new log file is created
        new_log_file = pathlib.Path(date_handler.baseFilename)
        if new_log_file.exists():
            logger.info(f"Log rollover successful. New log file created: {new_log_file}")
        else:
            logger.error(f"Log rollover failed. New log file not created: {new_log_file}")

    # Log final test message
    logger.info("Logging setup test completed.")

def setup_logging():
    log_level = logging.DEBUG
    log_path = pathlib.Path(__file__).parent / 'logs'
    log_file_name = DateRotatingFileHandler.get_log_filename(log_path)
    log_file_path = pathlib.Path(log_file_name)
    formatter = ColoredFormatter("%(asctime)s [%(name)s] %(levelname)s - %(message)s")
    fallback_log_path = log_path / "rollover_logs.txt"  # geef je fallback geen .log-extensie

    root_logger = logging.getLogger()
    handler = None  # initialiseer altijd

    # date-based filehandler alleen toevoegen als hij nog niet bestaat
    if not any(isinstance(h, DateRotatingFileHandler) for h in root_logger.handlers):
        handler = DateRotatingFileHandler(log_path, log_file_path, fallback_log_path)
        handler.setFormatter(formatter)
        handler.logger = root_logger
        # maak de map aan, en log alleen als het echt nieuw is
        if not log_path.exists():
            log_path.mkdir(parents=True)
            root_logger.info(f"Created log directory: {log_path}")
        root_logger.addHandler(handler)
        root_logger.setLevel(log_level)

    # console handler slechts één keer toevoegen
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # oude logs opruimen (alleen op nieuw aangemaakte handler)
    if handler is not None:
        try:
            handler.delete_old_logs()
        except Exception:
            root_logger.exception("Error during initial log cleanup")

    # Test logging setup
    #_test_logging_setup(logger, log_path)
