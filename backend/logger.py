import os
import json
import time

class ExperimentLogger:
    def __init__(self, log_dir="logs", filename="experiment_log.jsonl"):
        # Construct the absolute path based on this file's location
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(base_dir, log_dir)
        
        # Ensure the logs directory exists
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.log_path = os.path.join(self.log_dir, filename)

    def log_event(self, step_id, status, confidence=0.85, message=""):
        """
        Appends a structured JSON Line to the log file.
        """
        entry = {
            "timestamp": time.time(),
            "step_id": step_id,
            "status": status,
            "confidence": confidence,
            "message": message
        }
        
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def get_logs(self):
        """
        Reads and returns all parsed JSON logs from the file.
        """
        logs = []
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        logs.append(json.loads(line))
        return logs

# Singleton logger instance
experiment_logger = ExperimentLogger()
