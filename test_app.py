import streamlit as st

st.title("Dependency Test App")

# Test basic imports
st.write("Testing imports...")

try:
    import sys
    st.success(f"✓ Python {sys.version}")
except Exception as e:
    st.error(f"✗ sys import failed: {e}")

try:
    import google.generativeai
    st.success("✓ google.generativeai imported successfully")
except Exception as e:
    st.error(f"✗ google.generativeai import failed: {e}")
    
try:
    import pandas
    st.success("✓ pandas imported successfully")
except Exception as e:
    st.error(f"✗ pandas import failed: {e}")

try:
    import requests
    st.success("✓ requests imported successfully")
except Exception as e:
    st.error(f"✗ requests import failed: {e}")

st.write("---")
st.write("If google.generativeai fails, try running:")
st.code("pip install google-generativeai")