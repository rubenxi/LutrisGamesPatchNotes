import requests
import time
import random
import re
import html
import difflib
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from gui import UpdateGUI



HEADERS = {

    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

}



STEAM_SEARCH = (
    "https://store.steampowered.com/search/?term={}&category1=998"
)


STEAMDB_RSS = (
    "https://steamdb.info/api/PatchnotesRSS/?appid={}"
)


STEAM_NEWS_API = (
    "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
    "?appid={}&count=30&maxlength=0&format=json"
)




def normalize(text):

    text = text.lower()

    return re.sub(
        r"[^a-z0-9]",
        "",
        text
    )



def similar(
        original,
        found,
        threshold=0.60
):

    original_clean = normalize(
        original
    )

    found_clean = normalize(
        found
    )


    if not original_clean or not found_clean:

        return False



    # Exact match
    if original_clean == found_clean:

        return True



    # Steam result contains the Lutris name
    # Example:
    # slimerancher
    # slimerancher223sep2025...
    if original_clean in found_clean:

        return True



    # Try comparing only the beginning of the Steam result.
    # Steam usually puts the title first.
    max_length = len(original_clean)


    if len(found_clean) > max_length:

        found_prefix = found_clean[:max_length + 5]

    else:

        found_prefix = found_clean



    ratio = difflib.SequenceMatcher(
        None,
        original_clean,
        found_prefix
    ).ratio()



    return ratio >= threshold





# Steam's news content sometimes references clan-hosted images
# using a {STEAM_CLAN_IMAGE} placeholder instead of a real URL.
# This is the actual CDN base it stands in for.

STEAM_CLAN_IMAGE_BASE = (
    "https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/clans"
)


# Marker left in cleaned notes text wherever an inline image was
# found, so the GUI can render an actual picture there instead of
# showing (or losing) the raw bbcode.

NOTE_IMAGE_PATTERN = re.compile(
    r"\[\[STEAM_NOTE_IMAGE:(.+?)\]\]"
)



def resolve_image_url(url):

    url = url.strip().strip(
        "\"'"
    )


    if url.startswith(
        "{STEAM_CLAN_IMAGE}"
    ):

        url = (
            STEAM_CLAN_IMAGE_BASE
            +
            url[len("{STEAM_CLAN_IMAGE}"):]
        )


    return url



def _replace_image_tag(match):

    src_attr = match.group(1)
    inner = match.group(2)

    raw_url = (
        src_attr
        or
        inner
        or
        ""
    ).strip()


    if not raw_url:
        return ""


    url = resolve_image_url(
        raw_url
    )


    return f"\n[[STEAM_NOTE_IMAGE:{url}]]\n"



def extract_note_image_urls(notes):

    """
    Pull out every resolved image URL a cleaned notes string
    references, so callers can pre-download/cache them.
    """

    if not notes:
        return []


    return NOTE_IMAGE_PATTERN.findall(
        notes
    )



