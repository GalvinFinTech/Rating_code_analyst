import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from vnstock import *
from PIL import Image
import ta

st.set_page_config(page_title="Stock Dashboard", page_icon="📈", layout="wide")

# Đánh dấu hàm này để lưu trữ dữ liệu tải lên trong bộ nhớ cache
@st.cache_data
def load_data(file_path):
    df_info = pd.read_excel(file_path, sheet_name="Info")
    df_price = pd.read_excel(file_path, sheet_name="Price")
    df_volume = pd.read_excel(file_path, sheet_name="Volume")
    return df_info, df_price, df_volume
file_path = "Price-Vol VN 2015-2023.xlsx"

def load_and_clean_sheet(file_path):
    sheet = pd.read_excel(file_path, skiprows=7, skipfooter=11)
    sheet.columns = sheet.iloc[0]
    sheet = sheet.iloc[1:]
    return sheet

def filter_data(dt, industry, year):
    dt = dt.iloc[:, 1:]
    bank = dt[dt['Ngành ICB - cấp 4'].str.contains(industry, case=False, na=False)].copy()

    bank.index = [year] * len(bank)
    bank.reset_index(inplace=True)
    bank.rename(columns={'index': 'Year'}, inplace=True)
    for i in range(len(bank.columns)):
        quarter_info = f"\nHợp nhất\nQuý: Hàng năm\nNăm: {year}\n"
        if quarter_info in bank.columns[i]:
            bank.columns = bank.columns.str.replace(quarter_info, " ")
    return bank

def process_and_concat_data(years, industry):
    data_frames = [filter_data(load_and_clean_sheet(f"{year}-Vietnam.xlsx"), industry, year) for year in years]
    return pd.concat(data_frames, ignore_index=True)

def rename_columns_and_sort(df):
    df.rename(columns=lambda x: x.split('Đơn vị')[0].strip(), inplace=True)
    df.columns = df.columns.str.upper()
    df.sort_values(by=["MÃ", "YEAR"], inplace=True)

def process_numeric_column(df, column_name):
    df[column_name] = pd.to_numeric(df[column_name], errors='coerce')


def process_stock_data(df, code):
    mch_data = df[df['Mã'] == code].copy()
    mch_data.columns = mch_data.columns.str.split('\n').str[0]
    columns_cdkto = mch_data.filter(like='CĐKT.').columns
    df_cdkto = mch_data[['Năm'] + list(columns_cdkto)].reset_index(drop=True)
    columns_kqkd = mch_data.filter(like='KQKD.').columns
    df_kqkd = mch_data[['Năm'] + list(columns_kqkd)].reset_index(drop=True)
    columns_lctt = mch_data.filter(like='LCTT.').columns
    df_lctt = mch_data[['Năm'] + list(columns_lctt)].reset_index(drop=True)
    return df_cdkto, df_kqkd, df_lctt


def load_and_process_data(years, code):
    bctc = {year: load_and_clean_sheet(f'{year}-Vietnam.xlsx') for year in years}
    cdkt_dfs, kqkd_dfs, lctt_dfs = zip(*(process_stock_data(bctc[year], code) for year in years))

    df_cdkto_all = pd.concat(cdkt_dfs, ignore_index=True)
    df_kqkd_all = pd.concat(kqkd_dfs, ignore_index=True)
    df_lctt_all = pd.concat(lctt_dfs, ignore_index=True)

    for df in [df_cdkto_all, df_kqkd_all, df_lctt_all]:
        df['Năm'] = df['Năm'].astype(int)

    return df_cdkto_all, df_kqkd_all, df_lctt_all
years = [2018, 2019, 2020, 2021, 2022]
def prepare_data(data_dict, code):
    df_info, df_price, df_volume = data_dict
    stock_price = get_stock_data(df_price, code, "close")
    stock_volume = get_stock_data(df_volume, code, "volume")
    stock_info = df_info[df_info["Symbol"].str.contains(code, case=False, na=False)]
    return stock_info, stock_price, stock_volume
def get_stock_data(data_df, code, value_column):
    stock = data_df[data_df["Code"].astype(str).str.contains(code, case=False, na=False)]
    if stock.empty:
        return pd.DataFrame()
    stock_result = stock.melt(id_vars=["Name", "Code", "CURRENCY"], var_name="Date", value_name=value_column)
    stock_result = stock_result.dropna(subset=[value_column])
    return stock_result[["Date", value_column]]
def main():
    code = st.text_input('Enter stock code (Example: MCH):').upper()
    industry = 'Thực phẩm'
    bank_bctc = process_and_concat_data(years, industry)
    rename_columns_and_sort(bank_bctc)
    process_numeric_column(bank_bctc, 'CĐKT. VỐN CHỦ SỞ HỮU')
    avg_von = bank_bctc.groupby('MÃ')['CĐKT. VỐN CHỦ SỞ HỮU'].mean()
    top_10 = avg_von.nlargest(10)
    bctc = bank_bctc[bank_bctc['MÃ'].isin(top_10.index)]
    params = {
        "exchangeName": "HOSE,HNX,UPCOM",
        "epsGrowth1Year": (0, 1000000),
    }
    V = stock_screening_insights(params, size=1700, drop_lang='vi')
    mch_data = V[V['ticker'] == 'MCH']
    #mch_data_reset = mch_data.reset_index(drop=True)
    with st.sidebar:
        st.sidebar.title("📈 Stock Dashboard")
        options = st.sidebar.radio('Pages', options=['Phân tích ngành', 'Phân tích cổ phiếu'])
    # Tạo layout cột trái và cột phải
    left_column, right_column = st.columns(2)
    # Hiển thị tiêu đề và thông tin ở cột trái
    with left_column:
        st.title('MCH')
        image = Image.open('/Users/nguyenhoangvi/Downloads/Ứng dụng Python/Report - GPM/MCH.jpeg')
        st.image(image, caption='CTCP Hàng tiêu dùng Masan')
    with right_column:
        # Display metrics in a single row
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('Vốn hoá')
            mar = mch_data.at[mch_data.index[0], 'marketCap']
            st.subheader(mar)
        with c2:
            st.markdown('Beta')
            beta = mch_data.at[mch_data.index[0], 'beta']
            st.subheader(beta)
        with c3:
            st.markdown('EPS')
            eps =mch_data.at[mch_data.index[0],'eps']
            st.subheader(eps)

        # Display additional metrics in a single row
        c4, c5, c6 = st.columns(3)
        with c4:
            st.markdown('EV/Ebitda')
            ebit = mch_data.at[mch_data.index[0], 'evEbitda']
            st.subheader(ebit)
        with c5:
            st.markdown('PE')
            pe = mch_data.at[mch_data.index[0], 'pe']
            st.subheader(pe)
        with c6:
            st.markdown('PB')
            pb = mch_data.at[mch_data.index[0], 'pb']
            st.subheader(pb)

    df_info, df_price, df_volume = load_data(file_path)
    if options == 'Phân tích ngành':
            phan_tich_nganh(df_info,bctc)
    elif options == 'Phân tích cổ phiếu':
            phan_tich_cp(code,bctc)
