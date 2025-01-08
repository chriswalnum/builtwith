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
        'Weebly': [
            ('meta', {'name': 'generator', 'content': re.compile('Weebly', re.I)}),
            ('script', {'src': re.compile('weebly', re.I)}),
            ('div', {'class': re.compile('weebly-', re.I)}),
        ],
        'Duda': [
            ('script', {'src': re.compile('multiscreensite', re.I)}),
            ('script', {'src': re.compile('duda', re.I)}),
            ('meta', {'name': 'generator', 'content': re.compile('Duda', re.I)}),
        ],
        'Webflow': [
            ('html', {'data-wf-site': re.compile('.*')}),
            ('script', {'src': re.compile('webflow.com', re.I)}),
            ('meta', {'generator': 'Webflow'}),
        ],
        'Contentful': [
            ('meta', {'name': 'generator', 'content': re.compile('contentful', re.I)}),
            ('script', {'src': re.compile('contentful', re.I)}),
        ],
        'Sitefinity': [
            ('meta', {'generator': re.compile('Sitefinity', re.I)}),
            ('link', {'href': re.compile('Sitefinity', re.I)}),
        ],
        'Concrete CMS': [
            ('meta', {'name': 'generator', 'content': re.compile('concrete5|concrete cms', re.I)}),
            ('script', {'src': re.compile('concrete', re.I)}),
        ],
        'GoDaddy Website Builder': [
            ('meta', {'generator': re.compile('GoDaddy', re.I)}),
            ('script', {'src': re.compile('websitebuilder.godaddy.com', re.I)}),
            ('img', {'src': re.compile('godaddy-website-builder', re.I)}),
        ],
        'Strikingly': [
            ('meta', {'name': 'generator', 'content': re.compile('Strikingly', re.I)}),
            ('script', {'src': re.compile('strikingly', re.I)}),
        ],
        'Jimdo': [
            ('meta', {'name': 'generator', 'content': re.compile('Jimdo', re.I)}),
            ('script', {'src': re.compile('jimdo', re.I)}),
        ],
        'Contao': [
            ('meta', {'name': 'generator', 'content': re.compile('Contao', re.I)}),
            ('script', {'src': re.compile('contao', re.I)}),
        ],
        'Acquia': [
            ('script', {'src': re.compile('acquia', re.I)}),
            ('meta', {'name': 'generator', 'content': re.compile('Acquia', re.I)}),
        ],
        'CloudCannon': [
            ('meta', {'generator': re.compile('CloudCannon', re.I)}),
            ('script', {'src': re.compile('cloudcannon', re.I)}),
        ],
        'MODX': [
            ('meta', {'name': 'generator', 'content': re.compile('MODX', re.I)}),
            ('script', {'src': re.compile('modx', re.I)}),
        ],
        'Brightspot': [
            ('meta', {'name': 'generator', 'content': re.compile('Brightspot', re.I)}),
            ('script', {'src': re.compile('brightspot', re.I)}),
        ],
        'Contentstack': [
            ('meta', {'name': 'generator', 'content': re.compile('Contentstack', re.I)}),
            ('script', {'src': re.compile('contentstack', re.I)}),
        ],
        'Salesforce Experience Cloud': [
            ('meta', {'name': 'generator', 'content': re.compile('Salesforce', re.I)}),
            ('script', {'src': re.compile('force.com|salesforce.com', re.I)}),
            ('div', {'class': re.compile('salesforce-', re.I)}),
        ],
        'Netlify CMS': [
            ('meta', {'name': 'generator', 'content': re.compile('Netlify', re.I)}),
            ('script', {'src': re.compile('netlify-cms', re.I)}),
            ('div', {'class': re.compile('nc-')}),
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

def get_confidence_score(matches, total_checks):
    """Calculate confidence score based on number of matching signatures."""
    if total_checks == 0:
        return 0
    return (matches / total_checks) * 100

def detect_platform(url):
    """Detect the platform/framework used by a website with confidence scores."""
    try:
        # Send request with common browser headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check response headers and cookies for platform hints
        server = response.headers.get('Server', '').lower()
        poweredBy = response.headers.get('X-Powered-By', '').lower()
        cookies = response.cookies
        
        # Initialize results with confidence scores
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
                if confidence >= 30:  # Only include if confidence is at least 30%
                    detected_platforms.append({
                        'platform': platform,
                        'confidence': round(confidence, 1),
                        'matches': matches,
                        'total_checks': total_checks
                    })
        
        # Sort by confidence score
        detected_platforms.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Additional technology checks
        if server:
            detected_platforms.append({
                'platform': f'Server: {server}',
                'confidence': 100,
                'matches': 1,
                'total_checks': 1
            })
        
        if poweredBy:
            detected_platforms.append({
                'platform': f'Powered By: {poweredBy}',
                'confidence': 100,
                'matches': 1,
                'total_checks': 1
            })
            
        return detected_platforms if detected_platforms else [{
            'platform': 'Unable to determine platform',
            'confidence': 0,
            'matches': 0,
            'total_checks': 1
        }]
    
    except requests.exceptions.RequestException as e:
        return [{
            'platform': f'Error: {str(e)}',
            'confidence': 0,
            'matches': 0,
            'total_checks': 1
        }]
        
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


# Add footer with information
st.markdown('---')
st.markdown("""
This tool attempts to identify web platforms and frameworks by analyzing HTML structure, 
meta tags, scripts, and server headers. It can detect common platforms like WordPress, 
Shopify, Wix, and various frameworks like React, Angular, and Vue.js.
""")
