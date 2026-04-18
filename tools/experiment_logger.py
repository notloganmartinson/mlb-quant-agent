import sqlite3
import json
import os
from datetime import datetime
import shutil

class QuantLogger:
    def __init__(self, db_path="reports/registry.db"):
        self.db_path = db_path
        os.makedirs("reports/runs", exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiment_runs (
                run_id TEXT PRIMARY KEY,
                timestamp DATETIME,
                label TEXT,
                model_type TEXT,
                features TEXT,
                parameters TEXT,
                metrics TEXT,
                artifact_path TEXT
            )
        """)
        conn.close()

    def log_run(self, label, model_type, features, parameters, metrics, artifacts=None):
        """
        Logs a single experiment run.
        artifacts: list of file paths (e.g. PNGs, joblib models) to archive.
        """
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_dir = f"reports/runs/{run_id}"
        os.makedirs(run_dir, exist_ok=True)

        # Archive artifacts
        archived_paths = []
        if artifacts:
            for art_path in artifacts:
                if os.path.exists(art_path):
                    filename = os.path.basename(art_path)
                    dest = f"{run_dir}/{filename}"
                    shutil.copy(art_path, dest)
                    archived_paths.append(dest)

        # Log to DB
        conn = sqlite3.connect(self.db_path)
        sql = """
            INSERT INTO experiment_runs 
            (run_id, timestamp, label, model_type, features, parameters, metrics, artifact_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        conn.execute(sql, (
            run_id,
            datetime.now().isoformat(),
            label,
            model_type,
            json.dumps(features),
            json.dumps(parameters),
            json.dumps(metrics),
            run_dir
        ))
        conn.commit()
        conn.close()
        
        print(f"\n[Experiment Registry] Run logged successfully: {run_id}")
        print(f"  -> Label: {label}")
        print(f"  -> Artifacts: {run_dir}/")
        return run_id

# Global instance for easy import
logger = QuantLogger()