# Trang phân tích ngành
def phan_tich_nganh(df_info,bctc):
    # Áp dụng bộ lọc với hàm để lấy kết quả
    params = {
        "exchangeName": "HOSE,HNX,UPCOM",
        "epsGrowth1Year": (0, 1000000)
    }
    V = stock_screening_insights(params, size=1700, drop_lang='vi')

    a1,a2 = st.columns(2)
    with a1:
        chart_type = st.radio('Select Chart Type:', ['Treemap', 'Sunburst'])
        value_col = st.selectbox('Select Value to Plot:', ['totalTradingValue', 'marketCap'])
    with a2:
        width = st.slider('Width', min_value=200, max_value=1600, value=1000, step=100)
        height = st.slider('Height', min_value=200, max_value=1200, value=600, step=100)
    # Biểu đồ Treemap hoặc Sunburst tùy thuộc vào lựa chọn từ người dùng
    fig = create_chart(V, value_col, chart_type=chart_type.lower(), width=width, height=height)
    # Hiển thị biểu đồ trong ứng dụng Streamlit
    st.plotly_chart(fig)

    nganh = industry_analysis('MCH', lang="vi")
    d1 = preprocess_industry_data(nganh)
    d1.columns = ['Mã CP', 'Vốn hóa(tỷ)', 'Giá', 'P/B', 'ROE', 'P/E', 'ROA']
    # Chọn giá trị cho x và y từ người dùng
    selected_x = st.selectbox('Chọn giá trị cho trục x:', ['ROE', 'ROA'])
    selected_y = st.selectbox('Chọn giá trị cho trục y:', ['P/B', 'P/E'])

    # Tạo biểu đồ dựa trên lựa chọn của người dùng
    fig = px.scatter(
        d1, x=selected_x, y=selected_y, size="Vốn hóa(tỷ)", text="Mã CP",
        color="Vốn hóa(tỷ)", color_continuous_scale="Rainbow", size_max=120,
        hover_name="Mã CP", hover_data={selected_x: True, selected_y: True, "Vốn hóa(tỷ)": True, "Mã CP": False}
    )
    # Update layout
    fig.update_layout(
        title=f'So sánh tương quan - {selected_x} vs {selected_y}',
        xaxis=dict(title=f'{selected_x}'),
        yaxis=dict(title=f'{selected_y}'),
        showlegend=False,
        plot_bgcolor='white'
    )
    # Hiển thị biểu đồ
    st.plotly_chart(fig, use_container_width=True)
    st.write('So với các cổ phiếu cùng ngành khác, MCH có những điểm nổi bật sau:'
             '\n - MCH có hiệu quả sử dụng vốn chủ sở hữu và tổng tài sản tốt nhất. Điều này cho thấy công ty này có khả năng tạo ra lợi nhuận cao từ vốn và tài sản của mình.'
             '\n - MCH có tiềm năng tăng trưởng cao. Điều này được thể hiện qua giá trị PE thấp của cổ phiếu.'
             )

    col1, col2 = st.columns(2)
    with col1:
        sector_counts = df_info['Sector'].value_counts()
        color_palette = px.colors.qualitative.Light24
        fig_sector = px.bar(x=sector_counts.index, y=sector_counts.values, title='Number of Stocks by Sector',
                            color_discrete_sequence=color_palette)
        st.plotly_chart(fig_sector, use_container_width=True)

    with col2:
        exchange_counts = df_info['Exchange'].value_counts()
        fig_exchange = go.Figure([go.Pie(labels=exchange_counts.index, values=exchange_counts.values)])
        fig_exchange.update_layout(title='Number of Stocks by Exchange')
        st.plotly_chart(fig_exchange, use_container_width=True)
