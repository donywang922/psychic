"""Headless startup benchmark: python benchmark_startup.py [fallback-site-packages]."""
import os
from pathlib import Path
import subprocess
import sys
import time

child = r'''
import sys, time, json
if len(sys.argv) > 1:
    sys.path.append(sys.argv[1])
start = time.perf_counter()
import psychic
loaded = time.perf_counter()
app = psychic.QApplication([])
app.setStyleSheet(psychic.STYLESHEET)
gui = psychic.AgentGUI(["."])
gui.show()
app.processEvents()
print(json.dumps({"import_ms": round((loaded-start)*1000), "ready_ms": round((time.perf_counter()-start)*1000), "openai_loaded": "openai" in sys.modules, "pydantic_loaded": "pydantic" in sys.modules}))
gui.close()
'''
if __name__ == '__main__':
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    for _ in range(3):
        started = time.perf_counter()
        result = subprocess.run(
            [sys.executable, '-c', child, *sys.argv[1:]], env=env,
            cwd=Path(__file__).resolve().parent, capture_output=True,
            text=True, check=True, timeout=30,
        )
        print(result.stdout.strip(), 'process_ms=', round((time.perf_counter()-started)*1000))
