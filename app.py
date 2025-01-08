import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import validators
import time

# Configure caching
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_website(url):
    """Fetch website content with retries and caching."""
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,  # number of retries
        backoff_factor=1,  # wait 1, 2, 4 seconds between retries
        status_forcelist=[500, 502, 503, 504]  # retry on these HTTP status codes
    )
    
    # Create session with retry strategy
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        raise e

def clean_url(url):
    """Normalize and validate URL format."""
    if not url:
        return None
        
    # Remove leading/trailing whitespace
    url = url.strip()
    
    # Add https if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # Validate URL format
    if not validators.url(url):
        return None
        
    return url

def get_platform_signatures():
    """Return dictionary of platform signatures to look for."""
    # [Previous platform signatures remain the same]
    return {
        'WordPress': [
            ('meta', {'name': 'generator', 'content': re.compile('WordPress', re.I)}),
            ('link', {'rel': 'pingback'}),
            ('script', {'src': re.compile('wp-includes|wp-content', re.I)}),
        ],
        # ... [rest of signatures]
    }

def analyze_headers(headers):
    """Analyze response headers for platform hints."""
    header_scores = {}
    
    server = headers.get('Server', '').lower()
    powered_by = headers.get('X-Powered-By', '').lower()
    
    if 'apache' in server:
        header_scores['Apache'] = 100
    if 'nginx' in server:
        header_scores['Nginx'] = 100
    if 'php' in powered_by:
        header_scores['PHP'] = 100
        
    return header_scores

def get_confidence_score(matches, total_checks, header_matches=0):
    """Calculate confidence score with header information."""
    base_score = (matches / total_checks) * 100
    header_bonus = min(20, header_matches * 10)  # Cap header bonus at 20%
    return min(100, base_score + header_bonus)

def detect_platform(url):
    """Detect the platform/framework used by a website."""
    try:
        # Fetch website content
        response = fetch_website(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Analyze headers
        header_scores = analyze_headers(response.headers)
        
        # Initialize results
        detected_platforms = []
        
        # Check signatures for each platform
        signatures = get_platform_signatures()
        for platform, checks in signatures.items():
            matches = 0
            total_checks = len(checks)
            
            for tag, attrs in checks:
                elements = soup.find_all(tag, attrs)
                if elements:
                    matches += 1
                    # Bonus for multiple matches
                    if len(elements) > 1:
                        matches += 0.5
            
            # Calculate confidence score with header information
            if matches > 0:
                header_bonus = 1 if platform.lower() in str(header_scores).lower() else 0
                confidence = get_confidence_score(matches, total_checks, header_bonus)
                
                # Include even low confidence results, but mark them
                detected_platforms.append({
                    'platform': platform,
                    'confidence': round(confidence, 1),
                    'reliability': 'high' if confidence >= 70 else 'medium' if confidence >= 40 else 'low'
                })
        
        # Add header-only detections
        for platform, confidence in header_scores.items():
            if not any(p['platform'] == platform for p in detected_platforms):
                detected_platforms.append({
                    'platform': platform,
                    'confidence': confidence,
                    'reliability': 'high'
                })
        
        # Sort by confidence score
        detected_platforms.sort(key=lambda x: x['confidence'], reverse=True)
        
        return detected_platforms if detected_platforms else [{
            'platform': 'No platform detected',
            'confidence': 0,
            'reliability': 'none'
        }]
        
    except requests.exceptions.ConnectionError:
        return [{'platform': 'Could not connect to website. Please check the URL and try again.', 'confidence': 0, 'reliability': 'error'}]
    except requests.exceptions.Timeout:
        return [{'platform': 'Request timed out. The website took too long to respond.', 'confidence': 0, 'reliability': 'error'}]
    except requests.exceptions.RequestException as e:
        return [{'platform': 'An error occurred while analyzing the website. Please try again.', 'confidence': 0, 'reliability': 'error'}]

# Streamlit UI
st.set_page_config(page_title='Website Platform Detector', layout='wide')

st.title('Website Platform Detector')
st.write('Enter a website URL to detect its platform.')

# URL input with validation feedback
url = st.text_input('Website URL', placeholder='example.com')

if url:
    # Clean and validate URL
    cleaned_url = clean_url(url)
    
    if cleaned_url:
        # Show spinner during detection
        with st.spinner('Analyzing...'):
            try:
                platforms = detect_platform(cleaned_url)
                
                # Display results with visual indicators
                for platform in platforms:
                    if not platform['platform'].startswith(('Error:', 'Could not', 'An error')):
                        # Use different visual styles based on confidence
                        if platform['reliability'] == 'high':
                            st.success(f"{platform['platform']}: {platform['confidence']}%")
                        elif platform['reliability'] == 'medium':
                            st.info(f"{platform['platform']}: {platform['confidence']}%")
                        elif platform['reliability'] == 'low':
                            st.warning(f"{platform['platform']}: {platform['confidence']}%")
                    else:
                        st.error(platform['platform'])
                        
            except Exception as e:
                st.error('An unexpected error occurred. Please try again.')
    else:
        st.error('Please enter a valid URL')
