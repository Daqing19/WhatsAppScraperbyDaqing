import os
import time
import requests
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 👇 Toggle this to True (headless) or False (visible window)
headless = True

def generate_placeholder(path, name='?'):
    initial = name[0].upper() if name else '?'
    img = Image.new('RGB', (640, 640), color=(100, 100, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 320)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), initial, font=font)
    x = (640 - (bbox[2] - bbox[0])) / 2
    y = (640 - (bbox[3] - bbox[1])) / 2
    draw.text((x, y), initial, fill='white', font=font)
    img.save(path)

def is_valid_whatsapp_number(driver, number):
    url = f"https://web.whatsapp.com/send?phone={number}&text&app_absent=0"
    driver.get(url)
    time.sleep(3)
    return not driver.find_elements(By.XPATH, '//*[contains(text(),"Phone number shared via url is invalid")]')

def get_contact_info(driver, number, profile_pics_folder):
    time.sleep(2)
    try:
        name_elem = driver.find_element(By.XPATH, '//header//span[@title]')
        name = name_elem.get_attribute('title')
    except:
        name = ""

    try:
        driver.find_element(By.XPATH, '//header').click()
        time.sleep(2)
        about_elem = driver.find_element(By.XPATH, '//div[contains(text(),"About")]/following-sibling::div')
        about = about_elem.text.strip()
    except:
        about = ""

    os.makedirs(profile_pics_folder, exist_ok=True)
    clean_number = number.replace('+', '').replace(' ', '').replace('-', '')
    file_path = os.path.join(profile_pics_folder, f"{clean_number}.jpg")
    photo_path = ""

    try:
        img_elem = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.XPATH, '//img[contains(@src, "whatsapp.net/v/")]'))
        )
        img_url = img_elem.get_attribute('src')
        if img_url and img_url.startswith("https://"):
            img_data = requests.get(img_url, timeout=5).content
            with open(file_path, 'wb') as f:
                f.write(img_data)
            photo_path = file_path
        else:
            raise Exception("No downloadable photo URL")
    except Exception:
        generate_placeholder(file_path, name)
        photo_path = file_path

    try:
        driver.find_element(By.XPATH, '//span[@data-icon="x"]').click()
    except:
        pass

    return {
        "found": True,
        "name": name,
        "about": about,
        "photo_path": photo_path
    }

def safe_get_contact_info(driver, number, profile_pics_folder, retries=3, delay=10):
    for attempt in range(1, retries + 1):
        try:
            return get_contact_info(driver, number, profile_pics_folder)
        except Exception:
            if attempt == retries:
                return {"found": False}
            time.sleep(delay * attempt)

def main(user_folder):
    options = Options()
    user_data_path = os.path.abspath("User_Data")
    options.add_argument(f'--user-data-dir={user_data_path}')
    options.add_argument('--profile-directory=Default')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    if headless:
        options.add_argument('--headless=new')

    driver = webdriver.Chrome(options=options)
    driver.get("https://web.whatsapp.com")
    print("🔐 Please scan QR code in browser window...")

    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.ID, "side"))
    )

    output_path = os.path.join(user_folder, 'output.csv')
    profile_pics_folder = os.path.join(user_folder, 'profile_pics')
    progress_path = os.path.join(user_folder, 'progress.txt')
    upload_path = os.path.join(user_folder, 'uploads', 'numbers.txt')

    os.makedirs(profile_pics_folder, exist_ok=True)

    if os.path.exists(output_path):
        df_existing = pd.read_csv(output_path, encoding='utf-8-sig')
        done_numbers = set(str(n).strip() for n in df_existing['Phone Number'])
    else:
        df_existing = pd.DataFrame(columns=['Phone Number', 'Name', 'About', 'Photo Path', 'Timestamp'])
        done_numbers = set()

    with open(upload_path, 'r') as f:
        numbers = [line.strip() for line in f if line.strip()]

    total = len(numbers)

    for i, number in enumerate(numbers, 1):
        with open(progress_path, 'w') as pf:
            pf.write(f'{i}/{total}')

        if number in done_numbers:
            print(f"⏭️ Skipping {number} (already processed)")
            continue

        print(f"📞 Checking {number}...")

        try:
            if not is_valid_whatsapp_number(driver, number):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df_existing.loc[len(df_existing)] = [number, '', '', '', timestamp]
                df_existing.to_csv(output_path, index=False, encoding='utf-8-sig')
                print("❌ Not found on WhatsApp")
                continue

            info = safe_get_contact_info(driver, number, profile_pics_folder)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df_existing.loc[len(df_existing)] = [number, info['name'], info['about'], info['photo_path'], timestamp]
            df_existing.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"✅ Found: {info['name']}")
        except Exception as e:
            print(f"⚠️ Failed to process {number}: {e}")

        time.sleep(3)

    driver.quit()
    print(f"\n✅ Done! Results saved to {output_path} and {profile_pics_folder}/")

if __name__ == "__main__":
    # For standalone testing — specify user_folder manually
    main("user_data/daqing")
