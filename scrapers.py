import io

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import time
from urllib.parse import quote_plus
from datetime import datetime, timezone


class ScraperLogger:
    def __init__(self):
        self.log_file = "scrape_log.txt"

    def log(self, message):
        with open(self.log_file, "a") as f:
            f.write(f"{message}\n")


class BDSMLR_Scraper:
    def __init__(self, url, user, password):
        self.url = url.strip()
        self.blog_name = self.url.split(".")[0]
        self.user = user
        self.password = password
        self.image_urls = set()
        self.image_results = []
        self.session = None
        self.csrf_token = None
        self.logger = ScraperLogger()

    def fetch(self):
        def block_resources(route):
            blocked = ["image", "stylesheet", "font", "media", "other"]
            if route.request.resource_type in blocked:
                route.abort()
            else:
                route.continue_()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                + "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="en-US",
                timezone_id="UTC",
            )
            page = context.new_page()
            page.route("**/*", block_resources)
            page.set_default_navigation_timeout(0)
            print("loading login page...")
            page.goto("https://bdsmlr.com/login", wait_until="domcontentloaded")
            print("logging in...")
            page.get_by_placeholder("E-Mail").fill(self.user)
            page.get_by_placeholder("Password").fill(self.password)
            page.get_by_role("button", name="Login").click()

            self.csrf_token = page.locator('meta[name="csrf-token"]').get_attribute("content", timeout=0)
            self.session = requests.Session()
            for cookie in context.cookies():
                self.session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

            browser.close()

        base_url = f"https://{self.blog_name}.bdsmlr.com"
        state_file = f"{self.blog_name}_scraper_state.json"

        scroll = 0
        self.recursions = 0
        last_id = None
        resuming = False

        # Hydrate state if it exists
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)
                    scroll = state.get("scroll", 0)
                    last_id = state.get("last_id", None)
                    self.image_urls = set(state.get("image_urls", []))
                    resuming = True
                print(
                    f"Resuming scrape from state file: scroll={scroll}, last_id={last_id}, previous_images={len(self.image_urls)}"
                )
            except Exception as e:
                print(f"Failed to load state file: {e}")

        print("scraping...")

        # We could increase this some if we could increase the size of the Connection Pool for requests
        # which I'm sure is possible but I need to research how to do it.
        executor = ThreadPoolExecutor(max_workers=10)
        futures = []

        def retry_download(href):
            try:
                response = self.session.get(href, headers={"x-csrf-token": self.csrf_token, "Referer": self.url})
                if response.status_code == 404:
                    self.image_urls.remove(href)
                    self.logger.log(f"image {href} returned 404, discarding...")
                    return None
                if response.status_code == 502:
                    return 502
                else:
                    response.raise_for_status()
                    return (io.BytesIO(response.content), href)
            except Exception:
                return 502

        def download_image(href):
            try:
                response = self.session.get(href, headers={"x-csrf-token": self.csrf_token, "Referer": self.url})
                if response.status_code == 404:
                    self.image_urls.remove(href)
                    self.logger.log(f"image {href} returned 404, discarding...")
                    return None
                    # TODO: We should save these somehow so attempts to re-run/update the URL_File
                    #       ignore them, as once they go 404 on bdsmlr, they will always 404
                if response.status_code == 502:
                    for attempt in (1, 2, 3):
                        print(f"image {href} returned 502, retry attempt {attempt}...")
                        time.sleep(0.6)
                        if (res := retry_download(href)) != 502 and res is not None:
                            return res
                    print(f"Failed to download {href} after 3 attempts")
                else:
                    response.raise_for_status()
                    return (io.BytesIO(response.content), href)
            except Exception as e:
                if "RemoteDisconnected" in str(e):
                    for attempt in (1, 2, 3):
                        print(f"Retrying failed download after remote disconnect: attempt {attempt}...")
                        time.sleep(0.6)
                        if (res := retry_download(href)) != 502 and res is not None:
                            return res
                    print(f"Failed to download {href} after 3 attempts")
                print(f"Failed to download {href}: {e}")
            return None

        exit_reason = "unknown"
        try:
            while True:
                if scroll == 0:
                    api_url = f"{base_url}/loadfirst"
                    scroll = 20
                else:
                    api_url = f"{base_url}/infinitepb2/{self.blog_name}"

                data = {
                    "scroll": str(scroll),
                    "timenow": quote_plus(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
                }
                if last_id is not None:
                    data["last"] = str(last_id)

                success = False

                if resuming:
                    for img in self.image_urls:
                        print("dispatching href to executor...")
                        self.resolve_url_to_bytes(executor, futures, download_image, img)
                    resuming = False
                for attempt in range(3):
                    try:
                        r = self.session.post(
                            api_url,
                            data=data,
                            headers={
                                "x-csrf-token": self.csrf_token,
                                "Referer": self.url,
                                "Content-Type": "application/x-www-form-urlencoded",
                            },
                            timeout=60,
                        )
                        if r.status_code == 502:
                            print(f"[Attempt {attempt + 1}/3] 502 Bad Gateway. Retrying in 2 seconds...")
                            time.sleep(2)
                            continue
                        r.raise_for_status()
                        soup = BeautifulSoup(r.text, "html.parser")
                        success = True
                        break
                    except Exception as e:
                        print(f"[Attempt {attempt + 1}/3] API Error: {e}")
                        time.sleep(2)

                if not success:
                    print(f"Failed to fetch pagination from {api_url} after 3 attempts.")
                    exit_reason = "502"
                    break

                length = len(self.image_urls)

                for mag in soup.select(".magnify[href]"):
                    self.resolve_url_to_bytes(executor, futures, download_image, mag["href"])

                if (len(self.image_urls) - length) > 0:
                    print(f"-> Found {len(self.image_urls) - length} new images (total queued: {len(futures)})")

                new_last = None
                countinf = soup.select("div.countinf")
                if countinf:
                    new_last = countinf[-1].get("data-id")

                if new_last == last_id or new_last is None:
                    self.recursions += 1
                elif new_last == last_id:
                    self.recursions = 0
                if self.recursions > 5:
                    exit_reason = "recursion - possible success"
                    break

                last_id = new_last

                # Save state after successful page parse
                try:
                    with open(state_file, "w") as f:
                        json.dump({"scroll": scroll, "last_id": last_id, "image_urls": list(self.image_urls)}, f)
                except Exception as e:
                    print(f"Failed to save state: {e}")

        except KeyboardInterrupt:
            exit_reason = "keyboard interrupt"
            print("\n[!] Scraping forcefully interrupted by user. Salvaging queued images...")

        # Wait for all background image downloads to resolve
        total_queued = len(futures)
        print(f"Waiting for {total_queued} background downloads to complete...")

        completed = 0

        try:
            for future in as_completed(futures):
                res = future.result()
                if res:
                    self.image_results.append(res)
                completed += 1
                if completed % 10 == 0 or completed == total_queued:
                    print(f"   Downloaded {completed} / {total_queued} images...")
        except KeyboardInterrupt:
            print(
                f"\n[!] Downloads forcefully cancelled by user! Aborting {total_queued - completed} remaining requests."
            )
            exit_reason = "keyboard interrupt"
            for future in futures:
                future.cancel()

        executor.shutdown()
        print(f"Successfully downloaded {len(self.image_results)} total images this session.")
        exit_reason = "success"

        # Clean up state file on successful deep completion
        if self.recursions > 5 and os.path.exists(state_file):
            try:
                os.remove(state_file)
                print("Scrape complete. State file cleaned up.")
            except Exception:
                pass

        if exit_reason == "502":
            return self.fetch()
        else:
            self.logger.log(f"exit reason: {exit_reason}")
            self.logger.log("contents of image_results:")
            for item in self.image_results:
                img, href = item
                self.logger.log(f"{href}: {type(img)}")
            return self.image_results

    def resolve_url_to_bytes(self, executor, futures, download_image, href):
        print("resolving href to bytes...")
        if href not in self.image_urls:
            self.logger.log(f"found NEW image url: {href}")
            self.image_urls.add(href)

            folder_path = "url_files\\" + self.blog_name + ".bdsmlr.com"
            if os.path.isdir(folder_path):
                file_name = href.split("/")[-1]
                if file_name.endswith("jpg") or file_name.endswith("png"):
                    file_name = file_name.replace(".jpg", ".jpeg").replace(".png", ".jpeg")
                if not os.path.isfile(os.path.join(folder_path, file_name)):
                    self.logger.log(f"no image file found at {os.path.join(folder_path, file_name)}, downloading...")
                    futures.append(executor.submit(download_image, href))
                else:
                    self.logger.log(f"image file found at {os.path.join(folder_path, file_name)}, reading...")
                    self.image_results.append(
                        (io.BytesIO(open(os.path.join(folder_path, file_name), "rb").read()), href)
                    )
            else:
                print("path not found at", folder_path)
                print("creating folder at", folder_path)
                os.mkdir(folder_path)
                return self.resolve_url_to_bytes(executor, futures, download_image, href)


class VipergirlsScraper:
    def __init__(self, url, *args):
        self.url = url
        self.images = self.get_images()

    def get_images(self):

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url)

            imgs = []
            for img in page.query_selector_all(".postcontent img"):
                imgs.append(img.get_attribute("src"))

            return imgs
        browser.close()

    def fetch(self):
        return self.images


class GenericScraper:
    def __init__(self, url):
        self.url = url

    def fetch(self):

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url)

            imgs = page.query_selector_all("img")
            img_urls = []
            for img in imgs:
                img_urls.append(img.get_attribute("src"))

            browser.close()

        return img_urls


class TumblrScraper:
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password

    def fetch(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                + "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="en-US",
                timezone_id="UTC",
            )
            page = context.new_page()
            page.set_default_navigation_timeout(0)
            page.goto("https://tumblr.com")
            page.get_by_role("button", name="Log in").click()
            page.get_by_role("button", name="Continue with email").click()
            page.get_by_role("textbox", name="email").fill(self.user)
            page.get_by_role("button", name="Next").click()
            page.get_by_role("textbox", name="password").fill(self.password)
            page.get_by_role("button", name="Log in").click()
            page.wait_for_load_state("commit")
            self.session = requests.Session()
            for cookie in context.cookies():
                self.session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])
            page.goto(self.url)
            imgs = page.query_selector_all(".RoN4R")
