from pathlib import Path
from io import BytesIO
import hashlib
import requests

from PIL import Image


BASE_DIR = Path(__file__).resolve().parent

IMAGE_DIR = BASE_DIR / "images"

IMAGE_DIR.mkdir(
    exist_ok=True
)


# Patch-note screenshots are only ever shown small and inline, so
# unlike game thumbnails they're worth shrinking on disk. Each one
# is downscaled to fit within this many pixels per side (aspect
# ratio kept, never upscaled) and re-saved as a JPEG at this
# quality to keep the cache small.

NOTE_IMAGE_MAX_SIZE = 200

NOTE_IMAGE_QUALITY = 95


HEADERS = {

    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

}


# Fallback only. This unhashed CDN path only works for older,
# long-established games — newer or recently-repackaged store
# assets live under a content-hash segment we can't guess
# ("store_item_assets/steam/apps/{appid}/{hash}/header.jpg"), so
# for those this template 404s. ensure_image_cached() tries the
# Steam appdetails API first, which always returns the correct,
# current URL, and only falls back to guessing these if that
# lookup itself fails (e.g. Steam API hiccup).

IMAGE_URL_TEMPLATES = [

    "https://cdn.cloudflare.steamstatic.com/steam/apps/{}/header.jpg",

    "https://cdn.cloudflare.steamstatic.com/steam/apps/{}/capsule_184x69.jpg",

]


# Storefront API - given an appid, tells us the *current*,
# correctly-hashed capsule/header image URLs. Doesn't require a
# key. See https://wiki.teamfortress.com/wiki/User:RJackson/StorefrontAPI

STEAM_APPDETAILS_API = (
    "https://store.steampowered.com/api/appdetails"
    "?appids={}&filters=basic"
)



def _lookup_current_image_url(appid):

    """
    Ask Steam directly for this app's current image URLs instead
    of guessing a CDN path. Covers games whose store assets live
    under a hashed path (new releases, upcoming/unreleased games,
    or anything re-processed since launch) that the static
    IMAGE_URL_TEMPLATES can't predict.
    """

    try:

        response = requests.get(
            STEAM_APPDETAILS_API.format(appid),
            headers=HEADERS,
            timeout=10
        )


        if response.status_code != 200:
            return None


        payload = response.json()

    except (requests.RequestException, ValueError):

        return None



    entry = payload.get(
        str(appid)
    )


    if not entry or not entry.get("success"):
        return None


    data = entry.get(
        "data",
        {}
    )


    # Prefer the biggest source image available. thumbnail() can
    # only shrink an image, never enlarge it - if we cache a small
    # capsule (184x69 or 231x87), that's the ceiling on how big it
    # can ever be shown, no matter the thumbnail box size later.
    # header_image (~460x215) gives real resolution to work with.

    return (
        data.get("header_image")
        or data.get("capsule_image")
        or data.get("capsule_imagev5")
    )



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


    urls_to_try = []


    dynamic_url = _lookup_current_image_url(
        appid
    )


    if dynamic_url:

        urls_to_try.append(
            dynamic_url
        )


    urls_to_try.extend(

        template.format(appid)

        for template in IMAGE_URL_TEMPLATES

    )



    for url in urls_to_try:


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



# ----------------------------------------------------------------
# Inline patch-note images (e.g. screenshots embedded via
# [img src="{STEAM_CLAN_IMAGE}/..."]). These aren't tied to a
# Steam appid, so they're cached by a hash of their resolved URL
# instead.
# ----------------------------------------------------------------


def _note_image_path(url):

    if not url:
        return None


    digest = hashlib.sha1(
        url.encode("utf-8")
    ).hexdigest()


    # Always cached as .jpg - regardless of the source format,
    # ensure_note_image_cached re-encodes every note image as a
    # compressed JPEG, so the extension should reflect that rather
    # than the original URL's suffix.

    return IMAGE_DIR / f"note_{digest}.jpg"



def get_local_note_image_path(url):

    """
    Read-only lookup — never makes a network request.
    Safe to call from the GUI thread.
    """

    path = _note_image_path(
        url
    )


    if path and path.exists():
        return path


    return None



def _save_compressed_note_image(content, path):

    """
    Resize the downloaded image so neither side exceeds
    NOTE_IMAGE_MAX_SIZE (aspect ratio preserved, never upscaled)
    and re-save it as a JPEG at NOTE_IMAGE_QUALITY. This is only
    used for inline patch-note images - game thumbnails are left
    untouched by ensure_image_cached().
    """

    with Image.open(BytesIO(content)) as image:

        image.thumbnail(
            (NOTE_IMAGE_MAX_SIZE, NOTE_IMAGE_MAX_SIZE),
            Image.LANCZOS
        )


        # JPEG has no alpha channel - flatten anything with
        # transparency (PNG/GIF/WEBP) onto a white background
        # first instead of letting save() error out or discard it
        # oddly.

        if image.mode in ("RGBA", "LA", "P"):

            background = Image.new(
                "RGB",
                image.size,
                (255, 255, 255)
            )

            rgba_image = image.convert("RGBA")

            background.paste(
                rgba_image,
                mask=rgba_image.split()[-1]
            )

            image = background

        else:

            image = image.convert("RGB")


        image.save(
            path,
            "JPEG",
            quality=NOTE_IMAGE_QUALITY,
            optimize=True
        )



def ensure_note_image_cached(url):

    """
    Download an inline patch-note image once, compress/resize it,
    and cache it to disk. If it's already cached, this makes no
    network request.
    """

    path = _note_image_path(
        url
    )


    if path is None:
        return None


    if path.exists():
        return path


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

            try:

                _save_compressed_note_image(
                    response.content,
                    path
                )

            except Exception:

                # Not a format Pillow can decode, or otherwise
                # corrupt - fall back to caching the raw bytes
                # rather than losing the image entirely.

                path.write_bytes(
                    response.content
                )


            return path


    except requests.RequestException:

        pass



    return None
