import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import timedelta

# --- FUNÇÃO DE PLOTAGEM (AJUSTADA E ROBUSTA) ---
def plotar_grafico_aportes(ticker, df_aportes_filtrado, fig, ax, janela_dias=365):
    try:
        coluna_data = 'Data do Negócio'
        coluna_quantidade = 'Quantidade'
        datas_compra = pd.to_datetime(df_aportes_filtrado[coluna_data], format='%d/%m/%Y')
        quantidades_compra = df_aportes_filtrado[coluna_quantidade].tolist()
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os dados do ticker: {e}")
        return

    ticker_sa = f"{ticker.upper()}.SA"
    inicio = min(datas_compra) - timedelta(days=janela_dias + 5)
    fim = max(datas_compra) + timedelta(days=janela_dias + 5)
    df_cotacoes = yf.download(ticker_sa, start=inicio.strftime("%Y-%m-%d"), end=fim.strftime("%Y-%m-%d"), progress=False)

    if df_cotacoes.empty:
        st.warning(f"Não foram encontrados dados de cotação para '{ticker_sa}' no Yahoo Finance.")
        return

    ax.plot(df_cotacoes.index, df_cotacoes['Close'], label=f'Cotação ({ticker_sa})', color='royalblue', linewidth=2, zorder=1)
    
    fator_tamanho = 5
    for data, quantidade in zip(datas_compra, quantidades_compra):
        try:
            data_ajustada = df_cotacoes.index.asof(data)
            preco_no_dia = df_cotacoes.loc[data_ajustada]['Close']
            ax.scatter(data_ajustada, preco_no_dia, s=quantidade * fator_tamanho, color='red', edgecolor='black', alpha=0.7, zorder=5)
        except (KeyError, IndexError, TypeError):
            pass

    min_q = min(quantidades_compra) if quantidades_compra else 0
    max_q = max(quantidades_compra) if quantidades_compra else 0
    s_min = "unidade" if min_q == 1 else "unidades"
    s_max = "unidade" if max_q == 1 else "unidades"
    ax.scatter([], [], s=min_q * fator_tamanho, color='red', edgecolor='black', alpha=0.7, label=f'Aporte Mín. ({min_q} {s_min})')
    ax.scatter([], [], s=max_q * fator_tamanho, color='red', edgecolor='black', alpha=0.7, label=f'Aporte Máx. ({max_q} {s_max})')
    
    ax.set_title(f'Histórico de Cotações e Volume de Compras - {ticker_sa}', fontsize=16, weight='bold')
    ax.set_xlabel('Data', fontsize=12)
    ax.set_ylabel('Preço de Fechamento (R$)', fontsize=12)
    ax.legend(loc='upper left', fancybox=True, labelspacing=1.2)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

# --- LÓGICA DE NAVEGAÇÃO INTERNA DA PÁGINA ---
if 'pagina_aportes' not in st.session_state:
    st.session_state.pagina_aportes = 'upload'

def carregar_e_validar():
    arquivo_carregado = st.session_state.get('uploader_aportes', None)
    if arquivo_carregado:
        if 'movimentacao' in arquivo_carregado.name.lower():
            st.error("❌ **Arquivo Incorreto!** Você carregou a planilha de **movimentações**. Por favor, acesse a aba **Negociação** no portal da B3.")
            return
        try:
            with st.spinner('Carregando e validando sua planilha...'):
                df = pd.read_excel(arquivo_carregado)
                coluna_movimentacao = 'Tipo de Movimentação'
                coluna_ticker = 'Código de Negociação'
                coluna_preco = 'Preço'
                
                if coluna_movimentacao not in df.columns:
                    st.error(f"A coluna '{coluna_movimentacao}' não foi encontrada. Verifique se a planilha é a de 'Negociação' da B3.")
                    return
                
                df_compras = df[df[coluna_movimentacao] == 'Compra'].copy()
                if df_compras.empty:
                    st.warning("A planilha carregada não contém nenhuma operação de 'Compra'.")
                    return
                
                df_compras[coluna_preco] = pd.to_numeric(df_compras[coluna_preco].astype(str).str.replace('R$', '', regex=False).str.strip().str.replace(',', '.', regex=False), errors='coerce')
                df_compras.dropna(subset=[coluna_preco], inplace=True)
                
                df_compras[coluna_ticker] = df_compras[coluna_ticker].astype(str).str.strip().str.upper().str.replace('F$', '', regex=True)
                df_compras[coluna_ticker] = df_compras[coluna_ticker].str.replace('TRPL4', 'ISAE4', regex=True)
                df_compras[coluna_ticker] = df_compras[coluna_ticker].str.replace('TRPL3', 'ISAE3', regex=True)
                
                st.session_state.df_negociacoes = df_compras
                st.session_state.pagina_aportes = 'analise'
        except Exception as e:
            st.error(f"Não foi possível processar a planilha. Verifique o arquivo. Erro: {e}")
    else:
        st.warning("Por favor, carregue um arquivo para continuar.")

