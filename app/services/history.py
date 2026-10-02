import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from app.utils.paths import data_dir


class History:
    def __init__(self, path=None):
        self.db = sqlite3.connect(path or data_dir() / "history.sqlite3")
        self.db.execute("CREATE TABLE IF NOT EXISTS downloads (id TEXT PRIMARY KEY, date TEXT, data TEXT)")

    def record(self, job):
        data = {"id": job.id, "url": job.url, "title": job.title, "thumbnail": job.info.get("thumbnail", ""),
                "options": asdict(job.options), "output": job.output, "state": str(job.state), "error": job.error,
                "info": job.info}
        self.db.execute("INSERT OR REPLACE INTO downloads VALUES (?, ?, ?)",
                        (job.id, datetime.now(timezone.utc).isoformat(), json.dumps(data)))
        self.db.commit()

    def rows(self):
        return [dict(json.loads(data), date=date) for date, data in self.db.execute("SELECT date,data FROM downloads ORDER BY date DESC LIMIT 1000")]

    def remove(self, job_id):
        self.db.execute("DELETE FROM downloads WHERE id=?", (job_id,))
        self.db.commit()
