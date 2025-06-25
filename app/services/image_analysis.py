from PIL import Image
import numpy as np
import piexif
from typing import Dict, Any
import io

def analyze_image_spectrum(img: Image.Image) -> Image.Image:
    """
    Generate a frequency spectrum analysis of the image using FFT.
    """
    # Convert image to grayscale
    gray_img = img.convert('L')
    img_array = np.array(gray_img)
    
    # Apply FFT
    fft = np.fft.fft2(img_array)
    fft_shift = np.fft.fftshift(fft)
    magnitude_spectrum = 20 * np.log(np.abs(fft_shift) + 1)
    
    # Normalize to 0-255
    magnitude_spectrum = ((magnitude_spectrum - magnitude_spectrum.min()) * 
                         (255 / (magnitude_spectrum.max() - magnitude_spectrum.min())))
    
    # Convert back to image
    spectrum_img = Image.fromarray(magnitude_spectrum.astype(np.uint8))
    return spectrum_img

def extract_metadata(img: Image.Image) -> Dict[str, Any]:
    """
    Extract metadata from the image including EXIF data.
    """
    metadata = {}
    
    # Basic image info
    metadata['format'] = img.format
    metadata['mode'] = img.mode
    metadata['size'] = img.size
    
    # Try to extract EXIF data
    try:
        exif_dict = piexif.load(img.info.get('exif', b''))
        
        # Extract relevant EXIF tags
        if '0th' in exif_dict:
            for tag in piexif.TAGS['0th']:
                if tag in exif_dict['0th']:
                    value = exif_dict['0th'][tag]
                    # Convert bytes to string if necessary
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8')
                        except UnicodeDecodeError:
                            value = str(value)
                    metadata[f'exif_{piexif.TAGS["0th"][tag]["name"]}'] = value
                    
        if 'Exif' in exif_dict:
            for tag in piexif.TAGS['Exif']:
                if tag in exif_dict['Exif']:
                    value = exif_dict['Exif'][tag]
                    # Convert bytes to string if necessary
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8')
                        except UnicodeDecodeError:
                            value = str(value)
                    metadata[f'exif_{piexif.TAGS["Exif"][tag]["name"]}'] = value
    except:
        metadata['exif_error'] = 'No EXIF data available'
    
    return metadata 