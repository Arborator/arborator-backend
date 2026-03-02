import subprocess
import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

def run_update():
    try:
        script_path = os.path.join(os.path.dirname(__file__), "../..", "fetch_validator_data.sh")
        logger.info("Exécution: fetch_validator_data.sh")
        subprocess.run(["bash", script_path], check=True)
        logger.info("fetch_validator_data.sh exécuté avec succès")
    except Exception as e:
        logger.error(f"✗ Erreur: {e}")

def validator_exists():
    validator_path = os.path.join(os.path.dirname(__file__), "ud_validator", "data")
    return os.path.exists(validator_path)

def start_update_daemon():
    if not validator_exists():
        logger.info("UD Validator non trouvé. execution de fetch_validator_data.sh")
        run_update()
    
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(run_update, "interval", minutes=2, id="validator_update")
    scheduler.start()