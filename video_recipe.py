from flask import Blueprint, request, jsonify
from auth import token_required
import os
import tempfile
import time
import mimetypes
import io
import base64
import requests
import re
from google import genai
from PIL import Image

video_recipe_bp = Blueprint('video_recipe', __name__, url_prefix='/api/video-recipe')

def get_gemini_client():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")
    return genai.Client(api_key=api_key)

def detect_platform(url: str) -> str:
    """Detect which platform the URL is from"""
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'tiktok.com' in url_lower:
        return 'tiktok'
    return 'unknown'

def download_with_apify(url: str, output_path: str, platform: str) -> str:
    """Download video using Apify as fallback"""
    from apify_client import ApifyClient
    
    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not configured - cannot use Apify fallback")
    
    apify_client = ApifyClient(api_token)
    
    # Select the appropriate actor based on platform
    actor_map = {
        'youtube': 'apilabs/youtube-downloader',
        'instagram': 'apilabs/instagram-downloader',
        'tiktok': 'apilabs/tiktok-downloader',
    }
    
    actor_id = actor_map.get(platform)
    if not actor_id:
        raise ValueError(f"Unsupported platform for Apify: {platform}")
    
    print(f"Using Apify actor: {actor_id} for {platform}")
    
    # Define the input for the actor
    actor_input = {
        "audioOnly": False,
        "ffmpeg": True,
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
        "url": url
    }
    
    try:
        # Run the actor and wait for it to finish
        actor_call = apify_client.actor(actor_id).call(run_input=actor_input, timeout_secs=120)
        
        # Get the dataset from the run
        dataset_id = actor_call.get('defaultDatasetId')
        if not dataset_id:
            raise ValueError("No dataset returned from Apify actor")
        
        dataset_client = apify_client.dataset(dataset_id)
        items = dataset_client.list_items(limit=1, desc=True)
        
        if not items.items:
            raise ValueError("No items in Apify dataset")
        
        # Get the download link
        download_link = items.items[0].get('download_link') or items.items[0].get('downloadUrl') or items.items[0].get('url')
        if not download_link:
            raise ValueError("No download link found in Apify response")
        
        print(f"Apify download link: {download_link}")
        
        # Download the file
        response = requests.get(download_link, timeout=60)
        if response.status_code != 200:
            raise ValueError(f"Failed to download from Apify link: status {response.status_code}")
        
        # Determine file extension
        content_type = response.headers.get('Content-Type', 'video/mp4')
        extension = mimetypes.guess_extension(content_type.split(';')[0]) or '.mp4'
        
        final_path = output_path + extension
        with open(final_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Downloaded video via Apify: {final_path}")
        return final_path
        
    except Exception as e:
        raise Exception(f"Apify download failed: {str(e)}")

def download_video(url: str, output_path: str) -> str:
    """Download video from URL using yt-dlp, with Apify fallback"""
    platform = detect_platform(url)
    yt_dlp_error = None
    
    # First try yt-dlp
    try:
        import yt_dlp
        
        # Enhanced options to bypass rate limits and work on servers
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'best[ext=mp4][filesize<50M]/best[ext=mp4]/best[filesize<50M]/best',
            'quiet': True,
            'no_warnings': True,
            # User agent to appear as a regular browser
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            # Retry and timeout settings
            'retries': 3,
            'fragment_retries': 3,
            'socket_timeout': 30,
            # Extractor arguments for YouTube
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['dash', 'hls'],
                }
            },
            # Don't check certificates (helps on some servers)
            'nocheckcertificate': True,
            # Avoid geo-restrictions
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            # Sleep between requests to avoid rate limits
            'sleep_interval': 1,
            'max_sleep_interval': 3,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # yt-dlp may add extension, find the actual file
        if os.path.exists(output_path):
            return output_path
        # Check with common extensions
        for ext in ['.mp4', '.webm', '.mkv']:
            if os.path.exists(output_path + ext):
                return output_path + ext
        # Find any file in the directory
        dir_path = os.path.dirname(output_path)
        for f in os.listdir(dir_path):
            if f.startswith(os.path.basename(output_path).replace('.mp4', '')):
                return os.path.join(dir_path, f)
        
        return output_path
        
    except ImportError:
        yt_dlp_error = "yt-dlp not installed"
    except Exception as e:
        yt_dlp_error = str(e)
        print(f"yt-dlp failed: {yt_dlp_error}")
    
    # If yt-dlp failed and platform is supported, try Apify
    if yt_dlp_error and platform in ['youtube', 'instagram', 'tiktok']:
        print(f"Trying Apify fallback for {platform}...")
        try:
            return download_with_apify(url, output_path, platform)
        except Exception as apify_error:
            # Both failed, return combined error
            raise Exception(f"yt-dlp: {yt_dlp_error} | Apify: {str(apify_error)}")
    
    # If yt-dlp failed and Apify not applicable
    if yt_dlp_error:
        raise Exception(f"Error downloading video: {yt_dlp_error}")

