import cloudinary
import cloudinary.uploader
import os
import base64

# Configure Cloudinary from environment variables
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)


def upload_image(image_data: str, folder: str = "uploads", public_id: str = None) -> dict:
    """
    Upload an image to Cloudinary.
    
    Args:
        image_data: Base64 encoded image data (with or without data URL prefix)
        folder: Cloudinary folder to store the image
        public_id: Optional custom public ID for the image
    
    Returns:
        dict with 'url' and 'public_id' on success, or 'error' on failure
    """
    try:
        # Handle data URL format
        if image_data.startswith('data:image'):
            # Already in data URL format, Cloudinary accepts this
            upload_data = image_data
        else:
            # Pure base64, add data URL prefix
            upload_data = f"data:image/jpeg;base64,{image_data}"
        
        # Upload to Cloudinary
        upload_options = {
            'folder': folder,
            'resource_type': 'image',
            'overwrite': True,
        }
        
        if public_id:
            upload_options['public_id'] = public_id
        
        result = cloudinary.uploader.upload(upload_data, **upload_options)
        
        return {
            'url': result['secure_url'],
            'public_id': result['public_id']
        }
        
    except Exception as e:
        print(f"[CLOUDINARY ERROR] {str(e)}")
        return {'error': str(e)}


def delete_image(public_id: str) -> bool:
    """
    Delete an image from Cloudinary.
    
    Args:
        public_id: The public ID of the image to delete
    
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"[CLOUDINARY DELETE ERROR] {str(e)}")
        return False
