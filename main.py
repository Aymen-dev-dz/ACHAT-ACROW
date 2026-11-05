import logging
import sys
from typing import List, Optional

# Ensure standard streams are unbuffered and UTF-8 encoded for real-time live console streaming
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True, errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True, errors="replace")
except Exception:
    pass
from playwright.sync_api import sync_playwright, Page
from dataclasses import dataclass, asdict
import pandas as pd
import argparse
import platform
import time
import os
import re

@dataclass
class Place:
    name: str = ""
    address: str = ""
    website: str = ""
    phone_number: str = ""
    reviews_count: Optional[int] = None
    reviews_average: Optional[float] = None
    store_shopping: str = "No"
    in_store_pickup: str = "No"
    store_delivery: str = "No"
    place_type: str = ""
    opens_at: str = ""
    introduction: str = ""

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

def extract_text(page: Page, xpath: str) -> str:
    try:
        loc = page.locator(xpath)
        if loc.count() > 0:
            return loc.first.inner_text().strip()
    except Exception as e:
        pass
    return ""

def extract_place(page: Page, fallback_name: str = "") -> Place:
    place = Place()

    # Name extraction with multiple fallbacks
    name_selectors = [
        '//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]',
        '//h1[contains(@class, "DUwDvf")]',
        'h1.DUwDvf',
        'div.TIHn2 h1',
        '//div[contains(@class, "TIHn2")]//h1',
        'h1',
    ]
    name = ""
    for sel in name_selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                txt = loc.first.inner_text().strip()
                if txt and txt != "Résultats" and not txt.startswith("Sponsoris"):
                    name = txt
                    break
        except Exception:
            pass
    place.name = name or fallback_name

    # Address
    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
    place.address = extract_text(page, address_xpath)
    if not place.address:
        try:
            addr_loc = page.locator('button[data-item-id="address"]')
            if addr_loc.count() > 0:
                place.address = addr_loc.first.inner_text().strip()
        except Exception:
            pass

    # Website
    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
    place.website = extract_text(page, website_xpath)
    if not place.website:
        try:
            w_loc = page.locator('a[data-item-id="authority"]')
            if w_loc.count() > 0:
                href = w_loc.first.get_attribute("href")
                if href and href.startswith("http"):
                    place.website = href
        except Exception:
            pass

    # Phone number
    phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
    place.phone_number = extract_text(page, phone_number_xpath)
    if not place.phone_number:
        try:
            p_loc = page.locator('button[data-item-id*="phone:tel:"]')
            if p_loc.count() > 0:
                data_id = p_loc.first.get_attribute("data-item-id") or ""
                if "phone:tel:" in data_id:
                    place.phone_number = data_id.split("phone:tel:")[-1].strip()
        except Exception:
            pass

    # Place Type
    place_type_xpath = '//div[@class="LBgpqf"]//button[@class="DkEaL "]'
    place.place_type = extract_text(page, place_type_xpath)
    if not place.place_type:
        place.place_type = extract_text(page, '//button[contains(@class, "DkEaL")]')

    # Introduction
    intro_xpath = '//div[@class="WeS02d fontBodyMedium"]//div[@class="PYvSYb "]'
    place.introduction = extract_text(page, intro_xpath) or "None Found"

    # Reviews Count
    reviews_count_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span//span//span[@aria-label]'
    reviews_count_raw = extract_text(page, reviews_count_xpath)
    if not reviews_count_raw:
        for alt_xpath in [
            '//div[@class="F7nice"]//span[2]',
            '//button[contains(@aria-label, "avis") or contains(@aria-label, "reviews") or contains(@aria-label, "review")]',
            '//div[@class="TIHn2 "]//span[contains(@aria-label, "avis") or contains(@aria-label, "reviews")]',
            '//button[@jsaction="pane.reviewChart.moreReviews"]',
        ]:
            reviews_count_raw = extract_text(page, alt_xpath)
            if reviews_count_raw:
                break
    if reviews_count_raw:
        try:
            digits = re.sub(r'[^\d]', '', reviews_count_raw)
            if digits:
                place.reviews_count = int(digits)
        except Exception:
            pass

    # Reviews Average
    reviews_average_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span[@aria-hidden]'
    reviews_avg_raw = extract_text(page, reviews_average_xpath)
    if not reviews_avg_raw:
        reviews_avg_raw = extract_text(page, '//div[@class="F7nice"]//span[1]')
    if reviews_avg_raw:
        try:
            match = re.search(r'\d+(?:[.,]\d+)?', reviews_avg_raw)
            if match:
                place.reviews_average = float(match.group(0).replace(',', '.'))
        except Exception:
            pass

    # Store Info
    info1 = '//div[@class="LTs0Rc"][1]'
    info2 = '//div[@class="LTs0Rc"][2]'
    info3 = '//div[@class="LTs0Rc"][3]'
    for idx, info_xpath in enumerate([info1, info2, info3]):
        info_raw = extract_text(page, info_xpath)
        if info_raw:
            temp = info_raw.split('·')
            if len(temp) > 1:
                check = temp[1].replace("\n", "").lower()
                if 'shop' in check or 'achat' in check:
                    place.store_shopping = "Yes"
                if 'pickup' in check or 'retrait' in check:
                    place.in_store_pickup = "Yes"
                if 'delivery' in check or 'livraison' in check:
                    place.store_delivery = "Yes"

    # Opens At
    opens_at_xpath = '//button[contains(@data-item-id, "oh")]//div[contains(@class, "fontBodyMedium")]'
    opens_at_xpath2 = '//div[@class="MkV9"]//span[@class="ZDu9vd"]//span[2]'
    opens_at_raw = extract_text(page, opens_at_xpath)
    if opens_at_raw:
        opens = opens_at_raw.split('⋅')
        if len(opens) > 1:
            place.opens_at = opens[1].replace("\u202f","")
        else:
            place.opens_at = opens_at_raw.replace("\u202f","")
    else:
        opens_at2_raw = extract_text(page, opens_at_xpath2)
        if opens_at2_raw:
            opens = opens_at2_raw.split('⋅')
            if len(opens) > 1:
                place.opens_at = opens[1].replace("\u202f","")
            else:
                place.opens_at = opens_at2_raw.replace("\u202f","")
    return place

