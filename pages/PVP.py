import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import sqlite3

# --- FUNÇÕES DE LÓGICA E PLOTAGEM ---

@st.cache_data
def carregar_dados_db():
    """
    Conecta ao banco de dados SQLite e carrega as tabelas de VPA e cadastro.
    """
    try:
        conn = sqlite3.connect('database/dados_fii.db')
        df_vpa = pd.read_sql_query("SELECT * FROM vpa_historico", conn)
        df_cadastro = pd.read_sql_query("SELECT * FROM cadastro_fiis", conn)
        conn.close()
        
        df_vpa['data_comptc'] = pd.to_datetime(df_vpa['data_comptc'])
        return df_vpa, df_cadastro
    except Exception as e:
        st.error(f"Erro ao carregar o banco de dados 'dados_fii.db'.")
        st.error(f"Verifique se o arquivo existe na pasta 'database' e se os scripts de geração foram executados. Erro: {e}")
        return None, None

def plotar_pvp_por_ticker(ticker, df_vpa, df_cadastro, janela_anos=5):
    """
    Função final que busca os dados e retorna DUAS figuras Plotly: 
    1. P/VP histórico.
    2. Preço de Mercado vs. VPA.
    """
    ticker_upper = ticker.upper()
    
    df_fii_selecionado = df_cadastro[df_cadastro['ticker'] == ticker_upper]
    if df_fii_selecionado.empty:
        st.error(f"Ticker '{ticker_upper}' não encontrado na sua tabela de cadastro.")
        return None, None
    cnpj_do_fii = df_fii_selecionado['cnpj'].iloc[0]
    
    df_vp_do_fii = df_vpa[df_vpa['cnpj'] == cnpj_do_fii].copy()
    if df_vp_do_fii.empty:
        st.warning(f"Não foram encontrados dados de VPA para {ticker_upper} no banco de dados.")
        return None, None

    ticker_sa = f"{ticker_upper}.SA"
    hoje = datetime.now()
    data_inicial = hoje - pd.DateOffset(years=janela_anos)
    try:
        df_precos = yf.download(ticker_sa, start=data_inicial, end=hoje, progress=False)['Close'].squeeze().reset_index()
        df_precos.columns = ['data', 'preco_fechamento']
        if df_precos.empty: raise ValueError("Download do yfinance retornou vazio.")
    except Exception as e:
        st.error(f"Falha ao baixar os dados de preço para {ticker_sa} no Yahoo Finance. Detalhe: {e}")
        return None, None

    df_precos['data'] = pd.to_datetime(df_precos['data']).dt.tz_localize(None)
    df_vp_do_fii.rename(columns={'data_comptc': 'data'}, inplace=True)
    df_vp_do_fii['data'] = pd.to_datetime(df_vp_do_fii['data'])
    
    df_combinado = pd.merge_asof(df_precos.sort_values('data'), df_vp_do_fii.sort_values('data'), on='data', direction='backward').dropna()

    if df_combinado.empty:
        st.warning("Não foi possível combinar os dados de preço e VPA para gerar o gráfico.")
        return None, None

    df_combinado['P/VP'] = df_combinado['preco_fechamento'] / df_combinado['vpa']
    
    # --- GRÁFICO 1: P/VP Histórico (sem alterações) ---
    fig_pvp = go.Figure()
    fig_pvp.add_trace(go.Scatter(
        x=df_combinado['data'], y=df_combinado['P/VP'], mode='lines',
        name='P/VP Histórico', line=dict(color='darkgreen'),
        hovertemplate='<b>Data:</b> %{x|%d/%m/%Y}<br><b>P/VP:</b> %{y:.2f}<extra></extra>'
    ))
    fig_pvp.add_hline(y=1.0, line_width=2, line_dash="dash", line_color="red",
                      annotation_text="P/VP = 1.0", annotation_position="bottom right")
    media_pvp = df_combinado['P/VP'].mean()
    fig_pvp.update_layout(
        title=f'<b>Histórico de P/VP para {ticker.upper()}</b><br><sup>Média no período: {media_pvp:.2f}</sup>',
        xaxis_title='Data', yaxis_title='Índice P/VP', template='plotly_white'
    )

    # --- GRÁFICO 2: Preço de Mercado vs. VPA (NOVO) ---
    fig_preco_vpa = go.Figure()
    fig_preco_vpa.add_trace(go.Scatter(
        x=df_combinado['data'], y=df_combinado['preco_fechamento'], name='Preço de Mercado',
        line=dict(color='royalblue'), hovertemplate='<b>Preço:</b> R$ %{y:,.2f}<extra></extra>'
    ))
    fig_preco_vpa.add_trace(go.Scatter(
        x=df_combinado['data'], y=df_combinado['vpa'], name='Valor Patrimonial (VPA)',
        line=dict(color='darkorange', dash='dot'), hovertemplate='<b>VPA:</b> R$ %{y:,.2f}<extra></extra>'
    ))
    fig_preco_vpa.update_layout(
        title=f'<b>Preço de Mercado vs. Valor Patrimonial para {ticker.upper()}</b>',
        xaxis_title='Data', yaxis_title='Valor (R$)', template='plotly_white',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    # Retorna as duas figuras
    return fig_pvp, fig_preco_vpa

# --- Interface da Página ---
st.set_page_config(page_title="Análise P/VP", page_icon="📈", layout="wide")
st.title("📈 Análise P/VP Histórico")
st.markdown("Explore o indicador Preço/Valor Patrimonial (P/VP) para Fundos Imobiliários.")
df_vpa, df_cadastro = carregar_dados_db()

if df_cadastro is not None and not df_cadastro.empty:
    st.header("Selecione o Ativo e o Período")
    try:
        lista_ordenada = sorted(df_cadastro['ticker'].unique().tolist())
    except KeyError:
        st.error("A coluna 'ticker' não foi encontrada na sua tabela de cadastro.")
        st.stop()

    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        ticker_selecionado = st.selectbox("Selecione o Fundo Imobiliário:", lista_ordenada)
    with col2:
        # Janela de tempo mantida com o padrão de 5 anos
        janela_input = st.number_input('Analisar últimos (anos):', min_value=1, max_value=20, step=1, value=5)

    if st.button('Gerar Gráfico de P/VP', type="primary"):
        if ticker_selecionado:
            with st.spinner(f"Gerando análise para {ticker_selecionado}..."):
                # --- ALTERAÇÃO AQUI: Recebe as duas figuras ---
                figura_pvp, figura_preco_vpa = plotar_pvp_por_ticker(ticker_selecionado, df_vpa, df_cadastro, janela_input)
                
                # Exibe as duas figuras, se elas foram criadas com sucesso
                if figura_pvp and figura_preco_vpa:
                    st.subheader("Gráfico de Preço / Valor Patrimonial (P/VP)")
                    st.plotly_chart(figura_pvp, use_container_width=True)
                    
                    st.divider() # Adiciona uma linha divisória

                    st.subheader("Comparativo: Preço de Mercado vs. VPA")
                    st.plotly_chart(figura_preco_vpa, use_container_width=True)
        else:
            st.warning('Por favor, selecione um ativo da lista.')