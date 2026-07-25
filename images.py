from pathlib import Path
import requests


BASE_DIR = Path(__file__).resolve().parent

IMAGE_DIR = BASE_DIR / "images"

IMAGE_DIR.mkdir(
    exist_ok=True
)


HEADERS = {

    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

}


# Steam serves these directly from its CDN, keyed by appid — no
# lookup request needed, just a plain image download. Try the
# small capsule first, fall back to the header image if missing.

IMAGE_URL_TEMPLATES = [

    "https://cdn.cloudflare.steamstatic.com/steam/apps/{}/capsule_184x69.jpg",

    "https://cdn.cloudflare.steamstatic.com/steam/apps/{}/header.jpg",

]



def _image_path(appid):

    if not appid:
        return None


    return IMAGE_DIR / f"{appid}.jpg"



def get_local_image_path(appid):

    """
    Read-only lookup — never makes a network request.
    Safe to call from the GUI thread.
    """

    path = _image_path(
        appid
    )


    if path and path.exists():
        return path


    return None



def ensure_image_cached(appid):

    """
    Download the image once and cache it to disk. If it's
    already cached, this makes no network request at all.
    """

    path = _image_path(
        appid
    )


    if path is None:
        return None


    if path.exists():
        return path


    for template in IMAGE_URL_TEMPLATES:

        url = template.format(
            appid
        )


        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )


            if (
                response.status_code == 200
                and response.content
            ):

                path.write_bytes(
                    response.content
                )


                return path


        except requests.RequestException:

            continue



    return None
