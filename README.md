# CookView Streamlit

Streamlit website version of your recipe extractor.

## Local run

```bash
cd cookview_streamlit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open the local URL shown by Streamlit (usually `http://localhost:8501`).

## Deploy with GitHub + Streamlit Community Cloud

1. Create a GitHub repo and push the `cookview_streamlit` folder.
2. Go to Streamlit Community Cloud and click **New app**.
3. Select your repo and set:
   - Main file path: `streamlit_app.py` (or `cookview_streamlit/streamlit_app.py` if repo root differs)
4. Deploy.

You get a public HTTPS URL you can open from anywhere.

## Notes
- This still uses Python backend logic server-side, which is why it can fetch recipe URLs.
- Some sites may block scraping requests.
# cookview
# cookview
# cookview
