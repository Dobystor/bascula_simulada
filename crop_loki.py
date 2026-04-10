from PIL import Image
import os

def crop_to_head_torso(image_path, output_path):
    img = Image.open(image_path)
    width, height = img.size
    
    # Define crop area for head and torso (centered, top 65%)
    # Let's take a square from the top.
    # Left, Upper, Right, Lower
    left = width * 0.1
    top = 0
    right = width * 0.9
    bottom = height * 0.65
    
    # Crop and resize back to original size or a standard avatar size
    cropped = img.crop((left, top, right, bottom))
    # resize to square
    min_dim = min(cropped.size)
    # Actually just crop a square from the top center
    new_width, new_height = img.size
    crop_size = min(new_width, new_height)
    
    # Better approach: center crop from top
    left = (new_width - crop_size) / 2
    top = 0
    right = (new_width + crop_size) / 2
    bottom = crop_size * 0.7 # Take only 70% of the square height to focus on head
    
    # Re-crop
    final_crop = img.crop((0, 0, width, int(height * 0.7)))
    # If the original was 1024x1024, now it's 1024x716.
    # We want a square for an avatar.
    
    # 3D avatars are usually centered.
    # Let's take the top-most square part.
    square_size = min(width, height)
    head_crop = img.crop((0, 0, square_size, square_size))
    # This might still show some legs. Let's zoom in further.
    zoom_factor = 0.6 # 60% of original
    zoom_size = int(square_size * zoom_factor)
    left = (width - zoom_size) // 2
    top = height // 12 # Start slightly below top to avoid cutting ears
    right = left + zoom_size
    bottom = top + zoom_size
    
    zoomed = img.crop((left, top, right, bottom))
    zoomed.save(output_path)
    print(f"Cropped image saved to {output_path}")

if __name__ == "__main__":
    src = r"c:\bascula_simuladaV2\yahtzee-app\assets\avatars\loki.png"
    dst = r"c:\bascula_simuladaV2\yahtzee-app\assets\avatars\loki_cropped.png"
    crop_to_head_torso(src, dst)