#Trang phân tích cổ phiếu
def phan_tich_cp(code,bctc):
    #code = st.text_input('Enter stock code (Example: MCH):').upper()
    data_dict = load_data(file_path)
    stock_info, stock_price, stock_volume = prepare_data(data_dict, code)
    merged_df = pd.concat([stock_price.set_index('Date'), stock_volume.set_index('Date')], axis=1)
    df = merged_df.reset_index()
    df['Date'] = pd.to_datetime(df['Date'])
    df_cdkto, df_kqkd, df_lctt = load_and_process_data(years, code)

    st.markdown('### Time Series Analysis')
    left_column, right_column = st.columns((7, 3))
    with right_column:
        st.write('')
    with left_column:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=df['close'],
                                 mode='lines',
                                 name='Close Price',
                                 line=dict(color='blue', width=2)))  # Tùy chỉnh màu sắc và độ rộng đường

        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Close Price',
            hovermode='x unified',
            showlegend=True)

        colors = ['red' if df['close'].iloc[i] > df['close'].iloc[i - 1] else 'green' for i in range(1, len(df))]

        fig.add_trace(go.Bar(x=df['Date'].iloc[1:], y=df['volume'].iloc[1:],
                             name='Volume',
                             yaxis='y2',
                             marker=dict(color=colors),
                             hovertemplate='</b>: %{y}k'))  # Tùy chỉnh mẫu hovertemplate

        # Tùy chỉnh biểu đồ cho trục y thứ hai
        fig.update_layout(yaxis2=dict(title='Volume', overlaying='y', side='right'))

        # Thêm thanh trượt thời gian và nút chọn khoảng thời gian
        fig.update_xaxes(title_text='Date', rangeslider_visible=False, rangeselector=dict(
            buttons=[
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(count=5, label="5y", step="year", stepmode="backward"),
                dict(step="all")
            ]
        ))

        # Hiển thị biểu đồ
        st.plotly_chart(fig, use_container_width=True)

    t1,t2,t3,t4,t5,t6 = st.tabs(["Tổng quan",'Phân tích 360','Phân tích kĩ thuật','Tài chính','Hồ sơ','Cổ đông'])
    # Retrieve data based on the stock symbol
    with t1:
        data = general_rating(code)
        data.columns = ['Đánh giá Cổ phiếu', 'Định giá', 'Sức khỏe tài chính', 'Mô hình kinh doanh',
                        'Hiệu quả hoạt động', 'Điểm RS', 'Điểm TA', 'Mã cổ phiếu', 'Giá cao nhất',
                        'Giá thấp nhất', 'Thay đổi giá 3 tháng', 'Thay đổi giá 1 năm', 'Beta', 'Alpha']
        # Melt DataFrame to have a 'criteria' column
        df_melted = pd.melt(data, id_vars=['Mã cổ phiếu'],
                            value_vars=['Định giá', 'Sức khỏe tài chính', 'Mô hình kinh doanh',
                                        'Hiệu quả hoạt động', 'Điểm RS'])
        # Create Radar Chart with Plotly Express
        fig = px.line_polar(df_melted, r='value', theta='variable', line_close=True, color='Mã cổ phiếu',
                            labels={'variable': 'Tiêu chí', 'value': 'Điểm'},
                            title='Biểu đồ Radar - Tiêu chí Đánh giá Cổ phiếu',
                            height=600, width=1000,
                            color_discrete_sequence=px.colors.qualitative.Dark2
                            )
        # Customizing Radar Chart with Plotly Graph Objects
        fig.update_traces(fill='toself', hoverinfo='all', hovertemplate='%{r:.2f}',fillcolor='rgba(0, 200, 0, 0.5)')


        # Add highlighting at all highest points
        max_indices = df_melted.loc[df_melted.groupby('variable')['value'].idxmax()]
        for idx, row in max_indices.iterrows():
            fig.add_trace(go.Scatterpolar(
                r=[row['value']],
                theta=[row['variable']],
                mode='markers',
                marker=dict(color='orange', size=6),
                showlegend=False
            ))

        # Show the chart
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
        st.plotly_chart(fig)
        ta1,ta2 = st.columns(2)
        # Example usage
        df4 = valuation_rating("MCH")
        data4 = df4[['ticker', 'valuation', 'pe', 'pb', 'ps', 'evebitda','dividendRate']]
        data4.columns = ['Mã','Xếp hạng định giá','P/E','P/B','P/S','EV/EBITDA','Tỷ lệ cổ tức']

        df3 = financial_health_rating("MCH")
        data3 = df3[['ticker', 'financialHealth', 'netDebtEquity',
                    'currentRatio', 'quickRatio', 'interestCoverage', 'netDebtEBITDA']]
        data3.columns = ['Mã','Sức khoẻ tài chính','Dư nợ ròng/Vốn chủ sở hữu','Tỷ lệ thanh toán ngắn hạn',
        'Tỷ lệ thanh toán nhanh','Khả năng trả lãi vay','Dư nợ ròng/EBITDA']

        df2 = biz_operation_rating("MCH")
        data2 = df2[['ticker', 'avgROE', 'avgROA', 'last5yearsNetProfitGrowth',
                    'last5yearsRevenueGrowth', 'last5yearsOperatingProfitGrowth',
                    'last5yearsEBITDAGrowth', 'last5yearsFCFFGrowth',
                    'lastYearGrossProfitMargin', 'lastYearOperatingProfitMargin',
                    'lastYearNetProfitMargin']]
        data2.columns = ['Mã','ROE','ROA', 'Tăng trưởng lợi nhuận ròng 5 năm gần nhất',
        'Tăng trưởng doanh thu 5 năm gần nhất', 'Tăng trưởng lợi nhuận từ hoạt động kinh doanh 5 năm gần nhất',
        'Tăng trưởng EBITDA 5 năm gần nhất',   'Tăng trưởng FCFF 5 năm gần nhất','Biên lợi nhuận gộp năm trước',
        'Biên lợi nhuận thuần năm trước',  'Biên lợi nhuận hoạt động năm trước']

        df1 = biz_model_rating(code)
        data1 = df1[['ticker', 'businessEfficiency', 'assetQuality', 'cashFlowQuality', 'bom', 'businessAdministration',
                'productService', 'businessAdvantage', 'companyPosition', 'industry', 'operationRisk']]
        data1.columns = ['Mã', 'Hiệu suất kinh doanh', 'Chất lượng tài sản', 'Chất lượng dòng tiền', 'BOM',
        'Quản trị kinh doanh','Sản phẩm/Dịch vụ',   'Ưu thế kinh doanh','Vị trí công ty', 'Công nghiệp',
        'Rủi ro hoạt động']
        color_sequence1 = px.colors.qualitative.Plotly
        color_sequence2 = px.colors.qualitative.Prism
        with ta1:
            display_radar_chart(data1, 'Mô hình kinh doanh',color_sequence2)
            display_radar_chart(data2, 'Hiệu quả hoạt động',color_sequence1)
        with ta2:
            display_radar_chart(data4, 'Định giá',color_sequence1)
            display_radar_chart(data3, 'Sức khoẻ tài chính',color_sequence2)

    with t2:
        df_pe = stock_evaluation(symbol=code, period=5, time_window='D')
        fig_pe = create_stock_evaluation_chart(df_pe, 'PE', 'So sánh PE')
        df_pb = stock_evaluation(symbol=code, period=5, time_window='D')
        fig_pb = create_stock_evaluation_chart(df_pb, 'PB', 'So sánh PB')
        # Lựa chọn từ người dùng để chọn biểu đồ muốn hiển thị
        selected_chart = st.radio('Chọn biểu đồ để hiển thị', ['PE', 'PB'])
        # Hiển thị biểu đồ tương ứng với lựa chọn
        if selected_chart == 'PE':
            st.plotly_chart(fig_pe)
        elif selected_chart == 'PB':
            st.plotly_chart(fig_pb)
        st.write(
            'Kết luận:',
            ' Nhìn chung, có thể thấy MCH đang được định giá thấp hơn so với các công ty cùng ngành về PE, nhưng đang được định giá cao hơn so với các công ty cùng ngành và so với thị trường về PB.',
            ' Nguyên nhân có thể là do MCH là một công ty mới thành lập, nhưng có tốc độ tăng trưởng nhanh chóng, tiềm năng tăng trưởng cao và có thương hiệu mạnh.',
            ' Tuy nhiên, nhà đầu tư cần cân nhắc kỹ lưỡng các yếu tố rủi ro tiềm ẩn trước khi quyết định đầu tư vào MCH, bao gồm:',
            '\n -  MCH là một công ty mới thành lập, chưa có nhiều kinh nghiệm.',
            '\n -  MCH đang phải đối mặt với sự cạnh tranh gay gắt từ các công ty cùng ngành.'
        )
        fig7 = plot_revenue_comparison(bctc)
        st.plotly_chart(fig7)
        fig8 = plot_equity(bctc)
        st.plotly_chart(fig8)
        fig9 = plot_profit_after_tax(bctc)
        st.plotly_chart(fig9)

    with t3:
        start_date = pd.to_datetime(df["Date"]).min()
        end_date = pd.to_datetime(df["Date"]).max()
        col1, col2 = st.columns((2))
        with col1:
            date1 = pd.to_datetime(st.date_input("Start Date", start_date))
            date2 = pd.to_datetime(st.date_input("End Date", end_date))
        selected_data = df[(df['Date'] >= date1) & (df['Date'] <= date2)]
        with col2:
            # User-defined indicators and windows
            available_sma_windows = ['10', '14', '20', '50', '100']
            selected_sma_windows = st.multiselect('Select SMA Windows', available_sma_windows)
            available_ema_windows = ['10', '14', '20', '50', '100', '200']
            selected_ema_windows = st.multiselect('Select EMA Windows', available_ema_windows)
            chart_type = st.selectbox("Select Chart Type", ["MACD", "RSI"])
        l, r = st.columns(2)
        with l:
            # Create figure
            fig = go.Figure()
            # Plot Close Price
            add_trace(fig, selected_data['Date'], selected_data['close'], 'Close Price', 'blue', width=2)
            # Plot selected indicators
            plot_sma(fig, selected_data, selected_sma_windows, 'orange')
            plot_ema(fig, selected_data, selected_ema_windows, 'pink')
            plot_bollinger(fig, selected_data)
            # Tùy chỉnh biểu đồ
            fig.update_layout(
                title="Stock Price with Technical Indicators",
                xaxis_title='Date',
                yaxis_title='Close Price',
                showlegend=True,
                hovermode='x unified'
            )

            colors = ['red' if selected_data['close'].iloc[i] > selected_data['close'].iloc[i - 1] else 'green' for i in
                      range(1, len(selected_data))]

            fig.add_trace(go.Bar(x=selected_data['Date'].iloc[1:], y=selected_data['volume'].iloc[1:],
                                 name='Volume',
                                 yaxis='y2',
                                 marker=dict(color=colors),
                                 hovertemplate='</b>: %{y}k'))  # Tùy chỉnh mẫu hovertemplate

            # Tùy chỉnh biểu đồ cho trục y thứ hai
            fig.update_layout(yaxis2=dict(title='Volume', overlaying='y', side='right'))
            # Thêm thanh trượt thời gian và nút chọn khoảng thời gian
            fig.update_xaxes(title_text='Date', rangeslider_visible=False, rangeselector=dict(
                buttons=[
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(count=5, label="5y", step="year", stepmode="backward"),
                    dict(step="all")
                ]
            ))
            # Show the plot
            st.plotly_chart(fig)
        with r:
            macd_container = st.container()
            rsi_container = st.container()
            stochastic_container = st.container()
            if chart_type == "MACD":
                with macd_container:
                    plot_macd_chart(selected_data)
            elif chart_type == "RSI":
                with rsi_container:
                    st.plotly_chart(plot_rsi_chart(selected_data))

        expander = st.expander("Stock Data")
        expander.write(selected_data)

    with t4:
        fig1 = plot_accounting_balance(df_cdkto)
        st.plotly_chart(fig1)
        fig2 = plot_business_results(df_kqkd)
        st.plotly_chart(fig2)
        fig3 = plot_cash_flow(df_lctt)
        st.plotly_chart(fig3)
        fig4= plot_capital_structure(df_cdkto)
        st.plotly_chart(fig4)
        fig5 = plot_asset_structure(df_cdkto)
        st.plotly_chart(fig5)
        fig10 = plot_profit_structure(df_kqkd)
        st.plotly_chart(fig10)
        fig6 = plot_gross_profit_margin(df_kqkd)
        st.plotly_chart(fig6)




    with t5:
        co1,co2 = st.columns((6, 4))
        with co1:
            st.header('Thông tin sơ lược về cổ phiếu MCH')
            st.subheader('Vị thế công ty')
            st.write(
                'Công ty Cổ phần Hàng Tiêu Dùng MaSan (MCH) có tiền thân là Công ty Cổ phần Công nghiệp - Thương mại '
                'Masan được thành lập vào năm 2000. Công ty sản xuất và kinh doanh các loại thực phẩm và đồ uống '
                'bao gồm nước mắm, nước tương, tương ớt, mì ăn liền, cháo ăn liền, cà phê hòa tan, ngũ cốc dinh dưỡng'
                ' và đồ uống đóng chai với các thương hiệu mạnh như: Omachi, Chinsu, Kokomi, Vinacafe, Wake-up, '
                'Tam Thái Tử, Nam Ngư, Wake-up 247. Công ty đã sở hữu các ngành hàng chiếm % thị phần như sau: '
                'Nước mắm 66%, nước tương 67%, mì ăn liền 21%, tương ớt 71% và cà phê hòa tan 35% tính đến cuối năm 2017. '
                'Công ty đã xây dựng một trong những hệ thống phân phối thực phẩm và đồ uống lớn nhất tại Việt Nam '
                'với gần 180.000 điểm bán lẻ sản phẩm thực phẩm, 160.000 điểm bán lẻ sản phẩm đồ uống, 3 trung tâm '
                'phân phối tại Miền Nam, Miền Trung và Miền Bắc. MCH được giao dịch trên thị trường UPCOM từ đầu năm 2017.')
            st.subheader('Sản phẩm dịch vụ chính')
            st.write('Sản xuất và kinh doanh các loại thực phẩm và đồ uống;')
            st.subheader('Chiến lược phát triển và đầu tư')
            st.write('\n - Trở thành Công ty hàng tiêu dùng dẫn đầu Việt Nam xét về doanh số, lợi nhuận.'
                     '\n - Mục tiêu nắm giữ 70% thị phần các ngành gia vị và 35-40% thị phần thực phẩm tiện dụng.'
                     '\n - Tốc độ phát triển trung bình của doanh thu trong giai đoạn 2020-2025 đạt trên 20%/năm.'
                     '\n - Tập trung vào hai nhóm hàng chính là gia vị và mì ăn liền.'
                     '\n - Đẩy mạnh ngành hàng đồ uống nhằm đạt được mục tiêu doanh thu phân bổ theo tỷ lệ 50% đóng góp từ đồ uống, 50% từ thực phẩm vào năm 2025'
                     '\n - Đẩy mạnh thị phần dòng trung cấp với nhãn hiệu nước mắm Nam Ngư, nước tương Tam Thái Tử và mì gói Sagami, Kokomi, cà phê Wake-Up, Wake-Up 247;')
            st.subheader('Rủi ro kinh doanh')
            st.write(
                'Chi tiêu trên đầu người đối với thực phẩm và đồ uống của Việt Nam còn thấp so với các nước trong khu vực. Người tiêu dùng có xu hướng ngày càng thắt chặt chi tiêu. Họ thường chọn những sản phẩm có giá cả hợp lý thay vì chọn những sản phẩm xa xỉ.')
        with co2:
            lanh_dao = company_officers(symbol=code, page_size=20, page=0)
            # Bỏ cột và đổi tên cột
            df_new = lanh_dao.drop(['ticker', 'officerPosition'], axis=1)
            df_new['officerOwnPercent'] = df_new['officerOwnPercent'] * 100  # Chuyển đổi về đơn vị %
            # Đổi tên cột
            y = df_new.rename(columns={'officerName': 'Ban lãnh đạo', 'officerOwnPercent': 'Tỷ lệ CP (%)'})
            st.checkbox("Chi tiết", value=False, key="co2_checkbox")
            st.dataframe(y, use_container_width=st.session_state.co2_checkbox)

            cty_con = company_subsidiaries_listing(symbol=code, page_size=100, page=0)
            x = cty_con.rename(columns={'subCompanyName': 'Công ty con', 'subOwnPercent': 'Tỷ lệ (%) sở hữu'}).drop(
                'ticker',
                axis=1)
            x['Tỷ lệ (%) sở hữu'] = x['Tỷ lệ (%) sở hữu'] * 100
            st.checkbox("Chi tiết", value=False, key="co1_checkbox")
            st.dataframe(x, use_container_width=st.session_state.co1_checkbox)

    with t6:
        co_dong = company_large_shareholders(symbol=code)
        z = co_dong.rename(columns={'shareHolder': 'Cổ đông', 'shareOwnPercent': 'Tỷ lệ(%)'}).drop('ticker', axis=1)
        z['Tỷ lệ(%)'] = z['Tỷ lệ(%)'] * 100  # Chuyển đổi về đơn vị %
        st.checkbox("Chi tiết", value=False, key="t5_checkbox")
        st.dataframe(z, use_container_width=st.session_state.t5_checkbox)
