import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def plotar_compras_com_volume(ticker, google_sheet_public_url, fig, ax, janela_dias=365):
    try:
        df_negociacoes = pd.read_csv(google_sheet_public_url)
        coluna_data = 'Data do Negócio'
        coluna_ticker = 'Código de Negociação'
        coluna_quantidade = 'Quantidade'
        
        df_negociacoes[coluna_ticker] = df_negociacoes[coluna_ticker].astype(str)
        filtro_ticker = df_negociacoes[coluna_ticker].str.contains(ticker.strip().upper())
        compras_ativo = df_negociacoes[filtro_ticker].copy()

        if compras_ativo.empty:
            st.warning(f"Nenhuma negociação encontrada para o ticker '{ticker}'.")
            return

        datas_compra = pd.to_datetime(compras_ativo[coluna_data], format='%d/%m/%Y').tolist()
        quantidades_compra = compras_ativo[coluna_quantidade].tolist()

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar a planilha: {e}")
        return

    ticker_sa = f"{ticker.upper()}.SA"
    inicio = min(datas_compra) - timedelta(days=janela_dias)
    fim = max(datas_compra) + timedelta(days=janela_dias)
    df_cotacoes = yf.download(ticker_sa, start=inicio.strftime("%Y-%m-%d"), end=fim.strftime("%Y-%m-%d"))

    if df_cotacoes.empty:
        st.warning(f"Não foram encontrados dados de cotação para '{ticker_sa}'.")
        return

    ax.plot(df_cotacoes.index, df_cotacoes['Close'], label=f'Cotação ({ticker_sa})', color='royalblue', linewidth=2, zorder=1)
    
    fator_tamanho = 5
    for data, quantidade in zip(datas_compra, quantidades_compra):
        data_str = data.strftime('%Y-%m-%d')
        if data_str in df_cotacoes.index:
            preco = df_cotacoes.loc[data_str]['Close']
            ax.scatter(data, preco, s=quantidade * fator_tamanho, color='red', edgecolor='black', alpha=0.7, zorder=5)

    min_q = min(quantidades_compra)
    max_q = max(quantidades_compra)
    s_min = "ação" if min_q == 1 else "ações"
    s_max = "ação" if max_q == 1 else "ações"

    ax.scatter([], [], s=min_q * fator_tamanho, color='red', edgecolor='black', alpha=0.7, label=f'Aporte Mínimo ({min_q} {s_min})')
    ax.scatter([], [], s=max_q * fator_tamanho, color='red', edgecolor='black', alpha=0.7, label=f'Aporte Máximo ({max_q} {s_max})')
    
    ax.set_title(f'Histórico de Cotações e Volume de Compras - {ticker_sa}', fontsize=16, weight='bold')
    ax.set_xlabel('Data', fontsize=12)
    ax.set_ylabel('Preço de Fechamento (R$)', fontsize=12)
    ax.legend(loc='upper left', fancybox=True, labelspacing=1.2)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

# --- Interface do App Streamlit ---
st.set_page_config(layout="wide")
st.title('Meu Dashboard de Análise de Aportes 📈')

# Campo para o usuário digitar o ticker
ticker_input = st.text_input('Digite o código da Ação (ex: BBAS3, PETR4, ISAE4):', 'BBAS3').upper()

# Campo para o usuário digitar o link para a planilha
planillha_input = st.text_input('Digite o link da planilha: ', placeholder= 'Link da planilha')

# Campo para o usuário digitar o tempo para análise
janela_input = st.number_input(
    'Digite a janela de tempo em dias que você quer analisar:',
    min_value=1,
    step=1,
    format="%d",
    value=365
)
# Botão para gerar a análise
if st.button('Analisar Ativo'):
    if ticker_input:
        # Cria a figura e os eixos do Matplotlib
        fig, ax = plt.subplots(figsize=(15, 8))
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Chama a função para plotar os dados na figura
        plotar_compras_com_volume(ticker_input, planillha_input, fig, ax, janela_input)
        
        # Exibe o gráfico no Streamlit
        st.pyplot(fig)
    else:
        st.warning('Por favor, digite o código de um ativo.')

st.sidebar.header('Sobre')
st.sidebar.info('Este é um dashboard interativo para visualizar o histórico de aportes em ações, criado com Python e Streamlit.')