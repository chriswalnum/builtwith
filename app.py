import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import validators
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure caching
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_website(url):
    """Fetch website content with retries and caching."""
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    
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
        logger.error(f"Error fetching {url}: {str(e)}")
        raise e

def clean_url(url):
    """Normalize and validate URL format."""
    if not url:
        return None
        
    url = url.strip()
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    url = url.rstrip('/')
    
    if not validators.url(url):
        return None
        
    return url

def get_platform_signatures():
    """Return dictionary of platform signatures to look for."""
    return {
        'WordPress': [
            ('meta', {'name': 'generator', 'content': re.compile('WordPress', re.I)}),
            ('link', {'rel': 'pingback'}),
            ('script', {'src': re.compile('wp-includes|wp-content', re.I)}),
            ('link', {'href': re.compile('wp-content|wp-includes', re.I)}),
            ('meta', {'name': 'description', 'content': re.compile('WordPress', re.I)})
        ],
        'Shopify': [
            ('meta', {'content': re.compile('Shopify', re.I)}),
            ('link', {'href': re.compile('cdn.shopify.com', re.I)}),
            ('script', {'src': re.compile('shopify', re.I)}),
            ('div', {'class': re.compile('shopify', re.I)})
        ],
        'Wix': [
            ('meta', {'name': 'generator', 'content': re.compile('Wix.com', re.I)}),
            ('script', {'src': re.compile('static.wixstatic.com', re.I)}),
            ('img', {'src': re.compile('wixstatic.com', re.I)})
        ],
        'Drupal': [
            ('meta', {'name': 'generator', 'content': re.compile('Drupal', re.I)}),
            ('link', {'href': re.compile('sites/default/files', re.I)}),
            ('script', {'src': re.compile('sites/default/files', re.I)})
        ],
        'Joomla': [
            ('meta', {'name': 'generator', 'content': re.compile('Joomla', re.I)}),
            ('script', {'src': re.compile('/media/jui/', re.I)}),
            ('script', {'src': re.compile('/media/system/js/', re.I)})
        ],
        'Ghost': [
            ('meta', {'name': 'generator', 'content': re.compile('Ghost', re.I)}),
            ('link', {'href': re.compile('ghost.io', re.I)})
        ],
        'Webflow': [
            ('meta', {'name': 'generator', 'content': re.compile('Webflow', re.I)}),
            ('html', {'class': re.compile('w-mod-js', re.I)})
        ],
        'Squarespace': [
            ('meta', {'name': 'generator', 'content': re.compile('Squarespace', re.I)}),
            ('script', {'src': re.compile('static1.squarespace.com', re.I)}),
            ('img', {'src': re.compile('static1.squarespace.com', re.I)})
        ],
        'React': [
            ('div', {'id': 'root'}),
            ('div', {'id': 'app'}),
            ('script', {'src': re.compile('react', re.I)})
        ],
        'Angular': [
            ('script', {'src': re.compile('angular', re.I)}),
            ('app-root', {}),
            ('ng-version', {})
        ],
        'Vue.js': [
            ('div', {'id': 'app'}),
            ('script', {'src': re.compile('vue', re.I)}),
            ('div', {'data-v-': re.compile(r'.*')})
        ]
    }

def analyze_headers(headers):
    """Analyze response headers for platform hints."""
    header_scores = {}
    
    # Convert headers to lowercase for case-insensitive matching
    headers = {k.lower(): v.lower() for k, v in headers.items()}
    
    # Server software
    if 'server' in headers:
        server = headers['server']
        if 'apache' in server:
            header_scores['Apache'] = 100
        if 'nginx' in server:
            header_scores['Nginx'] = 100
        if 'microsoft-iis' in server:
            header_scores['IIS'] = 100
            
    # Technology indicators
    if 'x-powered-by' in headers:
        powered_by = headers['x-powered-by']
        if 'php' in powered_by:
            header_scores['PHP'] = 100
        if 'asp.net' in powered_by:
            header_scores['ASP.NET'] = 100
        if 'nodejs' in powered_by:
            header_scores['Node.js'] = 100
            
    # Platform-specific headers
    if any('x-shopify' in key for key in headers.keys()):
        header_scores['Shopify'] = 100
    if any('x-drupal' in key for key in headers.keys()):
        header_scores['Drupal'] = 100
    if any('x-wordpress' in key for key in headers.keys()):
        header_scores['WordPress'] = 100
        
    return header_scores

def get_confidence_score(matches, total_checks, header_matches=0):
    """Calculate confidence score with header information."""
    base_score = (matches / total_checks) * 100
    header_bonus = min(20, header_matches * 10)  # Cap header bonus at 20%
    return min(100, base_score + header_bonus)

def detect_platform(url):
    """Detect the platform/framework used by a website."""
    try:
        response = fetch_website(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        header_scores = analyze_headers(response.headers)
        detected_platforms = []
        
        signatures = get_platform_signatures()
        for platform, checks in signatures.items():
            matches = 0
            total_checks = len(checks)
            
            for tag, attrs in checks:
                elements = soup.find_all(tag, attrs)
                if elements:
                    matches += 1
                    if len(elements) > 1:
                        matches += 0.5
            
            if matches > 0:
                header_bonus = 1 if platform.lower() in str(header_scores).lower() else 0
                confidence = get_confidence_score(matches, total_checks, header_bonus)
                
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
        
        detected_platforms.sort(key=lambda x: x['confidence'], reverse=True)
        
        return detected_platforms if detected_platforms else [{
            'platform': 'No platform detected',
            'confidence': 0,
            'reliability': 'none'
        }]
        
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error for URL: {url}")
        return [{'platform': 'Could not connect to website. Please check the URL and try again.', 'confidence': 0, 'reliability': 'error'}]
    except requests.exceptions.Timeout:
        logger.error(f"Timeout error for URL: {url}")
        return [{'platform': 'Request timed out. The website took too long to respond.', 'confidence': 0, 'reliability': 'error'}]
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for URL {url}: {str(e)}")
        return [{'platform': f'An error occurred while analyzing the website: {str(e)}', 'confidence': 0, 'reliability': 'error'}]

# Streamlit UI
st.set_page_config(page_title='Website Platform Detector', layout='wide')

st.title('Website Platform Detector')
st.write('Enter a website URL to detect its platform.')

url = st.text_input('Website URL', placeholder='example.com')

if url:
    cleaned_url = clean_url(url)
    
    if cleaned_url:
        with st.spinner('Analyzing...'):
            try:
                platforms = detect_platform(cleaned_url)
                
                for platform in platforms:
                    if platform['reliability'] == 'error':
                        st.error(platform['platform'])
                    elif platform['platform'] != 'No platform detected':
                        if platform['reliability'] == 'high':
                            st.success(f"{platform['platform']}: {platform['confidence']}%")
                        elif platform['reliability'] == 'medium':
                            st.info(f"{platform['platform']}: {platform['confidence']}%")
                        else:
                            st.warning(f"{platform['platform']}: {platform['confidence']}%")
                    else:
                        st.warning('No platforms detected with confidence')
                        
            except Exception as e:
                logger.exception("Unexpected error")
                st.error(f'An unexpected error occurred: {str(e)}')
    else:
        st.error('Please enter a valid URL')