def attach_to_default_desktop():
    if platform.system() == "Windows":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW("Default", 0, False, 0x10000000)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
                user32.SwitchDesktop(hdesk)
        except Exception as e:
            logging.warning(f"Could not attach to Default desktop: {e}")

def scrape_places(
    search_for: str,
    total: int,
    headless: bool = False,
    slow_mo: int = 0,
    record_video_dir: Optional[str] = None,
    save_screenshots: bool = False,
    output_path: Optional[str] = None,
    append: bool = False
) -> List[Place]:
    setup_logging()

    # Cloud environment auto-detection (Render, Docker, Linux without DISPLAY)
    if not headless and platform.system() != "Windows" and not os.environ.get("DISPLAY"):
        logging.info("Environnement cloud sans écran détecté (Docker/Linux) : forçage du mode Headless.")
        headless = True

    if not headless:
        attach_to_default_desktop()
    places: List[Place] = []
    with sync_playwright() as p:
        launch_args = ["--start-maximized"] if not headless else []
        # Essential low-memory args for cloud containers (Render 512MB RAM cap)
        if headless or platform.system() != "Windows":
            launch_args.extend([
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
                "--disable-translate",
                "--mute-audio",
                "--no-first-run",
                "--safebrowsing-disable-auto-update",
                "--renderer-process-limit=1",
                "--js-flags=--max-old-space-size=128",
            ])
        if platform.system() == "Windows":
            chrome_candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]
            browser_path = next((path for path in chrome_candidates if os.path.isfile(path)), None)
            if browser_path:
                browser = p.chromium.launch(executable_path=browser_path, headless=headless, slow_mo=slow_mo, args=launch_args)
            else:
                browser = p.chromium.launch(headless=headless, slow_mo=slow_mo, args=launch_args)
        else:
            browser = p.chromium.launch(headless=headless, slow_mo=slow_mo, args=launch_args)

        context_kwargs = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "locale": "fr-FR",
        }
        if record_video_dir:
            os.makedirs(record_video_dir, exist_ok=True)
            context_kwargs["record_video_dir"] = record_video_dir
            context_kwargs["record_video_size"] = {"width": 1280, "height": 720}
        elif not headless:
            context_kwargs["no_viewport"] = True

        context = browser.new_context(**context_kwargs)

        # Inject consent cookie (SOCS) to bypass Google cookie banner entirely in European servers (Render Frankfurt)
        try:
            context.add_cookies([{
                "name": "SOCS",
                "value": "CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwODI5LjA3X3AwGgJmciACGgYIgLCspwY",
                "domain": ".google.com",
                "path": "/"
            }])
        except Exception:
            pass

        page = context.new_page()

        # Crucial RAM optimization: abort heavy resource types (image, media, font)
        # Google Maps HTML DOM contains all text, addresses, phones, links, and ratings.
        # Blocking images reduces Chromium memory footprint from ~450MB to <90MB.
        def _route_filter(route):
            try:
                req = route.request
                if req.resource_type in ["image", "media", "font"]:
                    route.abort()
                    return
                u = req.url
                if "google-analytics" in u or "/log?" in u or "stats.g." in u or "play.google.com/log" in u:
                    route.abort()
                    return
                route.continue_()
            except Exception:
                try:
                    route.abort()
                except Exception:
                    pass

        try:
            page.route("**/*", _route_filter)
        except Exception:
            pass

        try:
            page.goto("https://www.google.com/maps?hl=fr", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(1000)

            # Accept cookies dialog if present (fallback)
            cookie_selectors = [
                '//button[contains(., "Tout accepter") or contains(., "Accept all") or contains(., "I agree") or contains(., "Accetta tutto")]',
                '//button[contains(@aria-label, "Tout accepter") or contains(@aria-label, "Accept all")]',
                'form[action*="consent"] button',
                'button:has-text("Tout accepter")',
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
            ]
            for sel in cookie_selectors:
                try:
                    c_btn = page.locator(sel).first
                    if c_btn.is_visible(timeout=1500):
                        c_btn.click()
                        page.wait_for_timeout(1000)
                        break
                except Exception:
                    pass

            search_input = page.locator("#searchboxinput, input[name='q']").first
            try:
                search_input.wait_for(state="visible", timeout=15000)
            except Exception:
                pass
            search_input.fill(search_for)
            page.keyboard.press("Enter")

            # Check if direct place page loaded
            time.sleep(3)
            if "/maps/place/" in page.url:
                place = extract_place(page)
                if place.name:
                    places.append(place)
                    logging.info(f"EXTRACTED [1/1]: {place.name}")
                    if output_path:
                        save_places_to_csv(places, output_path, append=append)
                    return places

            try:
                page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=25000)
            except Exception as e:
                logging.warning(f"Attente de résultats terminée ou aucun résultat direct: {e}")

            if save_screenshots:
                os.makedirs("screenshots", exist_ok=True)
                page.screenshot(path="screenshots/1_search_results.png")

            listings_locator = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]')
            previously_counted = 0
            same_count_retries = 0
            while True:
                found = listings_locator.count()
                logging.info(f"Currently Found: {found}")
                if found >= total:
                    break
                if listings_locator.count() > 0:
                    try:
                        listings_locator.last.hover()
                    except Exception:
                        pass
                page.mouse.wheel(0, 10000)
                time.sleep(2)
                found = listings_locator.count()
                if found == previously_counted:
                    same_count_retries += 1
                    if same_count_retries >= 3:
                        logging.info("Arrived at all available")
                        break
                else:
                    same_count_retries = 0
                previously_counted = found

            raw_listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()[:total]
            logging.info(f"Total Found: {len(raw_listings)}")
            for idx, listing in enumerate(raw_listings):
                try:
                    fallback_name = listing.get_attribute("aria-label") or ""
                    parent = listing.locator("xpath=..")
                    try:
                        parent.scroll_into_view_if_needed()
                        parent.click()
                    except Exception:
                        listing.click()

                    try:
                        page.wait_for_selector('h1.DUwDvf, h1[class*="DUwDvf"], div.TIHn2 h1', timeout=8000)
                    except Exception:
                        time.sleep(1.5)

                    if save_screenshots and idx < 3:
                        page.screenshot(path=f"screenshots/place_{idx+1}.png")

                    place = extract_place(page, fallback_name=fallback_name)
                    if place.name:
                        places.append(place)
                        target_total = min(total, len(raw_listings))
                        logging.info(f"EXTRACTED [{len(places)}/{target_total}]: {place.name}")
                        if output_path:
                            if append:
                                save_places_to_csv([place], output_path, append=True)
                            else:
                                save_places_to_csv(places, output_path, append=False)
                    else:
                        logging.warning(f"No name found for listing {idx+1}, skipping.")
                except Exception as e:
                    logging.warning(f"Failed to extract listing {idx+1}: {e}")
        finally:
            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
    return places

