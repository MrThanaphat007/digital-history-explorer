"""Historical data analysis with Pandas + Plotly."""
import pandas as pd
import plotly.express as px
import streamlit as st
from db import query
from utils import fmt_year, year_ticks, style_fig, era_of, ERAS


def render(year: int, dark: bool):
    st.markdown("<div class='hero'><h1>Historical Data Analysis</h1></div>", unsafe_allow_html=True)
    st.caption("Sample datasets only. Read each series' source and note before drawing conclusions.")
    t1, t2, t3 = st.tabs(["Trends & comparison", "Migration flows", "Events analysis"])

    with t1:
        pop = query("SELECT * FROM population")
        metric = st.selectbox("Dataset / metric", sorted(pop["metric"].unique()))
        df = pop[pop["metric"] == metric]
        ents = st.multiselect("Compare", sorted(df["entity"].unique()), default=sorted(df["entity"].unique()))
        df = df[df["entity"].isin(ents)]
        if df.empty:
            st.info("Select at least one series.")
        else:
            log = st.checkbox("Logarithmic y-axis")
            fig = px.line(df, x="year", y="value", color="entity", markers=True,
                          hover_data={"source": True, "year": False}, labels={"value": df["unit"].iloc[0]})
            tv, tt = year_ticks(df["year"])
            fig.update_xaxes(tickvals=tv, ticktext=tt, title="")
            if log:
                fig.update_yaxes(type="log")
            st.plotly_chart(style_fig(fig, dark), width="stretch")

            # Compare two years for each series that has data at both points (Pandas pivot)
            yrs = sorted(df["year"].unique())
            if len(yrs) >= 2:
                a, b = st.select_slider("Compare change between", yrs, value=(yrs[0], yrs[-1]), format_func=fmt_year)
                wide = df.pivot_table(index="entity", columns="year", values="value")
                if a in wide and b in wide:
                    ch = wide[[a, b]].dropna()
                    if not ch.empty:
                        ch["Change %"] = ((ch[b] / ch[a] - 1) * 100).round(1)
                        ch.columns = [fmt_year(a), fmt_year(b), "Change %"]
                        st.dataframe(ch, width="stretch")
                    else:
                        st.info("No selected series has data at both years.")
            with st.expander("Sources and caveats"):
                st.dataframe(df[["entity", "year", "value", "unit", "source", "note"]].drop_duplicates(),
                             hide_index=True, width="stretch")

    with t2:
        fl = query("SELECT * FROM flows")
        fig = px.bar(fl, x="flow", y="value", color="flow", labels={"value": "million people", "flow": ""},
                     hover_data=["start_year", "end_year", "source"])
        st.plotly_chart(style_fig(fig, dark, 360), width="stretch")
        st.dataframe(fl[["flow", "start_year", "end_year", "value", "unit", "source", "note"]],
                     hide_index=True, width="stretch")
        st.caption("To extend: add rows to data/flows.csv (trade volumes, other migrations) with a source.")

    with t3:
        ev = query("SELECT * FROM events")
        ev["era"] = ev["year"].map(era_of)
        ev["century"] = ev["year"].map(lambda y: (y // 100) * 100)
        by = ev.groupby(["era", "category"]).size().reset_index(name="events")
        fig = px.bar(by, x="era", y="events", color="category", category_orders={"era": ERAS})
        fig.update_xaxes(title="")
        st.plotly_chart(style_fig(fig, dark, 360), width="stretch")
        st.caption("This shows what the sample dataset contains, not how eventful each era was.")
