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

def get_custom_site_indicators(soup, headers):
    """Analyze if the site might be custom built."""
    indicators = []
    
    # Check for absence of common CMS/platform signatures
    common_platforms = ['wordpress', 'shopify', 'wix', 'squarespace', 'webflow']
    page_source = str(soup).lower()
    if not any(platform in page_source for platform in common_platforms):
        indicators.append('No common platform signatures detected')
    
    # Check for custom bundled JavaScript
    js_files = soup.find_all('script', src=True)
    js_paths = [script['src'] for script in js_files if script.get('src')]
    if any('bundle' in js.lower() or 'vendor' in js.lower() or 'main' in js.lower() for js in js_paths):
        indicators.append('Custom bundled JavaScript detected')
    
    # Check for unique build tools/bundlers
    build_tools = ['webpack', 'parcel', 'rollup', 'vite']
    if any(tool in str(soup).lower() for tool in build_tools):
        indicators.append('Build tool signatures found')
    
    # Check for custom asset structure
    asset_patterns = ['/assets/', '/static/', '/dist/', '/build/']
    if any(pattern in str(soup) for pattern in asset_patterns):
        indicators.append('Custom asset structure detected')
    
    return indicators

def get_platform_signatures():
    """Return dictionary of platform signatures to look for."""
    return {
        'WordPress': [
            ('meta', {'name': 'generator', 'content': re.compile('WordPress', re.I)}),
            ('link', {'rel': 'pingback'}),
            ('script', {'src': re.compile('wp-includes|wp-content', re.I)}),
            ('link', {'href': re.compile('/wp-content/', re.I)}),
        ],
        'Magento': [
            ('script', {'src': re.compile('mage', re.I)}),
            ('script', {'type': 'text/x-magento-init'}),
            ('link', {'href': re.compile('frontend/Magento/', re.I)}),
        ],
        'OpenCart': [
            ('script', {'src': re.compile('catalog/view/javascript', re.I)}),
            ('link', {'href': re.compile('catalog/view/theme', re.I)}),
        ],
        'PrestaShop': [
            ('meta', {'name': 'generator', 'content': re.compile('PrestaShop', re.I)}),
            ('script', {'src': re.compile('prestashop', re.I)}),
            ('link', {'href': re.compile('themes/[^/]+/assets', re.I)}),
        ],
        'BigCommerce': [
            ('script', {'src': re.compile('bigcommerce.com', re.I)}),
            ('link', {'href': re.compile('cdn11.bigcommerce.com', re.I)}),
        ],
        'WooCommerce': [
            ('link', {'href': re.compile('wp-content/plugins/woocommerce', re.I)}),
            ('script', {'src': re.compile('woocommerce', re.I)}),
            ('div', {'class': re.compile('woocommerce', re.I)}),
        ],
        'Craft CMS': [
            ('meta', {'name': 'generator', 'content': re.compile('Craft CMS', re.I)}),
            ('script', {'src': re.compile('craftcms', re.I)}),
        ],
        'ExpressionEngine': [
            ('meta', {'name': 'generator', 'content': re.compile('ExpressionEngine', re.I)}),
            ('script', {'src': re.compile('expressionengine', re.I)}),
        ],
        'Umbraco': [
            ('meta', {'name': 'generator', 'content': re.compile('umbraco', re.I)}),
            ('script', {'src': re.compile('umbraco', re.I)}),
        ],
        'Kentico': [
            ('meta', {'name': 'generator', 'content': re.compile('Kentico', re.I)}),
            ('link', {'href': re.compile('kentico', re.I)}),
        ],
        'Sitecore': [
            ('meta', {'name': 'generator', 'content': re.compile('Sitecore', re.I)}),
            ('script', {'src': re.compile('sitecore', re.I)}),
        ],
        'Adobe Experience Manager': [
            ('meta', {'name': 'generator', 'content': re.compile('Adobe Experience Manager', re.I)}),
            ('div', {'class': re.compile('aem-Grid', re.I)}),
        ],
        'HubSpot CMS': [
            ('meta', {'name': 'generator', 'content': re.compile('HubSpot', re.I)}),
            ('script', {'src': re.compile('hubspot', re.I)}),
        ],
        'Scorpion CMS': [
            ('meta', {'name': 'author', 'content': re.compile('Scorpion', re.I)}),
            ('script', {'src': re.compile('scorpion', re.I)}),
            ('link', {'href': re.compile('scorpion', re.I)}),
            ('script', {'src': re.compile('\.scorp\.com', re.I)}),
            ('div', {'class': re.compile('scorpion-', re.I)}),
            ('img', {'src': re.compile('\.scorp\.com', re.I)}),
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
        'Next.js': [
            ('meta', {'name': 'next-head-count'}),
            ('script', {'src': re.compile('/_next/', re.I)}),
        ],
        'React': [
            ('script', {'src': re.compile('react', re.I)}),
            ('div', {'id': 'root'}),
        ],
        'Angular': [
            ('script', {'src': re.compile('angular', re.I)}),
            ('app-root', {}),
        ],
        'Vue.js': [
            ('script', {'src': re.compile('vue', re.I)}),
            ('div', {'id': 'app'}),
        ]
    }

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
            for tag, attrs in checks:
                if soup.find(tag, attrs):
                    if platform not in detected_platforms:
                        detected_platforms.append(platform)
                        break
        
        # Check for custom-built indicators if no major platforms detected
        if not detected_platforms or (len(detected_platforms) == 1 and detected_platforms[0] in ['PHP', 'Apache', 'Nginx']):
            custom_indicators = get_custom_site_indicators(soup, response.headers)
            if custom_indicators:
                detected_platforms.append('Likely Custom Built:')
                detected_platforms.extend([f'  • {indicator}' for indicator in custom_indicators])
        
        # Additional header-based checks
        if 'php' in poweredBy:
            detected_platforms.append('PHP')
        if 'apache' in server:
            detected_platforms.append('Apache')
        if 'nginx' in server:
            detected_platforms.append('Nginx')
        
        return detected_platforms if detected_platforms else ['Unable to determine platform']
    
    except requests.exceptions.RequestException as e:
        return [f'Error: {str(e)}']

# Streamlit UI
st.set_page_config(page_title='Website Platform Detector', layout='wide')

st.title('Website Platform Detector')
st.write('Enter a website URL to detect what platform or framework it\'s built with.')

# URL input
url = st.text_input('Website URL', placeholder='example.com')

if url:
    # Clean and validate URL
    cleaned_url = clean_url(url)
    
    if cleaned_url:
        st.write(f'Analyzing: {cleaned_url}')
        
        # Show spinner during detection
        with st.spinner('Detecting platform...'):
            platforms = detect_platform(cleaned_url)
        
        # Display results
        st.subheader('Detected Platforms/Technologies:')
        for platform in platforms:
            st.write(f'- {platform}')
            
        st.info('Note: Detection is based on common signatures and may not be 100% accurate.')
    else:
        st.error('Please enter a valid URL')

# Add footer with information
st.markdown('---')
st.markdown("""
This tool attempts to identify web platforms and frameworks by analyzing HTML structure, 
meta tags, scripts, and server headers. It can detect common platforms like WordPress, 
Shopify, Wix, and various frameworks like React, Angular, and Vue.js.
""")