def preprocess_industry_data(industry_data):
    industry_data = industry_data.loc[["Vốn hóa (tỷ)", "Giá", "P/E", "ROE", "P/B", "ROA"]]
    industry_data = industry_data.transpose().reset_index()
    industry_data.columns = ["Mã CP", "Vốn hóa (tỷ)", "Giá", "P/E", "ROE", "P/B", "ROA"]
    industry_data["ROE"] *= 100
    industry_data["ROA"] *= 100
    industry_data['Vốn hóa (tỷ)'] = pd.to_numeric(industry_data['Vốn hóa (tỷ)'], errors='coerce')
    return industry_data
def create_stock_evaluation_chart(df, metric, title):
    traces = [
        go.Scatter(
            x=df['fromDate'],
            y=df[metric],
            mode='lines',
            name=f'{metric} - {symbol}',
            hovertemplate='<b>%{x}</b><br>%{y}',
        )
        for metric, symbol in zip([metric, f'industry{metric}', f'vnindex{metric}'], ['Công ty', 'Ngành', 'Thị trường'])
    ]

    layout = go.Layout(
        title=f'{title} của Công ty, Ngành và Thị trường',
        xaxis=dict(title='Thời Gian', rangeselector=dict(buttons=list([
            dict(count=1, label='1M', step='month', stepmode='backward'),
            dict(count=6, label='6M', step='month', stepmode='backward'),
            dict(count=1, label='YTD', step='year', stepmode='todate'),
            dict(count=1, label='1Y', step='year', stepmode='backward'),
            dict(step='all')
        ]))),
        yaxis=dict(title=metric),
        hovermode='x unified',
    )

    return go.Figure(data=traces, layout=layout)
