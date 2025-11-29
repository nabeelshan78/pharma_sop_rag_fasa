import logging
import sys

def setup_logger(name: str = "FASA_APP"):
    """
    Configures a standard logger with a specific format.
    Prevents duplicate logs in Streamlit.
    """
    logger = logging.getLogger(name)
    
    # Only add handlers if they don't exist (Streamlit auto-reload fix)

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Format: [Time] [Level] [Module] - Message
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] - %(message)s",
            datefmt="%H:%M:%S"
        )
        
        # Output to Console
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger
