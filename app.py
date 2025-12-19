"""
GSE Market Intelligence Terminal
A Streamlit dashboard for Ghana Stock Exchange market data
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import glob

# =============================================================================
# CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="GSE Market Watch",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

SEEDS_FOLDER = "seeds"
MASTER_FILE = "gse_master_data.csv"

# Column mappings from raw CSV
COL_MAP = {
    "Daily Date": "date",
    "Share Code": "symbol",
    "Year High (GH¢)": "year_high",
    "Year Low (GH¢)": "year_low",
    "Previous Closing Price - VWAP (GH¢)": "prev_close",
    "Opening Price (GH¢)": "open",
    "Closing Price - VWAP (GH¢)": "close",
    "Price Change (GH¢)": "change",
    "Closing Bid Price (GH¢)": "bid",
    "Closing Offer Price (GH¢)": "ask",
    "Total Shares Traded": "volume",
    "Total Value Traded (GH¢)": "turnover"
}

# =============================================================================
# DATA LOADING & PROCESSING
# =============================================================================
@st.cache_data(ttl=3600)
def load_all_data():
    """Load and consolidate all CSV files from seeds folder"""
    all_dfs = []
    
    # Check if seeds folder exists
    if not os.path.exists(SEEDS_FOLDER):
        st.warning(f"Seeds folder '{SEEDS_FOLDER}' not found. Please create it and add your CSV files.")
        return pd.DataFrame()
    
    csv_files = glob.glob(os.path.join(SEEDS_FOLDER, "*.csv"))
    
    if not csv_files:
        st.warning(f"No CSV files found in '{SEEDS_FOLDER}' folder.")
        return pd.DataFrame()
    
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            # Rename columns to standardized names
            df = df.rename(columns=COL_MAP)
            all_dfs.append(df)
        except Exception as e:
            st.warning(f"Error loading {file}: {e}")
            continue
    
    if not all_dfs:
        return pd.DataFrame()
    
    # Combine all dataframes
    combined = pd.concat(all_dfs, ignore_index=True)
    
    # Clean and process data
    combined = clean_data(combined)
    
    return combined


def clean_data(df):
    """Clean and validate the data"""
    if df.empty:
        return df
    
    # Parse dates
    df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
    
    # Remove rows with invalid dates
    df = df.dropna(subset=['date'])
    
    # Clean numeric columns - remove commas and convert
    numeric_cols = ['year_high', 'year_low', 'prev_close', 'open', 'close', 
                    'change', 'bid', 'ask', 'volume', 'turnover']
    
    for col in numeric_cols:
        if col in df.columns:
            # Convert to string, remove commas, then to numeric
            df[col] = df[col].astype(str).str.replace(',', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Filter out obviously bad rows (e.g., year_high > 100 for most stocks is suspicious)
    # Keep rows where close price is reasonable (between 0.01 and 1000)
    df = df[(df['close'] > 0.01) & (df['close'] < 1000)]
    
    # Sort by symbol and date
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Remove duplicates (same symbol and date)
    df = df.drop_duplicates(subset=['symbol', 'date'], keep='last')
    
    return df


def calculate_metrics(df, symbol):
    """Calculate Yahoo Finance-style metrics for a stock"""
    stock_df = df[df['symbol'] == symbol].copy()
    
    if stock_df.empty:
        return {}
    
    stock_df = stock_df.sort_values('date')
    latest = stock_df.iloc[-1]
    
    # Basic price info
    current_price = latest['close']
    prev_close = latest['prev_close'] if pd.notna(latest['prev_close']) else current_price
    daily_change = latest['change'] if pd.notna(latest['change']) else 0
    daily_change_pct = (daily_change / prev_close * 100) if prev_close > 0 else 0
    
    # 52-week high/low (from data or calculated)
    year_high = latest['year_high'] if pd.notna(latest['year_high']) else stock_df['close'].max()
    year_low = latest['year_low'] if pd.notna(latest['year_low']) else stock_df['close'].min()
    
    # Volume metrics
    current_volume = latest['volume'] if pd.notna(latest['volume']) else 0
    avg_volume_10d = stock_df.tail(10)['volume'].mean() if len(stock_df) >= 10 else stock_df['volume'].mean()
    avg_volume_30d = stock_df.tail(30)['volume'].mean() if len(stock_df) >= 30 else stock_df['volume'].mean()
    
    # Bid/Ask
    bid = latest['bid'] if pd.notna(latest['bid']) and latest['bid'] > 0 else None
    ask = latest['ask'] if pd.notna(latest['ask']) and latest['ask'] > 0 else None
    spread = (ask - bid) if (bid and ask) else None
    spread_pct = (spread / current_price * 100) if spread else None
    
    # Moving averages
    ma_20 = stock_df.tail(20)['close'].mean() if len(stock_df) >= 20 else None
    ma_50 = stock_df.tail(50)['close'].mean() if len(stock_df) >= 50 else None
    ma_200 = stock_df.tail(200)['close'].mean() if len(stock_df) >= 200 else None
    
    # Returns
    returns = stock_df['close'].pct_change()
    
    # Volatility (annualized)
    volatility = returns.tail(30).std() * np.sqrt(252) * 100 if len(returns) >= 30 else None
    
    # Period returns
    def get_return(days):
        if len(stock_df) >= days:
            old_price = stock_df.iloc[-days]['close']
            return ((current_price - old_price) / old_price * 100) if old_price > 0 else None
        return None
    
    # YTD return
    current_year = datetime.now().year
    ytd_df = stock_df[stock_df['date'].dt.year == current_year]
    if len(ytd_df) > 1:
        first_price = ytd_df.iloc[0]['close']
        ytd_return = ((current_price - first_price) / first_price * 100) if first_price > 0 else None
    else:
        ytd_return = None
    
    return {
        'symbol': symbol,
        'current_price': current_price,
        'prev_close': prev_close,
        'daily_change': daily_change,
        'daily_change_pct': daily_change_pct,
        'open': latest['open'] if pd.notna(latest['open']) else current_price,
        'year_high': year_high,
        'year_low': year_low,
        'volume': current_volume,
        'avg_volume_10d': avg_volume_10d,
        'avg_volume_30d': avg_volume_30d,
        'turnover': latest['turnover'] if pd.notna(latest['turnover']) else 0,
        'bid': bid,
        'ask': ask,
        'spread': spread,
        'spread_pct': spread_pct,
        'ma_20': ma_20,
        'ma_50': ma_50,
        'ma_200': ma_200,
        'volatility': volatility,
        'return_1w': get_return(5),
        'return_1m': get_return(21),
        'return_3m': get_return(63),
        'return_6m': get_return(126),
        'return_1y': get_return(252),
        'return_ytd': ytd_return,
        'last_updated': latest['date'].strftime('%d %b %Y'),
        'data_points': len(stock_df)
    }


# =============================================================================
# UI COMPONENTS
# =============================================================================
def render_metric_card(label, value, delta=None, delta_color="normal", prefix="", suffix=""):
    """Render a metric in a styled card"""
    formatted_value = f"{prefix}{value:,.2f}{suffix}" if isinstance(value, (int, float)) else str(value)
    
    if delta is not None:
        delta_str = f"{delta:+.2f}%" if isinstance(delta, (int, float)) else str(delta)
        st.metric(label=label, value=formatted_value, delta=delta_str, delta_color=delta_color)
    else:
        st.metric(label=label, value=formatted_value)


def create_price_chart(df, symbol, show_volume=True, show_ma=True):
    """Create an interactive price chart with volume"""
    stock_df = df[df['symbol'] == symbol].copy()
    stock_df = stock_df.sort_values('date')
    
    if show_volume:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3]
        )
    else:
        fig = go.Figure()
    
    # Price line
    fig.add_trace(
        go.Scatter(
            x=stock_df['date'],
            y=stock_df['close'],
            mode='lines',
            name='Close Price',
            line=dict(color='#10B981', width=2),
            fill='tozeroy',
            fillcolor='rgba(16, 185, 129, 0.1)'
        ),
        row=1, col=1
    ) if show_volume else fig.add_trace(
        go.Scatter(
            x=stock_df['date'],
            y=stock_df['close'],
            mode='lines',
            name='Close Price',
            line=dict(color='#10B981', width=2),
            fill='tozeroy',
            fillcolor='rgba(16, 185, 129, 0.1)'
        )
    )
    
    # Moving averages
    if show_ma and len(stock_df) >= 20:
        stock_df['MA20'] = stock_df['close'].rolling(window=20).mean()
        fig.add_trace(
            go.Scatter(
                x=stock_df['date'],
                y=stock_df['MA20'],
                mode='lines',
                name='20-day MA',
                line=dict(color='#F59E0B', width=1, dash='dash')
            ),
            row=1, col=1
        ) if show_volume else fig.add_trace(
            go.Scatter(
                x=stock_df['date'],
                y=stock_df['MA20'],
                mode='lines',
                name='20-day MA',
                line=dict(color='#F59E0B', width=1, dash='dash')
            )
        )
    
    if show_ma and len(stock_df) >= 50:
        stock_df['MA50'] = stock_df['close'].rolling(window=50).mean()
        fig.add_trace(
            go.Scatter(
                x=stock_df['date'],
                y=stock_df['MA50'],
                mode='lines',
                name='50-day MA',
                line=dict(color='#EF4444', width=1, dash='dash')
            ),
            row=1, col=1
        ) if show_volume else fig.add_trace(
            go.Scatter(
                x=stock_df['date'],
                y=stock_df['MA50'],
                mode='lines',
                name='50-day MA',
                line=dict(color='#EF4444', width=1, dash='dash')
            )
        )
    
    # Volume bars
    if show_volume:
        colors = ['#10B981' if stock_df.iloc[i]['change'] >= 0 else '#EF4444' 
                  for i in range(len(stock_df))]
        fig.add_trace(
            go.Bar(
                x=stock_df['date'],
                y=stock_df['volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.7
            ),
            row=2, col=1
        )
    
    # Layout
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=30, b=0),
        height=500 if show_volume else 400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')
    
    if show_volume:
        fig.update_yaxes(title_text="Price (GH₵)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    else:
        fig.update_yaxes(title_text="Price (GH₵)")
    
    return fig


def get_market_summary(df):
    """Get market-wide summary statistics"""
    if df.empty:
        return {}
    
    latest_date = df['date'].max()
    latest_data = df[df['date'] == latest_date]
    
    gainers = latest_data[latest_data['change'] > 0].sort_values('change', ascending=False)
    losers = latest_data[latest_data['change'] < 0].sort_values('change')
    
    return {
        'total_stocks': df['symbol'].nunique(),
        'latest_date': latest_date.strftime('%d %b %Y'),
        'gainers': gainers.head(5)[['symbol', 'close', 'change']].to_dict('records'),
        'losers': losers.head(5)[['symbol', 'close', 'change']].to_dict('records'),
        'total_volume': latest_data['volume'].sum(),
        'total_turnover': latest_data['turnover'].sum()
    }


# =============================================================================
# MAIN APP
# =============================================================================
def main():
    # Custom CSS for dark theme
    st.markdown("""
    <style>
        .stApp {
            background-color: #0f172a;
        }
        .metric-card {
            background-color: #1e293b;
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid #334155;
        }
        .stock-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #f1f5f9;
        }
        .positive { color: #10B981; }
        .negative { color: #EF4444; }
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📈 GSE Market Watch")
        st.caption("Ghana Stock Exchange Market Intelligence Terminal")
    
    # Load data
    df = load_all_data()
    
    if df.empty:
        st.error("No data available. Please add CSV files to the 'seeds' folder.")
        st.info("""
        **Setup Instructions:**
        1. Create a folder called `seeds` in the same directory as this app
        2. Add your stock CSV files (e.g., ACCESS.csv, GCB.csv, etc.)
        3. Refresh this page
        """)
        return
    
    # Sidebar - Stock Selection
    st.sidebar.header("🔍 Stock Selection")
    
    symbols = sorted(df['symbol'].unique().tolist())
    
    # Search box
    search = st.sidebar.text_input("Search symbol...", "")
    if search:
        filtered_symbols = [s for s in symbols if search.upper() in s.upper()]
    else:
        filtered_symbols = symbols
    
    if not filtered_symbols:
        st.sidebar.warning("No stocks match your search")
        return
    
    selected_symbol = st.sidebar.selectbox(
        "Select Stock",
        filtered_symbols,
        index=0
    )
    
    # Chart options
    st.sidebar.header("📊 Chart Options")
    show_volume = st.sidebar.checkbox("Show Volume", value=True)
    show_ma = st.sidebar.checkbox("Show Moving Averages", value=True)
    
    # Time range filter
    time_range = st.sidebar.selectbox(
        "Time Range",
        ["1M", "3M", "6M", "1Y", "2Y", "5Y", "All"],
        index=3
    )
    
    # Filter data by time range
    stock_df = df[df['symbol'] == selected_symbol].copy()
    max_date = stock_df['date'].max()
    
    range_map = {
        "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "2Y": 730, "5Y": 1825
    }
    
    if time_range in range_map:
        min_date = max_date - timedelta(days=range_map[time_range])
        filtered_df = df[df['date'] >= min_date]
    else:
        filtered_df = df
    
    # Calculate metrics
    metrics = calculate_metrics(df, selected_symbol)
    
    # Main content
    st.markdown("---")
    
    # Stock header
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"### {selected_symbol}")
        change_color = "positive" if metrics['daily_change'] >= 0 else "negative"
        change_icon = "▲" if metrics['daily_change'] >= 0 else "▼"
        st.markdown(
            f"<span style='font-size: 2.5rem; font-weight: bold;'>GH₵ {metrics['current_price']:.2f}</span> "
            f"<span class='{change_color}'>{change_icon} {metrics['daily_change']:+.2f} ({metrics['daily_change_pct']:+.2f}%)</span>",
            unsafe_allow_html=True
        )
        st.caption(f"Last updated: {metrics['last_updated']} • {metrics['data_points']} data points")
    
    with col2:
        # Download button
        stock_data = df[df['symbol'] == selected_symbol][['date', 'symbol', 'open', 'close', 'change', 'volume', 'turnover']]
        csv = stock_data.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"{selected_symbol}_GSE_data.csv",
            mime="text/csv"
        )
    
    # Price chart
    st.plotly_chart(
        create_price_chart(filtered_df, selected_symbol, show_volume, show_ma),
        use_container_width=True
    )
    
    # Metrics grid
    st.markdown("### 📊 Key Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Previous Close", f"GH₵ {metrics['prev_close']:.2f}")
        st.metric("Open", f"GH₵ {metrics['open']:.2f}")
        if metrics['bid']:
            st.metric("Bid", f"GH₵ {metrics['bid']:.2f}")
    
    with col2:
        st.metric("52-Week High", f"GH₵ {metrics['year_high']:.2f}")
        st.metric("52-Week Low", f"GH₵ {metrics['year_low']:.2f}")
        if metrics['ask']:
            st.metric("Ask", f"GH₵ {metrics['ask']:.2f}")
    
    with col3:
        st.metric("Volume", f"{metrics['volume']:,.0f}")
        st.metric("Avg Vol (10d)", f"{metrics['avg_volume_10d']:,.0f}")
        st.metric("Avg Vol (30d)", f"{metrics['avg_volume_30d']:,.0f}")
    
    with col4:
        if metrics['ma_20']:
            st.metric("20-Day MA", f"GH₵ {metrics['ma_20']:.2f}")
        if metrics['ma_50']:
            st.metric("50-Day MA", f"GH₵ {metrics['ma_50']:.2f}")
        if metrics['volatility']:
            st.metric("Volatility (30d)", f"{metrics['volatility']:.1f}%")
    
    # Performance table
    st.markdown("### 📈 Performance")
    
    perf_cols = st.columns(6)
    periods = [
        ("1 Week", metrics['return_1w']),
        ("1 Month", metrics['return_1m']),
        ("3 Months", metrics['return_3m']),
        ("6 Months", metrics['return_6m']),
        ("1 Year", metrics['return_1y']),
        ("YTD", metrics['return_ytd'])
    ]
    
    for col, (label, value) in zip(perf_cols, periods):
        with col:
            if value is not None:
                color = "normal" if value >= 0 else "inverse"
                st.metric(label, f"{value:+.2f}%", delta_color=color)
            else:
                st.metric(label, "N/A")
    
    # Market overview (sidebar bottom)
    st.sidebar.markdown("---")
    st.sidebar.header("📊 Market Overview")
    
    summary = get_market_summary(df)
    if summary:
        st.sidebar.metric("Total Stocks", summary['total_stocks'])
        st.sidebar.metric("Data as of", summary['latest_date'])
        
        if summary['gainers']:
            st.sidebar.markdown("**Top Gainers**")
            for g in summary['gainers'][:3]:
                st.sidebar.markdown(f"• {g['symbol']}: +{g['change']:.2f}")
        
        if summary['losers']:
            st.sidebar.markdown("**Top Losers**")
            for l in summary['losers'][:3]:
                st.sidebar.markdown(f"• {l['symbol']}: {l['change']:.2f}")


if __name__ == "__main__":
    main()
