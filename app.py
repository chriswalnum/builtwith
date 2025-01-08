import streamlit as st
# Just test without BeautifulSoup for now
import requests

st.title('Website Platform Detector - Test')
st.write('Simple test version to verify deployment')

url = st.text_input('Enter a URL to test')

if url:
    st.write(f'You entered: {url}')
    st.write('Basic test successful!')
