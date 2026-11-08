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

def clean_str(s: str) -> str:
    if not s:
        return ""
    # Strip Google Material icon codes (\ue000-\uf8ff)
    s = re.sub(r'[\ue000-\uf8ff]', '', s)
    # Normalize multiple whitespace
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def parse_sidebar_card(link_element) -> Place:
    place = Place()
    # Name from aria-label
    aria = link_element.get_attribute("aria-label") or ""
    place.name = clean_str(aria)

    parent = link_element.locator("xpath=..")
    raw_text = parent.inner_text()
    raw_lines = [clean_str(l) for l in raw_text.split("\n")]
    lines = [l for l in raw_lines if l and l != "Sponsorisé" and l != place.name]

    # Direct website link in the card if available
    try:
        web_links = parent.locator('a[href^="http"]:not([href*="google.com/maps"])').all()
        for wl in web_links:
            href = wl.get_attribute("href")
            if href and "google.com" not in href:
                place.website = href
                break
    except Exception:
        pass

    full_str = " · ".join(lines)

    # 1. Phone number (Algerian/International formats)
    phone_match = re.search(r'(?:\+?\d{1,4}[-.\s]?)?(?:\(?0\d{1,3}\)?[-.\s]?)?\d{2}[-.\s]?\d{2}[-.\s]?\d{2}[-.\s]?\d{2}', full_str)
    if phone_match:
        cand = phone_match.group(0).strip()
        digits = re.sub(r'\D', '', cand)
        if 8 <= len(digits) <= 14:
            place.phone_number = cand

    # 2. Rating & Reviews count (e.g. "4,8 (12)", "5,0 (1)", "4.3")
    rating_match = re.search(r'(\d+[.,]\d+)\s*(?:\((\d+[\s\d]*)\))?', full_str)
    if rating_match:
        try:
            place.reviews_average = float(rating_match.group(1).replace(',', '.'))
            if rating_match.group(2):
                place.reviews_count = int(re.sub(r'\s', '', rating_match.group(2)))
        except Exception:
            pass

    # 3. Categorize lines (type, address, hours)
    for line in lines:
        l_low = line.lower()
        if 'achat en magasin' in l_low or 'in-store shopping' in l_low:
            place.store_shopping = "Yes"
        if 'retrait en magasin' in l_low or 'in-store pickup' in l_low:
            place.in_store_pickup = "Yes"
        if 'livraison' in l_low or 'delivery' in l_low:
            place.store_delivery = "Yes"

        if any(h in l_low for h in ['ferme', 'ouvert', 'ouvre', 'open', 'closed']):
            clean_hours = line
            if place.phone_number and place.phone_number in clean_hours:
                clean_hours = clean_hours.replace(place.phone_number, "").strip(" ·")
            place.opens_at = clean_hours

        # Splitting by bullet
        parts = [p.strip() for p in line.split('·')]
        if len(parts) >= 2:
            cand_type = clean_str(parts[0])
            if not place.place_type and cand_type and not any(char.isdigit() for char in cand_type):
                place.place_type = cand_type
            if len(parts) > 1:
                for cand_addr in parts[1:]:
                    cand_addr = clean_str(cand_addr)
                    if cand_addr and not any(w in cand_addr.lower() for w in ['ferme', 'ouvert', 'ouvre', 'km', 'avis']) and cand_addr != place.phone_number:
                        if not place.address:
                            place.address = cand_addr
        elif len(parts) == 1:
            val = clean_str(parts[0])
            if val and not place.place_type and not any(char.isdigit() for char in val) and len(val) < 40:
                if not any(w in val.lower() for w in ['ferme', 'ouvert', 'ouvre', 'avis']):
                    place.place_type = val

    return place

def extract_text(page: Page, xpath: str) -> str:
    try:
        loc = page.locator(xpath)
        if loc.count() > 0:
            return loc.first.inner_text().strip()
    except Exception:
        pass
    return ""

