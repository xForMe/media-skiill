import json
import os
import subprocess
import logging
from typing import Dict, Any

# Configure logging
def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "auto_run.log"), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"

def load_config(config_path: str = CONFIG_FILE) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        return {}

def run_command(command: list, description: str):
    """Run a subprocess command and log output."""
    logger.info(f"Starting: {description}")
    logger.info(f"Command: {' '.join(command)}")
    
    try:
        # Use subprocess.run to execute the command
        # Capture output to log it if needed, or let it stream to stdout/stderr
        result = subprocess.run(command, check=False)
        
        if result.returncode == 0:
            logger.info(f"Successfully completed: {description}")
        else:
            logger.error(f"Failed: {description} (Exit Code: {result.returncode})")
            
    except Exception as e:
        logger.error(f"Error executing {description}: {e}")

def main():
    logger.info("Starting Auto-Runner...")
    config = load_config()
    
    if not config:
        logger.error("Configuration is empty or invalid. Exiting.")
        return

    # 1. Run Channels
    channels_config = config.get("channels", {})
    
    # Xiaohongshu Channel
    xhs_config = channels_config.get("xiaohongshu", {})
    if xhs_config.get("enabled", False):
        cmd = ["python", "xiaohongshu_skill/main.py"]
        
        input_path = xhs_config.get("input_path", "output/articles")
        cmd.extend(["--input", input_path])
        
        mode = xhs_config.get("mode", "dry-run")
        if mode == "publish":
            if xhs_config.get("show_ui", False):
                cmd.append("--non-headless")
        else:
            cmd.append("--dry-run")
            
        run_command(cmd, "Xiaohongshu Channel Automation")

    logger.info("Auto-Runner completed all tasks.")

if __name__ == "__main__":
    main()
