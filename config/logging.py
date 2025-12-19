import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO"):
    """Configure structured JSON logging"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # JSON formatter
    json_formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)
    
    # File handler for application logs
    file_handler = logging.FileHandler(log_dir / "application.log")
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    # Separate audit log handler
    audit_logger = logging.getLogger("audit")
    audit_handler = logging.FileHandler(log_dir / "audit.log")
    audit_handler.setFormatter(json_formatter)
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    
    # Security event logger
    security_logger = logging.getLogger("security")
    security_handler = logging.FileHandler(log_dir / "security.log")
    security_handler.setFormatter(json_formatter)
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)