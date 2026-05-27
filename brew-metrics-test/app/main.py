from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="brew-metrics")


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
      <body style="font-family: sans-serif; padding: 2rem;">
        <h1>brew-metrics</h1>
        <p>App is running.</p>
      </body>
    </html>
    """


@app.get("/health")
def health():
    return {"status": "ok"}
