import requests
import time
import random
import re
import difflib
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from gui import UpdateGUI



HEADERS = {

    "User-Agent":
    "Mozilla/5.0 SteamUpdateChecker"

}



STEAM_SEARCH = (
    "https://store.steampowered.com/search/?term={}&category1=998"
)


STEAMDB_RSS = (
    "https://steamdb.info/api/PatchnotesRSS/?appid={}"
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





class SteamClient:



    def __init__(self):

        self.search_requests = 0

        self.rss_requests = 0




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



        return {


            "appid":

            appid,



            "url":

            f"https://store.steampowered.com/app/{appid}"


        }





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