def voltar_para_upload():
    # Limpa os dados da sessão ao voltar
    for key in ['df_negociacoes', 'pagina_aportes', 'uploader_aportes']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.pagina_aportes = 'upload'

# --- RENDERIZAÇÃO DA PÁGINA DE APORTES ---

st.title("📊 Análise de Aportes")

# ETAPA 1: UPLOAD
if st.session_state.pagina_aportes == 'upload':
    st.header('Passo 1: Carregue sua Planilha de Negociação')
    st.markdown("Use o arquivo **.xlsx** de **negociações** obtido no Portal do Investidor da B3.")

    # Inserido o passo a passo que você queria
    with st.expander("Precisa de ajuda para obter o arquivo? Clique aqui."):
        st.markdown("""
        1.  **🔑 Acesse o Portal do Investidor B3** ([https://www.investidor.b3.com.br](https://www.investidor.b3.com.br))
        2.  **📜 Encontre seu Extrato de Negociações:** No menu, navegue por **Extratos > Negociação**. (⚠️ Não use a aba "Movimentação"!)
        3.  **📅 Filtre o Período Completo:** Para uma análise completa, filtre desde o seu primeiro investimento.
        4.  **📥 Baixe a Planilha:** Clique no ícone de **Download** (⬇️) para baixar o arquivo em formato Excel (`.xlsx`).
        """)

    st.file_uploader(
        "**Arraste o arquivo da B3 para cá ou clique para procurar**",
        type=['xlsx'],
        key='uploader_aportes',
        label_visibility='visible'
    )
    st.button('Analisar Planilha', on_click=carregar_e_validar, type="primary")

# ETAPA 2: ANÁLISE
elif st.session_state.pagina_aportes == 'analise':
    st.header('Passo 2: Escolha o Ativo para Análise')
    df_completo = st.session_state.df_negociacoes
    coluna_ticker = 'Código de Negociação'

    try:
        # Lógica de ordenação dos tickers reintroduzida
        tickers_unicos = df_completo[coluna_ticker].unique().tolist()
        outros_ativos = [ticker for ticker in tickers_unicos if not ticker.endswith('11')]
        ativos_com_final_11 = [ticker for ticker in tickers_unicos if ticker.endswith('11')]
        lista_ordenada = sorted(outros_ativos) + sorted(ativos_com_final_11)
    except KeyError:
        st.error(f"A coluna '{coluna_ticker}' não foi encontrada na sua planilha.")
        st.button('Voltar', on_click=voltar_para_upload)
        st.stop()

    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        ticker_selecionado = st.selectbox('Selecione o Ativo:', options=lista_ordenada)
    with col2:
        janela_input = st.number_input('Janela de tempo (dias):', min_value=30, step=30, format="%d", value=365)
    
    # Botão para gerar o gráfico
    if st.button('Gerar Gráfico', type="primary"):
        if ticker_selecionado:
            with st.spinner(f'Buscando dados de {ticker_selecionado} e gerando o gráfico...'):
                filtro_ticker = df_completo[coluna_ticker] == ticker_selecionado
                df_filtrado = df_completo[filtro_ticker]
                fig, ax = plt.subplots(figsize=(15, 8))
                plt.style.use('seaborn-v0_8-darkgrid')
                plotar_grafico_aportes(ticker_selecionado, df_filtrado, fig, ax, janela_input)
                st.pyplot(fig)
        else:
            st.warning('Por favor, selecione um ativo da lista.')
            
    st.button('Carregar Outra Planilha', on_click=voltar_para_upload)