def clean_bbcode(text):

    if not text:
        return text


    # Real <br> tags occasionally show up inside the raw content -
    # turn those into actual line breaks before anything else.

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )


    # Images (e.g. [img src="{STEAM_CLAN_IMAGE}/123/abc.jpg"] or
    # [img]https://.../abc.jpg[/img]) get swapped for a resolved-URL
    # marker instead of being deleted, so the GUI can render the
    # actual picture in place.

    text = re.sub(
        r"\[img(?:\s+src=[\"']([^\"']+)[\"'])?\](?:(.*?)\[/img\])?",
        _replace_image_tag,
        text,
        flags=re.IGNORECASE | re.DOTALL
    )


    # Embedded videos aren't renderable here either.

    text = re.sub(
        r"\[previewyoutube[^\]]*\].*?\[/previewyoutube\]",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )


    # Keep link text readable, but fold the URL in next to it
    # instead of just discarding it.

    text = re.sub(
        r"\[url=([^\]]+)\](.*?)\[/url\]",
        lambda match: f"{match.group(2)} ({match.group(1)})",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )


    # Turn list items into their own bulleted line. Steam closes
    # each item with [/*] (not [/list]) and often doesn't put a
    # real line break between items, so without this every bullet
    # ran together in one block and the [/*] markers leaked through
    # as visible text.

    text = re.sub(
        r"\[\*\]",
        "\n\u2022 ",
        text
    )

    text = re.sub(
        r"\[/\*\]",
        "",
        text
    )


    # Strip whatever bbcode tags are left over - bold, italic,
    # headers, lists, quotes, etc. - attributes and all. The old
    # version only matched a narrow set of characters inside the
    # brackets, which is why tags with slashes/dots/braces (like
    # image paths) were slipping through as visible text.

    text = re.sub(
        r"\[/?[a-zA-Z0-9_]+(?:=[^\]]*)?\]",
        "",
        text
    )

    text = html.unescape(
        text
    )


    # Keep single blank lines as paragraph breaks, but collapse
    # runs of several blank lines down to one.

    lines = []

    previous_blank = False


    for raw_line in text.splitlines():

        line = raw_line.strip()


        if line:

            lines.append(
                line
            )

            previous_blank = False


        elif not previous_blank:

            lines.append(
                ""
            )

            previous_blank = True



    return "\n".join(
        lines
    ).strip()



def find_matching_news(
        update_date,
        news_items,
        max_diff_seconds=3 * 24 * 3600
):

    # Titles share most of their text (the game name), so fuzzy
    # title matching can't tell one post from another. Publish
    # date does: SteamDB's pubDate for a real announcement lines
    # up with the timestamp Steam's own News API reports for it.

    try:

        target_ts = parsedate_to_datetime(
            update_date
        ).timestamp()

    except Exception:

        return None



    best_item = None

    best_diff = None


    for item in news_items:

        item_date = item.get(
            "date"
        )


        if item_date is None:
            continue


        diff = abs(
            item_date - target_ts
        )


        if best_diff is None or diff < best_diff:

            best_diff = diff

            best_item = item



    if (
        best_item is not None
        and best_diff is not None
        and best_diff <= max_diff_seconds
    ):

        return best_item



    return None



def extract_rating(result):

    """
    Steam's search page embeds each game's review summary right on
    the result row (a tooltip like "Very Positive<br>92% of the
    ... reviews are positive"). No extra request needed - just
    read it out of the page we already fetched.
    """

    review_el = result.find(
        "span",
        class_="search_review_summary"
    )


    if not review_el:
        return None, None


    tooltip = review_el.get(
        "data-tooltip-html",
        ""
    )


    if not tooltip:
        return None, None


    text = tooltip.split(
        "<br>"
    )[0].strip()


    match = re.search(
        r"(\d+)%",
        tooltip
    )


    percent = int(
        match.group(1)
    ) if match else None


    return text or None, percent



