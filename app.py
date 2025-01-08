import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

def clean_url(url):
    """Normalize URL format."""
    if not url:
        return None
    
    # Add https if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slashes
    url = url.rstrip('/')
    
    return url

def get_platform_signatures():
    """Return dictionary of platform signatures to look for."""
    return {
        'WordPress': [
            ('meta', {'name': 'generator', 'content': re.compile('WordPress', re.I)}),
            ('link', {'rel': 'pingback'}),
            ('script', {'src': re.compile('wp-includes|wp-content', re.I)}),
        ],
        'Shopify': [
            ('meta', {'name': 'shopify-checkout-api-token'}),
            ('script', {'src': re.compile('shopify', re.I)}),
            ('link', {'href': re.compile('shopify', re.I)}),
        ],
        'Wix': [
            ('meta', {'name': 'generator', 'content': re.compile('Wix.com', re.I)}),
            ('script', {'src': re.compile('static.wixstatic.com', re.I)}),
        ],
        'Squarespace': [
            ('meta', {'generator': re.compile('Squarespace', re.I)}),
            ('script', {'src': re.compile('squarespace', re.I)}),
        ],
        'Webflow': [
            ('meta', {'generator': 'Webflow'}),
            ('html', {'data-wf-site': re.compile('.*')}),
        ],
        'Drupal': [
            ('meta', {'name': 'generator', 'content': re.compile('Drupal', re.I)}),
            ('script', {'src': re.compile('drupal.js', re.I)}),
        ],
        'Joomla': [
            ('meta', {'name': 'generator', 'content': re.compile('Joomla!', re.I)}),
            ('script', {'src': re.compile('joomla', re.I)}),
        ],
        'Ghost': [
            ('meta', {'name': 'generator', 'content': re.compile('Ghost', re.I)}),
            ('link', {'href': re.compile('ghost', re.I)}),
        ],
        'Magento': [
            ('script', {'src': re.compile('mage', re.I)}),
            ('script', {'type': 'text/x-magento-init'}),
        ],
        'Scorpion CMS': [
            ('meta', {'name': 'author', 'content': re.compile('Scorpion', re.I)}),
            ('script', {'src': re.compile('scorpion', re.I)}),
            ('link', {'href': re.compile('scorpion', re.I)}),
            ('script', {'src': re.compile('\.scorp\.com', re.I)}),
            ('div', {'class': re.compile('scorpion-', re.I)}),
        ]
    }

def get_confidence_score(matches, total_checks):
    """Calculate confidence score based on number of matching signatures."""
    if total_checks == 0:
        return 0
    return (matches / total_checks) * 100

def detect_platform(url):
    """Detect the platform/framework used by a website."""
    try:
        # Send request with common browser headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check response headers for platform hints
        server = response.headers.get('Server', '').lower()
        poweredBy = response.headers.get('X-Powered-By', '').lower()
        
        # Initialize results
        detected_platforms = []
        
        # Check signatures for each platform
        signatures = get_platform_signatures()
        for platform, checks in signatures.items():
            matches = 0
            total_checks = len(checks)
            
            for tag, attrs in checks:
                if soup.find(tag, attrs):
                    matches += 1
            
            # Calculate confidence score
            if matches > 0:
                confidence = get_confidence_score(matches, total_checks)
                if confidence >= 30:
                    detected_platforms.append({
                        'platform': platform,
                        'confidence': round(confidence, 1)
                    })
        
        # Sort by confidence score
        detected_platforms.sort(key=lambda x: x['confidence'], reverse=True)
        
        return detected_platforms if detected_platforms else [{
            'platform': 'Unable to determine platform',
            'confidence': 0
        }]
    
    except requests.exceptions.RequestException as e:
        return [{'platform': f'Error: {str(e)}', 'confidence': 0}]

# Streamlit UI
st.set_page_config(page_title='Website Platform Detector', layout='wide')

st.title('Website Platform Detector')
st.write('Enter a website URL to detect its platform.')

# URL input
url = st.text_input('Website URL', placeholder='example.com')

if url:
    # Clean and validate URL
    cleaned_url = clean_url(url)
    
    if cleaned_url:
        # Show spinner during detection
        with st.spinner('Analyzing...'):
            platforms = detect_platform(cleaned_url)
        
        # Display only platforms with their confidence
        for platform in platforms:
            if isinstance(platform, dict) and 'platform' in platform:
                # Skip server and powered-by information
                if not platform['platform'].startswith(('Server:', 'Powered By:', 'Error:', 'Unable')):
                    st.write(f"{platform['platform']}: {platform['confidence']}%")
    else:
        st.error('Please enter a valid URL')