def create_chart(df, value_col, chart_type='treemap', color_continuous_scale='RdBu', width=1000, height=600):
    df_filtered = df[df[value_col] != 0].dropna(subset=[value_col])

    if chart_type not in ['treemap', 'sunburst']:
        raise ValueError("Invalid chart_type. Please choose 'treemap' or 'sunburst'.")

    if chart_type == 'treemap':
        fig = px.treemap(
            df_filtered,
            path=['industryName.en', 'ticker'],
            values=value_col,
            color=value_col,
            color_continuous_scale=color_continuous_scale,
            title=f'Treemap - {value_col} ',
            labels=df_filtered['ticker'],
            custom_data=[df_filtered[value_col]]
        )
    elif chart_type == 'sunburst':
        fig = px.sunburst(
            df_filtered,
            path=['industryName.en', 'ticker'],
            values=value_col,
            color=value_col,
            color_continuous_scale=color_continuous_scale,
            title=f'Sunburst - {value_col} ',
            labels=df_filtered['ticker'],
            custom_data=[df_filtered[value_col]]
        )

    fig.update_layout(width=width, height=height)

    fig.update_layout(
        margin=dict(l=0, r=0, b=0, t=30) if chart_type == 'treemap' else dict(l=0, r=0, b=0, t=100),
        showlegend=False
    )

    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>%{customdata:,.2f}',
        textinfo='label+value',
    )
    return fig