class SteamClient:



    def __init__(self):

        self.search_requests = 0

        self.rss_requests = 0

        self.news_requests = 0




    # ---------------------------------
    # HTTP REQUEST HANDLER
    # ---------------------------------

    def request(
            self,
            url,
            retries=3
    ):


        for attempt in range(
            retries
        ):


            print(
                f"[HTTP] Requesting: {url}"
            )


            try:


                response = requests.get(

                    url,

                    headers=HEADERS,

                    timeout=15

                )



                print(

                    f"[HTTP] Status: {response.status_code}"

                )



                if response.status_code == 429:


                    delay = random.randint(
                        20,
                        40
                    )


                    print(

                        f"[HTTP] Rate limited. Waiting {delay}s"

                    )


                    time.sleep(
                        delay
                    )


                    continue



                response.raise_for_status()



                print(
                    "[HTTP] Success"
                )



                return response




            except requests.Timeout:


                print(

                    f"[HTTP] Timeout ({attempt+1}/{retries})"

                )



            except requests.RequestException as e:


                print(

                    f"[HTTP] Error ({attempt+1}/{retries}): {e}"

                )



            time.sleep(
                5
            )




        print(

            f"[HTTP] FAILED after {retries} attempts"

        )


        return None





    # ---------------------------------
    # STEAM SEARCH
    # ---------------------------------

    def search_game(
            self,
            name
    ):


        self.search_requests += 1



        print(

            f"[Steam] Searching: {name}"

        )



        url = STEAM_SEARCH.format(

            requests.utils.quote(
                name
            )

        )



        response = self.request(
            url
        )



        if response is None:


            print(

                f"[Steam] Search failed: {name}"

            )


            return None




        soup = BeautifulSoup(

            response.text,

            "html.parser"

        )



        result = soup.find(

            "a",

            class_="search_result_row"

        )



        if not result:


            print(

                f"[Steam] No result: {name}"

            )


            return None




        title = result.get_text(
            strip=True
        )



        print(

            f"[Steam] Found candidate: {title}"

        )



        if not similar(

            name,

            title

        ):


            print(

                f"[Steam] Name mismatch: {name} != {title}"

            )


            return None




        href = result.get(
            "href"
        )



        if not href:

            return None




        match = re.search(

            r"/app/(\d+)",

            href

        )



        if not match:

            return None




        appid = match.group(1)



        print(

            f"[Steam] AppID found: {appid}"

        )



        rating_text, rating_percent = extract_rating(
            result
        )



        return {


            "appid":

            appid,



            "url":

            f"https://store.steampowered.com/app/{appid}",


            "rating_text":

            rating_text,


            "rating_percent":

            rating_percent


        }





    # ---------------------------------
    # OFFICIAL NEWS (full patch notes text, one request per game)
    # ---------------------------------

    def get_news_for_app(
            self,
            appid
    ):

        self.news_requests += 1


        url = STEAM_NEWS_API.format(
            appid
        )


        print(

            f"[Steam] Fetching official news for app {appid}"

        )


        response = self.request(
            url
        )


        if response is None:


            print(

                "[Steam] Failed to fetch news"

            )


            return []



        try:

            data = response.json()

        except Exception as e:


            print(

                f"[Steam] News JSON error: {e}"

            )


            return []



        items = (

            data
            .get("appnews", {})
            .get("newsitems", [])

        )


        print(

            f"[Steam] {len(items)} news items fetched for {appid}"

        )


        return items



    # ---------------------------------
    # STEAMDB UPDATES
    # ---------------------------------

    def get_updates(
            self,
            appid
    ):


        self.rss_requests += 1



        url = STEAMDB_RSS.format(

            appid

        )



        print(

            f"[SteamDB] Checking app {appid}"

        )



        response = self.request(
            url
        )



        if response is None:


            print(

                f"[SteamDB] No response for {appid}"

            )


            return []



        print(

            f"[SteamDB] Parsing RSS {appid}"

        )



        updates = []



        try:


            root = ET.fromstring(

                response.text

            )



            channel = root.find(
                "channel"
            )



            if channel is None:


                print(

                    f"[SteamDB] Empty RSS for {appid}"

                )


                return []




            for item in channel.findall(
                    "item"
            ):


                link = item.findtext(
                    "link",
                    ""
                )



                if link:

                    link = link.split(
                        "?",
                        1
                    )[0]



                updates.append({


                    "title":

                    item.findtext(
                        "title",
                        ""
                    ),



                    "description":

                    item.findtext(
                        "description",
                        ""
                    ),



                    "date":

                    item.findtext(
                        "pubDate",
                        ""
                    ),



                    "link":

                    link


                })




            print(

                f"[SteamDB] {len(updates)} updates found for {appid}"

            )



        except Exception as e:


            print(

                f"[SteamDB] XML error {appid}: {e}"

            )



        return updates
