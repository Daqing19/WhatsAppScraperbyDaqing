import os
import pandas as pd
from PIL import Image

def main(username):
    print(f"[INFO] Running WhatsApp scraper for user: {username}")

    # Setup user-specific folders
    base_upload_dir = f'uploads/{username}'
    base_output_file = f'outputs/{username}_output.csv'
    base_profile_dir = f'static/profile_pics/{username}'

    os.makedirs(base_upload_dir, exist_ok=True)
    os.makedirs(base_profile_dir, exist_ok=True)
    os.makedirs('outputs', exist_ok=True)  # ensure outputs folder exists

    # Example: process uploaded images in user upload dir
    image_files = [f for f in os.listdir(base_upload_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    result_data = []

    for img_name in image_files:
        img_path = os.path.join(base_upload_dir, img_name)
        print(f"[INFO] Processing image: {img_path}")

        try:
            # simulate image processing
            img = Image.open(img_path)
            width, height = img.size

            # save to user profile folder (resized copy for example)
            profile_path = os.path.join(base_profile_dir, img_name)
            img.thumbnail((200, 200))
            img.save(profile_path)

            result_data.append({
                'image_name': img_name,
                'width': width,
                'height': height,
                'profile_path': profile_path
            })

        except Exception as e:
            print(f"[ERROR] Failed to process {img_name}: {e}")

    # Save result to user-specific output CSV
    if result_data:
        df = pd.DataFrame(result_data)
        df.to_csv(base_output_file, index=False)
        print(f"[SUCCESS] Saved output to: {base_output_file}")
    else:
        print(f"[WARNING] No valid images processed for user: {username}")