def extract_place(page: Page, fallback_name: str = "") -> Place:
    place = Place()

    # Name extraction with multiple fallbacks
    name_selectors = [
        'h1.DUwDvf',
        'div.TIHn2 h1',
        'h1[class*="DUwDvf"]',
        'h1',
    ]
    name = ""
    for sel in name_selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                txt = clean_str(loc.first.inner_text())
                if txt and txt != "Résultats" and not txt.startswith("Sponsoris"):
                    name = txt
                    break
        except Exception:
            pass
    place.name = name or fallback_name

    # Address
    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
    place.address = clean_str(extract_text(page, address_xpath))
    if not place.address:
        try:
            addr_loc = page.locator('button[data-item-id="address"]')
            if addr_loc.count() > 0:
                place.address = clean_str(addr_loc.first.inner_text())
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
    place.place_type = clean_str(extract_text(page, place_type_xpath))
    if not place.place_type:
        place.place_type = clean_str(extract_text(page, '//button[contains(@class, "DkEaL")]'))

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
            place.opens_at = opens[1].replace("\u202f","").strip()
        else:
            place.opens_at = opens_at_raw.replace("\u202f","").strip()
    else:
        opens_at2_raw = extract_text(page, opens_at_xpath2)
        if opens_at2_raw:
            opens = opens_at2_raw.split('⋅')
            if len(opens) > 1:
                place.opens_at = opens[1].replace("\u202f","").strip()
            else:
                place.opens_at = opens_at2_raw.replace("\u202f","").strip()
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
    append: bool = False,
    min_rating: float = 0.0,
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
        launch_args = ["--start-maximized", "--new-window", "--no-default-browser-check"] if not headless else []
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
        if platform.system() == "Windows" and not headless:
            try:
                # Officially recommended Playwright channel for Google Chrome on desktop
                browser = p.chromium.launch(channel="chrome", headless=headless, slow_mo=slow_mo, args=launch_args)
            except Exception as e:
                logging.warning(f"Could not launch via channel='chrome' ({e}), falling back to bundled Chromium.")
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
        if not headless:
            try:
                page.bring_to_front()
            except Exception:
                pass

        # Crucial RAM optimization: abort heavy resource types only in headless/cloud mode
        if headless or platform.system() != "Windows":
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

            # Accept cookies dialog if present (fallback for FR, EN, IT, AR)
            cookie_selectors = [
                '//button[contains(., "Tout accepter") or contains(., "Accept all") or contains(., "I agree") or contains(., "Accetta tutto") or contains(., "قبول الكل") or contains(., "موافق")]',
                '//button[contains(@aria-label, "Tout accepter") or contains(@aria-label, "Accept all") or contains(@aria-label, "قبول")]',
                'form[action*="consent"] button',
                'button:has-text("Tout accepter")',
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("قبول الكل")',
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
            try:
                search_btn = page.locator("#searchbox-searchbutton, button[id*='searchbox-searchbutton'], button[aria-label='Rechercher'], button[aria-label='Search']").first
                if search_btn.is_visible(timeout=1000):
                    search_btn.click()
            except Exception:
                pass

            # Check if direct place page loaded
            time.sleep(3)
            if "/maps/place/" in page.url:
                place = extract_place(page)
                if place.name:
                    req_rating = 4.95 if min_rating >= 5.0 else min_rating
                    if min_rating > 0 and (place.reviews_average is None or place.reviews_average < req_rating):
                        logging.info(f"FILTERED_OUT: '{place.name}' a une note de {place.reviews_average or 'N/A'}⭐ (inférieure à {min_rating}⭐)")
                    else:
                        places.append(place)
                        logging.info(f"EXTRACTED [1/1]: {place.name} (⭐ {place.reviews_average or 'N/A'})")
                        if output_path:
                            save_places_to_csv(places, output_path, append=append)
                    return places

            try:
                page.wait_for_selector('//a[contains(@href, "/maps/place")]', timeout=25000)
            except Exception as e:
                logging.warning(f"Attente de résultats terminée ou aucun résultat direct: {e}")

            if save_screenshots:
                os.makedirs("screenshots", exist_ok=True)
                page.screenshot(path="screenshots/1_search_results.png")

            listings_locator = page.locator('//a[contains(@href, "/maps/place")]')
            previously_counted = 0
            same_count_retries = 0
            target_scroll_count = total if min_rating <= 0 else max(total * 4, 30)
            while True:
                found = listings_locator.count()
                logging.info(f"Currently Found: {found}")
                if found >= target_scroll_count:
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

            raw_listings = page.locator('//a[contains(@href, "/maps/place")]').all()
            logging.info(f"Total Found: {len(raw_listings)}")
            for idx, listing in enumerate(raw_listings):
                if len(places) >= total:
                    break
                try:
                    # In visual mode, visibly scroll and highlight the card
                    if not headless:
                        try:
                            listing.scroll_into_view_if_needed(timeout=2000)
                            listing.hover(timeout=1500)
                        except Exception:
                            pass

                    # High-speed, memory-safe card extraction
                    place = parse_sidebar_card(listing)

                    # In non-headless desktop visual mode, click to show the supplier details panel on screen
                    if not headless:
                        try:
                            parent = listing.locator("xpath=..")
                            parent.click(timeout=2000)
                            page.wait_for_timeout(1200)
                            full_place = extract_place(page, fallback_name=place.name)
                            if full_place.name:
                                if full_place.phone_number: place.phone_number = full_place.phone_number
                                if full_place.address: place.address = full_place.address
                                if full_place.website: place.website = full_place.website
                                if full_place.reviews_average: place.reviews_average = full_place.reviews_average
                                if full_place.reviews_count: place.reviews_count = full_place.reviews_count
                        except Exception:
                            pass

                    if not place.name:
                        logging.warning(f"No name found for listing {idx+1}, skipping.")
                        continue

                    # Filter by minimum rating (e.g. 5.0 stars)
                    if min_rating > 0:
                        req_rating = 4.95 if min_rating >= 5.0 else min_rating
                        if place.reviews_average is None or place.reviews_average < req_rating:
                            logging.info(f"FILTERED_OUT: '{place.name}' a une note de {place.reviews_average or 'N/A'}⭐ (inférieure à {min_rating}⭐)")
                            continue

                    places.append(place)
                    logging.info(f"EXTRACTED [{len(places)}/{total}]: {place.name} (⭐ {place.reviews_average})")
                    if output_path:
                        if append:
                            save_places_to_csv([place], output_path, append=True)
                        else:
                            save_places_to_csv(places, output_path, append=False)
                except Exception as e:
                    logging.warning(f"Failed to extract listing {idx+1}: {e}")

            if not headless and len(places) > 0:
                # Brief pause so the user sees the final completed state on Google Maps
                page.wait_for_timeout(4000)
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
    parser.add_argument("--min-rating", type=float, default=0.0, help="Minimum rating (1.0 to 5.0) to filter places")
    args = parser.parse_args()
    search_for = args.search or "turkish stores in toronto Canada"
    total = args.total or 1
    output_path = args.output
    append = args.append
    headless = args.headless
    slow_mo = args.slow_mo
    record_video = args.record_video
    save_screenshots = args.screenshots
    min_rating = args.min_rating
    places = scrape_places(
        search_for,
        total,
        headless=headless,
        slow_mo=slow_mo,
        record_video_dir=record_video,
        save_screenshots=save_screenshots,
        output_path=output_path,
        append=append,
        min_rating=min_rating
    )
    if not append:
        save_places_to_csv(places, output_path, append=False)

if __name__ == "__main__":
    main()
