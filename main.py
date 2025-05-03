import logging

from fastapi import FastAPI, Response

logger = logging.getLogger("uvstarter.error")
logger.info("API is starting up")

app = FastAPI()


@app.get("/")
def main():
    logger.debug("this is a debug message")
    return Response(content="Hello from UV!", media_type="text/plain")


if __name__ == "__main__":
    main()
