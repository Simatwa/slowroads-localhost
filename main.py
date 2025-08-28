#!/usr/bin/python

# TODO:

"""
-  Create route for static contents
-  Add route for handling any other requests. Since by reaching that endpoint will mean the
resource is not locally available, so we have to fetch it from remote server and cache
it in the required path to be served in the next requests.

"""

import os
from urllib.parse import urljoin
from typing import Annotated, Any, Coroutine
from pathlib import Path as P

import httpx
import aiofiles

from fastapi import FastAPI, Path, HTTPException, status
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse, FileResponse, Response


from starlette.types import Scope

app = FastAPI(
    title="Slowroads.localhost",
    description="Host slowroads.io from your machine.",
    version="0.1.0",
)

SCRIPT_DIR = P(__name__).parent

FRONTEND_DIR = SCRIPT_DIR / "slowroads.io"

HOST_URL = "https://slowroads.io"


REQUEST_HEADERS = {
    "Accept-Language": "en-US,en;q=0.5",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0",
}
client = httpx.AsyncClient(headers=REQUEST_HEADERS)


class CustomStaticFiles(StaticFiles):
    async def get_response(
        self, path: str, scope: Scope
    ) -> Coroutine[Any, Any, Response]:
        check_path = scope["path"].replace("/static/", "")

        if not FRONTEND_DIR.joinpath(check_path).exists():
            print("Fetching missing file")
            return await download_file(path, redirect=False)

        return await super().get_response(path, scope)


static_files = CustomStaticFiles(directory=FRONTEND_DIR, html=True)

app.mount("/static", static_files)


@app.get("/", name="Index", include_in_schema=False)
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


async def download_file(path: str, redirect: bool = True):
    url = urljoin(HOST_URL, path.replace("\\", "/"))
    print("URL : ", url)

    saved_to: P = FRONTEND_DIR / path

    def send_response():
        redirect_to = "/static/" + path
        if redirect:
            return RedirectResponse(
                redirect_to,
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                # status.HTTP_308_PERMANENT_REDIRECT
            )
        else:
            return FileResponse(saved_to)

    if saved_to.exists():
        return send_response()

    try:
        if not saved_to.parent.exists():
            os.makedirs(saved_to.parent)

        async with client.stream("GET", url) as stream:
            if stream.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            stream.raise_for_status()

            async with aiofiles.open(saved_to, "wb") as fh:
                async for chunk in stream.aiter_bytes(2400):
                    await fh.write(chunk)

        return send_response()

    except Exception as e:
        if not isinstance(e, HTTPException):
            print("Error while fetching remote content : ", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        raise e


@app.get("/{path:path}", name="Serve non-cached file")
async def fetch_from_remote_and_catch(
    path: Annotated[str, Path(description="Path to remote file")],
):
    return await download_file(path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
    )  # reload=True, workers=1)