def extract_frames(video_path: str, interval_seconds: int = 2):
    """Extract frames from video at specified interval"""
    import cv2
    
    frames = []
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30  # Default fallback
    frame_interval = int(fps * interval_seconds)
    frame_count = 0
    max_frames = 30  # Limit to prevent too many frames
    
    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            # Convert BGR to RGB
            import cv2
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            # Resize to reduce size
            pil_image.thumbnail((512, 512))
            frames.append(pil_image)
        
        frame_count += 1
    
    cap.release()
    return frames

def analyze_video_direct(client, video_path: str, model_name: str = 'gemini-2.0-flash') -> dict:
    """Analyze video directly by uploading to Gemini"""
    mime_type, _ = mimetypes.guess_type(video_path)
    if mime_type is None:
        mime_type = 'video/mp4'
    
    # Upload the video file
    with open(video_path, 'rb') as f:
        video_file = client.files.upload(file=f, config={'mime_type': mime_type})
    
    # Wait for video to be processed
    max_wait = 60  # 60 seconds max
    waited = 0
    while video_file.state == "PROCESSING" and waited < max_wait:
        time.sleep(2)
        waited += 2
        video_file = client.files.get(name=video_file.name)
    
    if video_file.state == "FAILED":
        raise ValueError("Video processing failed")
    
    prompt = """Analyze this cooking video and extract a detailed recipe. Return the response in this exact JSON format:

{
    "title": "Name of the dish",
    "description": "Brief description of the dish",
    "prepTime": 10,
    "cookTime": 20,
    "servings": 4,
    "difficulty": "Easy/Medium/Hard",
    "ingredients": [
        {"name": "ingredient name", "amount": "quantity with unit"}
    ],
    "steps": [
        "Step 1 instruction",
        "Step 2 instruction"
    ],
    "equipment": ["pan", "spatula"],
    "tips": ["cooking tip 1", "tip 2"],
    "nutritionPerServing": {
        "calories": 300,
        "protein": 25,
        "carbs": 30,
        "fat": 12
    },
    "tags": ["high-protein", "quick", "meal-prep"]
}

Be specific about ingredients and measurements. Estimate nutrition based on visible ingredients."""

    response = client.models.generate_content(
        model=model_name,
        contents=[video_file, prompt]
    )
    
    return parse_recipe_response(response.text)

