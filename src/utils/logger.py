import sys
from loguru import logger
from src.config.settings import LoggingSettings, load_settings

def setup_logger():
    # Load logging settings from the global AppSettings
    # This assumes config.json is in the root directory when load_settings() is called
    # For utilities, it might be better to pass settings or have a global settings instance
    try:
        # Try to load settings from a default config.json path
        # This path might need to be relative to the project root, not necessarily CWD
        # For now, assume config.json is discoverable by load_settings default.
        app_settings = load_settings() # Uses default "config.json"
        log_settings = app_settings.logging
    except FileNotFoundError:
        # Fallback if config.json is not found during initial logger setup
        # This might happen if logger is imported before main app fully initializes settings
        print("Warning: config.json not found for logger setup. Using default logging settings.")
        log_settings = LoggingSettings() # Use Pydantic default values
    except Exception as e:
        print(f"Warning: Error loading logging settings: {e}. Using default logging settings.")
        log_settings = LoggingSettings()

    logger.remove() # Remove default handler to avoid duplicate logs if reconfigured
    logger.add(
        sys.stderr, 
        level=log_settings.level.upper(), 
        format=log_settings.format
    )
    # You can add more handlers here, e.g., for file logging:
    # logger.add("logs/app.log", rotation="10 MB", level=log_settings.level.upper(), format=log_settings.format)
    return logger

# Initialize and export the logger instance for other modules to use
# This will run when the module is first imported.
app_logger = setup_logger()

if __name__ == "__main__":
    # Example usage
    app_logger.debug("This is a debug message.")
    app_logger.info("This is an info message.")
    app_logger.warning("This is a warning message.")
    app_logger.error("This is an error message.")
    app_logger.critical("This is a critical message.")

    print(f"\nTo test custom config, ensure 'config.json' is in the root directory with a 'logging' section.")
    print("Example 'config.json' logging section:")
    print("""
    "logging": {
        "level": "DEBUG",
        "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    }
    """ ) 