def save_places_to_csv(places: List[Place], output_path: str = "result.csv", append: bool = False):
    df = pd.DataFrame([asdict(place) for place in places])
    if not df.empty:
        file_exists = os.path.isfile(output_path)
        mode = "a" if append else "w"
        header = not (append and file_exists)
        df.to_csv(output_path, index=False, mode=mode, header=header, encoding="utf-8-sig")
        logging.info(f"Saved {len(df)} places to {output_path} (append={append})")
    else:
        logging.warning("No data to save. DataFrame is empty.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str, help="Search query for Google Maps")
    parser.add_argument("-t", "--total", type=int, help="Total number of results to scrape")
    parser.add_argument("-o", "--output", type=str, default="result.csv", help="Output CSV file path")
    parser.add_argument("--append", action="store_true", help="Append results to the output file instead of overwriting")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (without visible UI)")
    parser.add_argument("--slow-mo", type=int, default=0, help="Slow down Playwright actions by N milliseconds (useful for watching)")
    parser.add_argument("--record-video", type=str, default=None, help="Directory to save video recordings")
    parser.add_argument("--screenshots", action="store_true", help="Save step-by-step screenshots to screenshots/")
    args = parser.parse_args()
    search_for = args.search or "turkish stores in toronto Canada"
    total = args.total or 1
    output_path = args.output
    append = args.append
    headless = args.headless
    slow_mo = args.slow_mo
    record_video = args.record_video
    save_screenshots = args.screenshots
    places = scrape_places(
        search_for,
        total,
        headless=headless,
        slow_mo=slow_mo,
        record_video_dir=record_video,
        save_screenshots=save_screenshots,
        output_path=output_path,
        append=append
    )
    if not append:
        save_places_to_csv(places, output_path, append=False)

if __name__ == "__main__":
    main()