def analyze_frames(client, frames: list, model_name: str = 'gemini-2.0-flash') -> dict:
    """Analyze extracted frames with Gemini"""
    prompt = f"""Analyze these {len(frames)} frames from a cooking video and extract a detailed recipe. Return the response in this exact JSON format:

{{
    "title": "Name of the dish",
    "description": "Brief description of the dish",
    "prepTime": 10,
    "cookTime": 20,
    "servings": 4,
    "difficulty": "Easy/Medium/Hard",
    "ingredients": [
        {{"name": "ingredient name", "amount": "quantity with unit"}}
    ],
    "steps": [
        "Step 1 instruction",
        "Step 2 instruction"
    ],
    "equipment": ["pan", "spatula"],
    "tips": ["cooking tip 1", "tip 2"],
    "nutritionPerServing": {{
        "calories": 300,
        "protein": 25,
        "carbs": 30,
        "fat": 12
    }},
    "tags": ["high-protein", "quick", "meal-prep"]
}}

Be specific about ingredients and measurements. Estimate nutrition based on visible ingredients."""

    # Convert frames to base64
    frame_parts = []
    for frame in frames:
        img_byte_arr = io.BytesIO()
        frame.save(img_byte_arr, format='JPEG', quality=85)
        img_bytes = img_byte_arr.getvalue()
        
        frame_parts.append({
            'inline_data': {
                'mime_type': 'image/jpeg',
                'data': base64.b64encode(img_bytes).decode()
            }
        })
    
    response = client.models.generate_content(
        model=model_name,
        contents=[prompt] + frame_parts
    )
    
    return parse_recipe_response(response.text)

def parse_recipe_response(text: str) -> dict:
    """Parse the AI response to extract recipe JSON"""
    import json
    import re
    
    # Try to extract JSON from the response
    # First, try to find JSON block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find raw JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            json_str = json_match.group(0)
        else:
            # Return a basic structure with the raw text
            return {
                "title": "Recipe from Video",
                "description": text[:200],
                "prepTime": 15,
                "cookTime": 30,
                "servings": 4,
                "difficulty": "Medium",
                "ingredients": [],
                "steps": [text],
                "equipment": [],
                "tips": [],
                "nutritionPerServing": {
                    "calories": 0,
                    "protein": 0,
                    "carbs": 0,
                    "fat": 0
                },
                "tags": [],
                "rawResponse": text
            }
    
    try:
        recipe = json.loads(json_str)
        # Ensure all required fields exist
        recipe.setdefault("title", "Recipe from Video")
        recipe.setdefault("description", "")
        recipe.setdefault("prepTime", 15)
        recipe.setdefault("cookTime", 30)
        recipe.setdefault("servings", 4)
        recipe.setdefault("difficulty", "Medium")
        recipe.setdefault("ingredients", [])
        recipe.setdefault("steps", [])
        recipe.setdefault("equipment", [])
        recipe.setdefault("tips", [])
        recipe.setdefault("nutritionPerServing", {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
        recipe.setdefault("tags", [])
        return recipe
    except json.JSONDecodeError:
        return {
            "title": "Recipe from Video",
            "description": text[:200],
            "prepTime": 15,
            "cookTime": 30,
            "servings": 4,
            "difficulty": "Medium",
            "ingredients": [],
            "steps": [text],
            "equipment": [],
            "tips": [],
            "nutritionPerServing": {
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0
            },
            "tags": [],
            "rawResponse": text
        }

@video_recipe_bp.route('/analyze', methods=['POST'])
@token_required
def analyze_video(current_user):
    """
    Analyze a cooking video and extract recipe
    
    Request body:
    {
        "url": "https://instagram.com/reel/...",
        "method": "direct" | "frames"  (optional, default: "direct")
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'Video URL is required'}), 400
        
        url = data['url']
        method = data.get('method', 'direct')
        
        # Initialize Gemini client
        client = get_gemini_client()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video")
            
            # Download video
            try:
                actual_path = download_video(url, video_path)
            except Exception as e:
                return jsonify({'error': f'Failed to download video: {str(e)}'}), 400
            
            # Analyze based on method
            try:
                if method == "frames":
                    frames = extract_frames(actual_path, interval_seconds=2)
                    if not frames:
                        return jsonify({'error': 'Could not extract frames from video'}), 400
                    recipe = analyze_frames(client, frames)
                else:
                    recipe = analyze_video_direct(client, actual_path)
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
                return jsonify({'error': f'Failed to analyze video: {error_msg}'}), 500
        
        return jsonify({
            'success': True,
            'recipe': recipe
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Video recipe error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500
