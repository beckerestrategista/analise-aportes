import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# A sua função de plotagem permanece a mesma, sem alterações.
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


# --- LÓGICA DE NAVEGAÇÃO E INTERFACE DO APP ---

st.set_page_config(layout="wide")

# Inicializa a "memória" da sessão para saber em qual página estamos.
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'home'

# Função para mudar para a página de análise
def navegar_para_analise():
    # Salva o link da planilha na memória antes de mudar de página
    if st.session_state.url_input_field and "docs.google.com" in st.session_state.url_input_field:
        st.session_state.link_da_planilha = st.session_state.url_input_field
        st.session_state.pagina_atual = 'analise'
    else:
        st.warning("Por favor, insira um link válido do Google Sheets.")

# Função para voltar para a página inicial
def navegar_para_home():
    st.session_state.pagina_atual = 'home'

# --- RENDERIZAÇÃO DA PÁGINA ---

# PÁGINA 1: TELA INICIAL
if st.session_state.pagina_atual == 'home':
    st.title('Meu Dashboard de Análise de Aportes 📈')
    st.header('Passo 1: Conecte sua Planilha')
    
    st.text_input(
        'Insira o link PÚBLICO da sua planilha Google Sheets (formato .csv):',
        key='url_input_field', # Chave para acessar o valor na memória
        placeholder='https://docs.google.com/spreadsheets/d/e/seu-link-aqui/pub?output=csv'
    )
    
    st.button('Avançar para Análise', on_click=navegar_para_analise)

# PÁGINA 2: TELA DE ANÁLISE
elif st.session_state.pagina_atual == 'analise':
    st.title('Análise de Ativo Individual 📊')
    st.info(f"Analisando dados da planilha: {st.session_state.link_da_planilha}")
    st.header('Passo 2: Escolha o Ativo e a Janela de Tempo')

    # Cria duas colunas para organizar os campos de input
    col1, col2 = st.columns(2)

    with col1:
        ticker_input = st.text_input('Digite o código da Ação (ex: BBAS3, PETR4):', 'BBAS3').upper()
    
    with col2:
        janela_input = st.number_input(
            'Janela de tempo em dias:',
            min_value=30, step=30, format="%d", value=365
        )
    
    # Botão para gerar a análise
    if st.button('Analisar Ativo'):
        if ticker_input:
            # Usa um spinner para dar um feedback visual enquanto os dados carregam
            with st.spinner(f'Buscando dados de {ticker_input} e gerando o gráfico...'):
                fig, ax = plt.subplots(figsize=(15, 8))
                plt.style.use('seaborn-v0_8-darkgrid')
                plotar_compras_com_volume(ticker_input, st.session_state.link_da_planilha, fig, ax, janela_input)
                st.pyplot(fig)
        else:
            st.warning('Por favor, digite o código de um ativo.')
            
    st.button('Voltar e inserir outra planilhla', on_click=navegar_para_home)