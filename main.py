import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# A função de plotagem não precisa de nenhuma alteração.
def plotar_grafico_aportes(ticker, df_aportes_filtrado, fig, ax, janela_dias=365):
  try:
    coluna_data = 'Data do Negócio'
    coluna_quantidade = 'Quantidade'
    datas_compra = pd.to_datetime(df_aportes_filtrado[coluna_data], format='%d/%m/%Y').tolist()
    quantidades_compra = df_aportes_filtrado[coluna_quantidade].tolist()
  except Exception as e:
    st.error(f"Ocorreu um erro ao processar os dados do ticker: {e}")
    return

  ticker_sa = f"{ticker.upper()}.SA"
  inicio = min(datas_compra) - timedelta(days=janela_dias)
  fim = max(datas_compra) + timedelta(days=janela_dias)
  df_cotacoes = yf.download(ticker_sa, start=inicio.strftime("%Y-%m-%d"), end=fim.strftime("%Y-%m-%d"))

  if df_cotacoes.empty:
    st.warning(f"Não foram encontrados dados de cotação para '{ticker_sa}' no Yahoo Finance.")
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
st.set_page_config(layout="wide", page_title="Dashboard de Aportes")

if 'pagina_atual' not in st.session_state:
  st.session_state.pagina_atual = 'home'

def carregar_e_navegar():
  arquivo_carregado = st.session_state.file_uploader_widget
  if arquivo_carregado:
    try:
      with st.spinner('Carregando e validando sua planilha...'):
        df = pd.read_excel(arquivo_carregado)
        coluna_ticker = 'Código de Negociação'
        df[coluna_ticker] = df[coluna_ticker].astype(str).str.strip().str.upper()
        df[coluna_ticker] = df[coluna_ticker].str.replace('F$', '', regex=True)
        st.session_state.df_negociacoes = df
        st.session_state.pagina_atual = 'analise'
    except Exception as e:
      st.error(f"Não foi possível carregar a planilha. Verifique o link e as permissões. Erro: {e}")
  else:
    st.warning("Por favor, insira um link válido do Google Sheets.")

def navegar_para_home():
  for key in ['df_negociacoes', 'pagina_atual']:
    if key in st.session_state:
      del st.session_state[key]
  st.session_state.pagina_atual = 'home'

# --- RENDERIZAÇÃO DAS PÁGINAS ---
if st.session_state.pagina_atual == 'home':
  st.title('Meu Dashboard de Análise de Aportes 📈')
  st.header('Passo 1: Carregue sua Planilha')
  st.markdown("Insira o arquivo de histórico de aportes no formato **.xlsx** obtido pelo Portal do Investidor da B3.")
  
# --- GUIA PASSO A PASSO APRIMORADO ---
  with st.expander("Precisa de ajuda para obter o arquivo? Clique aqui para ver o passo a passo."):
        st.markdown("""
        1.  **🔑 Acesse o Portal do Investidor B3**
            -   Faça seu login no site oficial: [https://www.investidor.b3.com.br](https://www.investidor.b3.com.br)

        2.  **📜 Encontre seu Extrato de Negociações**
            -   No menu lateral, navegue por **Extratos > Negociação**.

        3.  **📅 Filtre o Período Completo**
            -   Use os filtros para selecionar o intervalo de datas que deseja analisar.
            -   *Dica: Para uma visão completa, filtre desde a data do seu primeiro investimento.*

        4.  **📥 Baixe a Planilha de Negociações**
            -   Clique no ícone de **Download** (uma seta para baixo) para baixar o arquivo em formato Excel (`.xlsx`).
            -   Atente-se para baixar a planilha completa clicando em "Ver detalhe".
        """)
  
  st.file_uploader(
        "**Arraste o arquivo da B3 para cá ou clique para procurar**",
        type=['xlsx'],
        key='file_uploader_widget',
        label_visibility='visible' # Garante que o rótulo sempre apareça
    )
  
  st.button('Carregar Planilha e Avançar', on_click=carregar_e_navegar, type="primary")

elif st.session_state.pagina_atual == 'analise' and 'df_negociacoes' in st.session_state:
  st.title('Análise de Ativo Individual 📊')
  st.header('Passo 2: Escolha o Ativo e a Janela de Tempo')

  df_completo = st.session_state.df_negociacoes
  coluna_ticker = 'Código de Negociação'

  try:
    # --- MUDANÇA PRINCIPAL: ORDENAÇÃO PERSONALIZADA DA LISTA ---
    # 1. Pega a lista de tickers únicos da planilha já carregada e limpa
    tickers_unicos = df_completo[coluna_ticker].unique().tolist()
    
    # 2. Separa os ativos em dois grupos
    outros_ativos = [ticker for ticker in tickers_unicos if not ticker.endswith('11')]
    ativos_com_final_11 = [ticker for ticker in tickers_unicos if ticker.endswith('11')]

    # 3. Ordena cada grupo alfabeticamente e junta as listas
    lista_ordenada = sorted(outros_ativos) + sorted(ativos_com_final_11)

  except KeyError:
    st.error(f"A coluna '{coluna_ticker}' não foi encontrada na sua planilha. Verifique o nome da coluna.")
    st.button('Voltar', on_click=navegar_para_home)
    st.stop()

  col1, col2 = st.columns([0.7, 0.3])

  with col1:
    # Usa a nova lista ordenada para popular o selectbox
    ticker_selecionado = st.selectbox('Selecione o Ativo para Análise:', options=lista_ordenada)
  
  with col2:
    janela_input = st.number_input(
      'Janela de tempo (dias):',
      min_value=30, step=30, format="%d", value=365
    )
  
  if st.button('Analisar Ativo', type="primary"):
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
      
  st.button('Voltar e usar outra planilha', on_click=navegar_para_home)