def calculate_rsi(data, window=14):
    delta = data.diff()
    up = delta.mask(delta < 0, 0)
    down = -delta.mask(delta > 0, 0)

    avg_gain = up.rolling(window).mean()
    avg_loss = down.rolling(window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
# Tạo hàm để vẽ biểu đồ RSI
def plot_rsi_chart(data):
    fig = go.Figure()

    # Tính toán và thêm đường RSI vào biểu đồ
    rsi = calculate_rsi(data['close'])
    fig.add_trace(go.Scatter(
        x=data['Date'],
        y=rsi,
        mode='lines',
        name='RSI',
        line=dict(color='purple', width=1)
    ))

    # Thêm đường ngưỡng bán (Y=80)
    fig.add_trace(go.Scatter(
        x=data['Date'],
        y=[80] * len(data),
        mode='lines',
        name='Overbought',
        line=dict(color='red', width=1, dash='dash')
    ))

    # Thêm đường ngưỡng mua (Y=20)
    fig.add_trace(go.Scatter(
        x=data['Date'],
        y=[20] * len(data),
        mode='lines',
        name='Oversold',
        line=dict(color='blue', width=1, dash='dash')
    ))

    # Tùy chỉnh biểu đồ
    fig.update_layout(
        title="RSI Chart",
        xaxis_title='Date',
        yaxis_title='RSI',
        showlegend=True,
        plot_bgcolor='white',
        hovermode='x unified'
    )

    # Thêm thanh trượt thời gian và nút chọn khoảng thời gian
    fig.update_xaxes(title_text='Date', rangeslider_visible=False, rangeselector=dict(
        buttons=[
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(count=5, label="5y", step="year", stepmode="backward"),
            dict(step="all")
        ]
    ))

    return fig
def plot_macd_chart(data):
    fig = go.Figure()

    # Tính toán các giá trị MACD
    data['ema_12'] = data['close'].ewm(span=12, adjust=False).mean()
    data['ema_26'] = data['close'].ewm(span=26, adjust=False).mean()
    data['macd'] = data['ema_12'] - data['ema_26']
    data['signal'] = data['macd'].ewm(span=9, adjust=False).mean()
    data['histogram'] = data['macd'] - data['signal']

    # Đường MACD
    fig.add_trace(go.Scatter(
        x=data['Date'],
        y=data['macd'],
        mode='lines',
        name='MACD',
        line=dict(color='blue', width=1)
    ))

    # Đường tín hiệu (signal)
    fig.add_trace(go.Scatter(
        x=data['Date'],
        y=data['signal'],
        mode='lines',
        name='Signal',
        line=dict(color='orange', width=1)
    ))

    # Cột histogram
    fig.add_trace(go.Bar(
        x=data['Date'],
        y=data['histogram'],
        name='Histogram',
        marker=dict(
            color=data['histogram'],
            colorscale=[[0, 'red'], [0.5, 'red'], [0.5, 'green'], [1, 'green']],
            cmin=-max(abs(data['histogram'])),
            cmax=max(abs(data['histogram'])),
            showscale=False
        )
    ))

    # Tùy chỉnh biểu đồ
    fig.update_layout(
        title="MACD Chart",
        xaxis_title='Date',
        yaxis_title='MACD',
        showlegend=True, plot_bgcolor='white', hovermode='x unified',
    )

    # Thêm thanh trượt thời gian và nút chọn khoảng thời gian
    fig.update_xaxes(title_text='Date', rangeslider_visible=False, rangeselector=dict(
        buttons=[
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(count=5, label="5y", step="year", stepmode="backward"),
            dict(step="all")
        ]
    ))

    # Hiển thị biểu đồ trong Streamlit
    st.plotly_chart(fig)
def add_trace(fig, x, y, name, color, width=1.5, mode='lines'):
    fig.add_trace(go.Scatter(x=x, y=y, mode=mode, name=name, line=dict(color=color, width=width)))
def plot_sma(fig, df, windows, color):
    for window in windows:
        df[f'sma_{window}'] = ta.trend.sma_indicator(df['close'], window=int(window))
        add_trace(fig, df['Date'], df[f'sma_{window}'], f"SMA ({window})", color)
def plot_ema(fig, df, windows, color):
    for window in windows:
        df[f'ema_{window}'] = ta.trend.ema_indicator(df['close'], window=int(window))
        add_trace(fig, df['Date'], df[f'ema_{window}'], f"EMA ({window})", color)
def plot_bollinger(fig, df):
    df['bollinger_hband'] = ta.volatility.bollinger_hband(df['close'], window=20, window_dev=2)
    df['bollinger_lband'] = ta.volatility.bollinger_lband(df['close'], window=20, window_dev=2)
    add_trace(fig, df['Date'], df['bollinger_hband'], 'Bollinger High', 'red', width=1)
    add_trace(fig, df['Date'], df['bollinger_lband'], 'Bollinger Low', 'green', width=1)
def radar_chart(df, title, color_sequence):
    # Melt DataFrame to have a 'criteria' column
    df_melted = pd.melt(df, id_vars=['Mã'],
                        value_vars=df.columns[1:])

    # Create Radar Chart with Plotly Express
    fig = px.line_polar(df_melted, r='value', theta='variable', line_close=True, color='Mã',
                        labels={'variable': 'Tiêu chí', 'value': 'Điểm'},
                        title=title,
                        height=400, width=700,
                        color_discrete_sequence=color_sequence)

    # Customizing Radar Chart with Plotly Graph Objects
    fig.update_traces(fill='toself', hoverinfo='all', hovertemplate='%{r:.2f}', fillcolor='rgba(0, 200, 0, 0.5)')

    # Add highlighting at all highest points
    max_indices = df_melted.loc[df_melted.groupby('variable')['value'].idxmax()]
    for idx, row in max_indices.iterrows():
        fig.add_trace(go.Scatterpolar(
            r=[row['value']],
            theta=[row['variable']],
            mode='markers',
            marker=dict(color='orange', size=6),
            showlegend=False
        ))

    # Show the chart
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
    return fig
def display_radar_chart(df, title, color_sequence):
    st.plotly_chart(radar_chart(df, title, color_sequence))
#OK
def plot_accounting_balance(df):
    # Your plotting logic here
    colors = ['rgb(200,50, 50)', 'rgb(50, 200,10)', 'rgb(10, 60, 200)']
    # Tạo dữ liệu cho các cột nhóm với màu pastel
    data = [
        go.Bar(
            name='Tổng tài sản',
            x=df['Năm'],
            y=df['CĐKT. TỔNG CỘNG TÀI SẢN'],
            marker_color=colors[0]
        ),
        go.Bar(
            name='Vốn chủ sở hữu',
            x=df['Năm'],
            y=df['CĐKT. VỐN CHỦ SỞ HỮU'],
            marker_color=colors[2]
        )]
    layout = go.Layout(
        title='CÂN ĐỐI KẾ TOÁN',
        xaxis=dict(title='Giá trị (đồng)'),
        yaxis=dict(title='Năm'),
        barmode='group'
    )
    # Tạo đối tượng Figure và thêm dữ liệu và layout vào
    fig = go.Figure(data=data, layout=layout)

    return fig#OK
#OK
def plot_business_results(df):
    # Tạo bảng màu pastel
    colors = ['rgb(250,50, 50)', 'rgb(0, 200,0)']

    # Tạo dữ liệu cho các cột nhóm với màu pastel
    data = [
        go.Bar(
            name='Doanh thu thuần',
            x=df['Năm'],
            y=df['KQKD. Doanh thu thuần'],
            marker_color=colors[0]
        ),
        go.Bar(
            name='Lợi nhuận sau thuế',
            x=df['Năm'],
            y=df['KQKD. Lợi nhuận sau thuế thu nhập doanh nghiệp'],
            marker_color=colors[1]
        )
    ]
    layout = go.Layout(
            title='Kết quả kinh doanh',
            xaxis=dict(title='Giá trị (đồng)'),
            yaxis=dict(title='Năm'),
            barmode='group'
        )
    # Tạo đối tượng Figure và thêm dữ liệu và layout vào
    fig = go.Figure(data=data, layout=layout)

    return fig#OK
#OK
def plot_cash_flow(df):
    # Tạo bảng màu pastel
    colors = ['rgb(250,50, 50)', 'rgb(0, 200,0)', 'rgb(50, 50, 255)']

    # Tạo dữ liệu cho các cột nhóm với màu pastel
    data = [
        go.Bar(
            name='LCTT từ hoạt động tài chính',
            x=df['Năm'],
            y=df['LCTT. Lưu chuyển tiền tệ từ hoạt động tài chính (TT)'],
            marker_color=colors[0]
        ),
        go.Bar(
            name='LCTT từ hoạt động kinh doanh',
            x=df['Năm'],
            y=df['LCTT. Lưu chuyển tiền tệ ròng từ các hoạt động sản xuất kinh doanh (TT)'],
            marker_color=colors[1]
        ),
        go.Bar(
            name='LCTT từ hoạt động đầu tư',
            x=df['Năm'],
            y=df['LCTT. Lưu chuyển tiền tệ ròng từ hoạt động đầu tư (TT)'],
            marker_color=colors[2]
        )
    ]
    layout = go.Layout(
            title='DÒNG TIỀN',
            xaxis=dict(title='Giá trị (đồng)'),
            yaxis=dict(title='Năm'),
            barmode='group')
    # Tạo đối tượng Figure và thêm dữ liệu và layout vào
    fig = go.Figure(data=data, layout=layout)

    return fig


def plot_capital_structure(df_cdkto):
    df_melted = pd.melt(df_cdkto, id_vars=['Năm'], value_vars=[
        'CĐKT. NỢ PHẢI TRẢ', 'CĐKT. Nợ ngắn hạn',
       'CĐKT. Phải trả người bán ngắn hạn',
       'CĐKT. Người mua trả tiền trước ngắn hạn',
       'CĐKT. Doanh thu chưa thực hiện ngắn hạn',
       'CĐKT. Vay và nợ thuê tài chính ngắn hạn', 'CĐKT. Nợ dài hạn',
       'CĐKT. Phải trả nhà cung cấp dài hạn',
       'CĐKT. Người mua trả tiền trước dài hạn',
       'CĐKT.Doanh thu chưa thực hiên dài hạn',
       'CĐKT. Vay và nợ thuê tài chính dài hạn', 'CĐKT. VỐN CHỦ SỞ HỮU',
       'CĐKT. Vốn và các quỹ', 'CĐKT. Vốn góp của chủ sở hữu',
       'CĐKT. Thặng dư vốn cổ phần', 'CĐKT.Vốn khác',
       'CĐKT. Lãi chưa phân phối',
       'CĐKT. LNST chưa phân phối lũy kế đến cuối kỳ trước',
       'CĐKT. LNST chưa phân phối kỳ này',
       'CĐKT. Lợi ích cổ đông không kiểm soát',
       'CĐKT. Nguồn kinh phí và quỹ khác',
       'CĐKT. LỢI ÍCH CỦA CỔ ĐÔNG KHÔNG KIỂM SOÁT (trước 2015)',
       'CĐKT. TỔNG CỘNG NGUỒN VỐN']
                        , var_name='Loại', value_name='Giá trị')
    df_cdkto['Tỷ số Nợ vay trên Tổng tài sản'] = (df_cdkto['CĐKT. Vay và nợ thuê tài chính ngắn hạn'] + df_cdkto['CĐKT. Vay và nợ thuê tài chính dài hạn']) / df_cdkto['CĐKT. TỔNG CỘNG TÀI SẢN']
    # Sắp xếp lại dữ liệu theo năm
    df_melted.sort_values(by='Năm', inplace=True)

    # Sử dụng plotly.graph_objects để vẽ biểu đồ cột đôi
    fig = go.Figure()

    for i, loai in enumerate(df_melted['Loại'].unique()):
        fig.add_trace(go.Bar(
            x=df_melted[df_melted['Loại'] == loai]['Năm'],
            y=df_melted[df_melted['Loại'] == loai]['Giá trị'],
            name=loai
        ))
    fig.add_trace(go.Scatter(x=df_cdkto['Năm'], y=df_cdkto['Tỷ số Nợ vay trên Tổng tài sản'], mode='lines+markers',
                             name='Tỉ lệ Nợ vay/TTS', yaxis='y2'))
    fig.update_layout(yaxis2=dict(anchor='x', overlaying='y', side='right'))

    # Cấu hình trực quan cho biểu đồ
    fig.update_layout(
        barmode='group',
        xaxis_tickmode='linear',
        xaxis_title='Năm',
        yaxis_title='Giá trị (tỷ đồng)',
        title='Cơ Cấu Nguồn vốn',
        updatemenus=[
            dict(
                active=0,
                buttons=list([
                    dict(label='Tăng', method='relayout', args=['barmode', 'stack']),
                    dict(label='Tăng cường', method='relayout', args=['barmode', 'group'])
                ]),
                direction='down',
                showactive=True,
                x=1.05,
                xanchor='left',
                y=1.2,
                yanchor='top'
            )
        ]
    )

    return fig

def plot_asset_structure(df_cdkto):
    df_cdkto['Tiền/TTS'] = df_cdkto['CĐKT. TÀI SẢN NGẮN HẠN'] / df_cdkto['CĐKT. TỔNG CỘNG TÀI SẢN']
    # Melt DataFrame để có thể sử dụng biểu đồ cột đôi
    df_melted = pd.melt(df_cdkto, id_vars=['Năm'], value_vars=[
        'CĐKT. TÀI SẢN NGẮN HẠN', 'CĐKT. Tiền và tương đương tiền ',
        'CĐKT. Đầu tư tài chính ngắn hạn', 'CĐKT. Các khoản phải thu ngắn hạn',
        'CĐKT. Hàng tồn kho, ròng', 'CĐKT. Tài sản ngắn hạn khác',
        'CĐKT. TÀI SẢN DÀI HẠN', 'CĐKT. Phải thu dài hạn',
        'CĐKT. Tài sản cố định', 'CĐKT. GTCL TSCĐ hữu hình',
        'CĐKT. GTCL Tài sản thuê tài chính',
        'CĐKT. GTCL tài sản cố định vô hình',
        'CĐKT. Xây dựng cơ bản dở dang (trước 2015)',
        'CĐKT. Giá trị ròng tài sản đầu tư', 'CĐKT. Tài sản dở dang dài hạn',
        'CĐKT. Đầu tư dài hạn', 'CĐKT. Lợi thế thương mại (trước 2015)',
        'CĐKT. Tài sản dài hạn khác', 'CĐKT.Lợi thế thương mại',
        'CĐKT. TỔNG CỘNG TÀI SẢN']
                        , var_name='Loại', value_name='Giá trị')

    # Sắp xếp lại dữ liệu theo năm
    df_melted.sort_values(by='Năm', inplace=True)

    # Sử dụng plotly.graph_objects để vẽ biểu đồ cột đôi
    fig = go.Figure()

    for i, loai in enumerate(df_melted['Loại'].unique()):
        fig.add_trace(go.Bar(
            x=df_melted[df_melted['Loại'] == loai]['Năm'],
            y=df_melted[df_melted['Loại'] == loai]['Giá trị'],
            name=loai
        ))
    fig.add_trace(go.Scatter(
        x=df_cdkto['Năm'],
        y=df_cdkto['Tiền/TTS'],
        mode='lines+markers',
        name='Tiền/TTS', yaxis='y2'))
    fig.update_layout(yaxis2=dict(anchor='x', overlaying='y', side='right'))

    # Cấu hình trực quan cho biểu đồ
    fig.update_layout(
        barmode='group',
        xaxis_tickmode='linear',
        xaxis_title='Năm',
        yaxis_title='Giá trị (tỷ đồng)',
        title='Cơ Cấu Tài Sản',
        updatemenus=[
            dict(
                active=0,
                buttons=list([
                    dict(label='Tăng', method='relayout', args=['barmode', 'stack']),
                    dict(label='Tăng cường', method='relayout', args=['barmode', 'group'])
                ]),
                direction='down',
                showactive=True,
                x=1.05,
                xanchor='left',
                y=1.2,
                yanchor='top'
            )
        ]
    )

    return fig
def plot_gross_profit_margin(data):
    data['Biên lợi nhuận gộp'] = data['KQKD. Lợi nhuận gộp về bán hàng và cung cấp dịch vụ']/data['KQKD. Doanh thu thuần']
    # Tạo biểu đồ cột cho Doanh thu thuần và Lợi nhuận gộp
    fig = go.Figure()

    # Biểu đồ cột cho Doanh thu thuần
    fig.add_trace(go.Bar(
        x=data['Năm'],
        y=data['KQKD. Doanh thu thuần'],
        name='Doanh thu thuần',
        marker=dict(color='rgb(180, 235, 253)')
    ))

    # Biểu đồ cột cho Lợi nhuận gộp
    fig.add_trace(go.Bar(
        x=data['Năm'],
        y=data['KQKD. Lợi nhuận gộp về bán hàng và cung cấp dịch vụ'],
        name='Lợi nhuận gộp',
        marker=dict(color='rgb(255, 204, 204)')
    ))

    # Biểu đồ đường cho Biên lợi nhuận gộp
    fig.add_trace(go.Scatter(
        x=data['Năm'],
        y=data['Biên lợi nhuận gộp'],
        name='Biên lợi nhuận gộp',
        mode='lines+markers',
        yaxis='y2',
        line=dict(color='rgb(50, 171, 96)')
    ))

    # Cập nhật layout của biểu đồ
    fig.update_layout(
        title='Doanh thu và Lợi nhuận gộp',
        xaxis=dict(title='Năm'),
        yaxis=dict(title='Số tiền (tỷ đồng)'),
        yaxis2=dict(
            title='Biên lợi nhuận gộp (%)',
            overlaying='y',
            side='right',
            showgrid=False
        )
    )

    return fig


def plot_profit_structure(data):
    # Tạo biểu đồ cột
    fig = go.Figure()

    # Thêm các cột vào biểu đồ
    fig.add_trace(go.Bar(
        x=data['Năm'],
        y=data['KQKD. Lợi nhuận gộp về bán hàng và cung cấp dịch vụ'],
        name='Lợi nhuận gộp',
        marker=dict(color='rgb(180, 235, 253)')
    ))

    fig.add_trace(go.Bar(
        x=data['Năm'],
        y=data['KQKD. Doanh thu hoạt động tài chính'],
        name='Lợi nhuận từ hoạt động tài chính',
        marker=dict(color='rgb(255, 204, 204)')
    ))

    fig.add_trace(go.Bar(
        x=data['Năm'],
        y=data['KQKD. Lợi nhuận khác'],
        name='Lợi nhuận khác',
        marker=dict(color='rgb(204, 255, 204)')
    ))

    fig.add_trace(go.Bar(
        x=data['Năm'],
        y=data['KQKD. Lợi nhuận sau thuế thu nhập doanh nghiệp'],
        name='Lợi nhuận sau thuế',
        marker=dict(color='rgb(255, 255, 204)')
    ))

    # Cập nhật layout của biểu đồ
    fig.update_layout(
        title='CƠ CẤU LỢI NHUẬN',
        xaxis=dict(title='Năm'),
        yaxis=dict(title='Lợi nhuận (tỷ đồng)'),
        yaxis2=dict(title='Tăng trưởng (%)', overlaying='y', side='right')
    )

    return fig


#3CAI NÀY OK HẾT
def plot_profit_after_tax(df):
    # Tạo biểu đồ tương tác
    fig = go.Figure()

    # Lặp qua từng cổ phiếu và thêm đường tượng trưng cho mỗi cổ phiếu
    for ma, data in df.groupby('MÃ'):
        fig.add_trace(go.Scatter(x=data['YEAR'], y=data['KQKD. LỢI NHUẬN SAU THUẾ THU NHẬP DOANH NGHIỆP'],
                                 mode='lines+markers', name=ma,
                                 marker=dict(size=8),
                                 hovertemplate='Năm: %{x}<br>Lợi nhuận sau thuế: %{y:.2f} tỷ đồng'))

    # Cập nhật layout cho biểu đồ
    fig.update_layout(title='SO SÁNH LỢI NHUẬN SAU THUẾ', xaxis=dict(title='Năm', tickmode='linear', tickformat='%Y'),
                      yaxis=dict(title='Lợi nhuận sau thuế'))
    # Hiển thị biểu đồ
    return fig
def plot_equity(df):
    # Tạo biểu đồ tương tác
    fig = go.Figure()

    # Lặp qua từng cổ phiếu và thêm đường tượng trưng cho mỗi cổ phiếu
    for ma, data in df.groupby('MÃ'):
        fig.add_trace(go.Scatter(x=data['YEAR'], y=data['CĐKT. VỐN CHỦ SỞ HỮU'], mode='lines+markers', name=ma,
                                 marker=dict(size=8),
                                 hovertemplate='Năm: %{x}<br>Vốn chủ sở hữu: %{y:.2f} tỷ đồng'))

    # Cập nhật layout cho biểu đồ
    fig.update_layout(title='SO SÁNH VỐN CHỦ SỞ HỮU', xaxis=dict(title='Năm', tickmode='linear', tickformat='%Y'),
                      yaxis=dict(title='Vốn chủ sở hữu'))

    # Hiển thị biểu đồ trên Streamlit
    return fig
def plot_revenue_comparison(dataframe):
    # Tạo biểu đồ tương tác
    fig = go.Figure()
    # Lặp qua từng cổ phiếu và thêm đường tượng trưng cho mỗi cổ phiếu
    for ma, data in dataframe.groupby('MÃ'):
        fig.add_trace(go.Bar(
            x=data['YEAR'],
            y=data['KQKD. DOANH THU THUẦN'],
            name=ma,
            hovertemplate='Năm: %{x}<br>Doanh thu thuần: %{y:.2f} tỷ đồng'
        ))

    # Cập nhật layout của biểu đồ
    fig.update_layout(
        title='So sánh Doanh thu thuần của các cổ phiếu trong ngành xây dựng',
        xaxis=dict(title='Năm'),
        yaxis=dict(title='Doanh thu thuần'),
        barmode='group',
        legend=dict(orientation='h', yanchor='top', y=-0.15)
    )

    # Hiển thị biểu đồ
    return fig

if __name__ == "__main__":
    main()

