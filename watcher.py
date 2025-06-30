import sys
import subprocess
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class RestartHandler(PatternMatchingEventHandler):
    def __init__(self, cmd):
        super().__init__(patterns=["*.py"])
        self.cmd = cmd
        self.process = subprocess.Popen(self.cmd)

    def on_modified(self, event):
        print(f"{event.src_path} geändert → Neustart")
        self.process.kill()
        self.process = subprocess.Popen(self.cmd)


if __name__ == "__main__":
    cmd = [sys.executable, "main.py"]
    event_handler = RestartHandler(cmd)
    obs = Observer()
    obs.schedule(event_handler, path=".", recursive=True)
    obs.start()
    obs.join()
