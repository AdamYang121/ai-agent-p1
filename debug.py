"""
PyCharm debug entry point.
Run this file with the green ▶ / 🐛 button in PyCharm.
Breakpoints in any file (routers, services, models) will work.

NOTE: reload=False is intentional — reload forks a subprocess which
breaks PyCharm's debugger attachment. Just re-run manually after changes.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
