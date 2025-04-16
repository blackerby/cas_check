from datetime import date, timedelta
import os

import httpx
import polars as pl
import streamlit as st

GPO_API_PACKAGES_URL = "https://api.govinfo.gov/packages"
CDG_API_BILL_URL = "https://api.congress.gov/v3/bill"
CDG_BILL_URL = "https://www.congress.gov/bill"

PAGE_SIZE = 1000
OFFSET_MARK = "*"
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
CURRENT_CONGRESS = (date.today().year - 1789) // 2 + 1


API_KEY = os.environ.get("GPO_API_KEY", "DEMO_KEY")
HEADERS = {"X-Api-Key": API_KEY}
TITLE = "Constitutional Authority Statement Check"

st.set_page_config(page_title=TITLE, layout="wide")

# Report starts here
st.title(TITLE)

crec_date = st.date_input("Congressional Record date", YESTERDAY, format="YYYY-MM-DD")
package_id = f"CREC-{crec_date}"
granules_url = f"{GPO_API_PACKAGES_URL}/{package_id}/granules?pageSize={PAGE_SIZE}&offsetMark={OFFSET_MARK}"

response = httpx.get(granules_url, headers=HEADERS)
gpo_data = response.json()
granules = gpo_data["granules"]

if not granules:
    st.header("No CREC today")
else:
    bills = [
        # granule["title"].partition("for ")[2].replace(".", "").split()
        granule
        for granule in response.json()["granules"]
        if granule["title"].startswith("Constitutional Authority Statement for ")
    ]

    for bill in bills:
        bill_type, bill_num = (
            bill["title"].partition("for ")[2].replace(".", "").split()
        )
        bill["cdg_api_url"] = (
            f"{CDG_API_BILL_URL}/{CURRENT_CONGRESS}/{bill_type}/{bill_num}?format=json"
        )
        bill["cdg_url"] = f"{CDG_BILL_URL}/{CURRENT_CONGRESS}/{bill_type}/{bill_num}"
        response = httpx.get(
            bill["cdg_api_url"],
            headers=HEADERS,
        )
        bill_obj = response.json().get("bill")
        bill["cas"] = bill_obj.get("constitutionalAuthorityStatementText")

        df = (
            pl.from_dicts(bills)
            .select(
                pl.col("title"),
                pl.col("granuleId"),
                pl.concat_str(pl.col("granuleLink"), pl.lit("?api_key=DEMO_KEY")),
                pl.concat_str(pl.col("cdg_api_url"), pl.lit("&api_key=DEMO_KEY")),
                pl.col("cdg_url"),
                pl.col("cas"),
            )
            .sort("title")
        )

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "granuleLink": st.column_config.LinkColumn(),
            "cdg_api_url": st.column_config.LinkColumn(),
            "cdg_url": st.column_config.LinkColumn(),
        },
    )
