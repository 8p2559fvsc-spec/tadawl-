import json

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ماسح تداول", layout="wide")
st.title("📈 ماسح الأسهم السعودية")

with open("results.json", encoding="utf-8") as f:
    data = json.load(f)

st.caption(f"آخر تحديث: {data['updated']}")
st.warning(data["disclaimer"])

df = pd.DataFrame(data["results"])
df = df.rename(columns={
    "name": "السهم", "ticker": "الرمز", "price": "السعر",
    "rsi": "RSI", "score": "الدرجة",
})
cols = ["السهم", "الرمز", "السعر", "RSI", "الدرجة"]

st.subheader("إشارات إيجابية (درجة 4 فأكثر)")
top = df[df["الدرجة"] >= 4]
if top.empty:
    st.info("ما فيه أسهم وصلت درجة 4 حاليا")
else:
    st.dataframe(top[cols], hide_index=True, use_container_width=True)

st.subheader("كل الأسهم")
st.dataframe(df[cols], hide_index=True, use_container_width=True)
