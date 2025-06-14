import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import timedelta

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
    # Adicionado um buffer para garantir que a janela não quebre se não houver cotação no dia exato
    inicio = min(datas_compra) - timedelta(days=janela_dias + 5)
    fim = max(datas_compra) + timedelta(days=janela_dias + 5)
    df_cotacoes = yf.download(ticker_sa, start=inicio.strftime("%Y-%m-%d"), end=fim.strftime("%Y-%m-%d"))

    if df_cotacoes.empty:
        st.warning(f"Não foram encontrados dados de cotação para '{ticker_sa}' no Yahoo Finance.")
        return

    ax.plot(df_cotacoes.index, df_cotacoes['Close'], label=f'Cotação ({ticker_sa})', color='royalblue', linewidth=2, zorder=1)

    fator_tamanho = 5
    for data, quantidade in zip(datas_compra, quantidades_compra):
        # Busca a data mais próxima no índice de cotações caso a data exata não exista
        try:
            data_ajustada = df_cotacoes.index.asof(data)
            preco = df_cotacoes.loc[data_ajustada]['Close']
            ax.scatter(data, preco, s=quantidade * fator_tamanho, color='red', edgecolor='black', alpha=0.7, zorder=5)
        except (KeyError, IndexError):
            # Ignora o aporte se não encontrar cotação próxima (ex: feriados)
            pass

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
        # Verifica se o nome do arquivo contém "movimentacao".
        if 'movimentacao' in arquivo_carregado.name.lower():
            st.error(
                "❌ **Arquivo Incorreto!** "
                "Você carregou a planilha de **movimentações**. "
                "Por favor, acesse a aba **Negociação** no portal da B3 para baixar o arquivo correto."
            )
            return

        try:
            with st.spinner('Carregando e validando sua planilha...'):
                df = pd.read_excel(arquivo_carregado)
                coluna_ticker = 'Código de Negociação'
                coluna_movimentacao = 'Tipo de Movimentação'

                # Verifica se a coluna de movimentação existe
                if coluna_movimentacao not in df.columns:
                    st.error(f"A coluna '{coluna_movimentacao}' não foi encontrada. Verifique se a planilha é a de 'Negociação' da B3.")
                    return
                
                # Filtra o DataFrame para manter apenas as linhas de "Compra"
                df_compras = df[df[coluna_movimentacao] == 'Compra'].copy()

                # Verifica se restou algum dado após o filtro
                if df_compras.empty:
                    st.warning("A planilha carregada não contém nenhuma operação de 'Compra'.")
                    return
                
                # Continua o processamento com o DataFrame já filtrado
                df_compras[coluna_ticker] = df_compras[coluna_ticker].astype(str).str.strip().str.upper()
                df_compras[coluna_ticker] = df_compras[coluna_ticker].str.replace('F$', '', regex=True)
                
                # Trata ticker que mudou de nome
                df_compras[coluna_ticker] = df_compras[coluna_ticker].str.replace('TRPL4', 'ISAE4', regex=True)
                df_compras[coluna_ticker] = df_compras[coluna_ticker].str.replace('TRPL3', 'ISAE3', regex=True)
                
                st.session_state.df_negociacoes = df_compras
                st.session_state.pagina_atual = 'analise'

        except Exception as e:
            st.error(f"Não foi possível processar a planilha. Verifique o arquivo. Erro: {e}")
    else:
        st.warning("Por favor, carregue um arquivo para continuar.")

def navegar_para_home():
    for key in ['df_negociacoes', 'pagina_atual']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.pagina_atual = 'home'

# --- RENDERIZAÇÃO DAS PÁGINAS ---
if st.session_state.pagina_atual == 'home':
    st.title('Dashboard de Análise de Aportes 📈')
    st.header('Passo 1: Carregue sua Planilha de Negociação')
    st.markdown("Use o arquivo **.xlsx** de **negociações** obtido no Portal do Investidor da B3.")

    with st.expander("Precisa de ajuda para obter o arquivo? Clique aqui para ver o passo a passo."):
        st.markdown("""
        1.  **🔑 Acesse o Portal do Investidor B3**
            -   Faça seu login no site oficial: [https://www.investidor.b3.com.br](https://www.investidor.b3.com.br)

        2.  **📜 Encontre seu Extrato de Negociações**
            -   No menu lateral, navegue por **Extratos > Negociação**.
            -   ⚠️ **Atenção:** Não utilize o extrato de "Movimentação".

        3.  **📅 Filtre o Período Completo**
            -   Use os filtros para selecionar o intervalo de datas que deseja analisar.
            -   *Dica: Para uma visão completa, filtre desde a data do seu primeiro investimento.*

        4.  **📥 Baixe a Planilha Correta**
            -   Clique no ícone de **Download** (⬇️) para baixar o arquivo em formato Excel (`.xlsx`).
        """)

    st.file_uploader(
        "**Arraste o arquivo da B3 para cá ou clique para procurar**",
        type=['xlsx'],
        key='file_uploader_widget',
        label_visibility='visible'
    )

    st.button('Analisar Planilha', on_click=carregar_e_navegar, type="primary")

elif st.session_state.pagina_atual == 'analise' and 'df_negociacoes' in st.session_state:
    st.title('Análise de Ativo Individual 📊')
    st.header('Passo 2: Escolha o Ativo e a Janela de Tempo')

    df_completo = st.session_state.df_negociacoes
    coluna_ticker = 'Código de Negociação'

    try:
        tickers_unicos = df_completo[coluna_ticker].unique().tolist()
        outros_ativos = [ticker for ticker in tickers_unicos if not ticker.endswith('11')]
        ativos_com_final_11 = [ticker for ticker in tickers_unicos if ticker.endswith('11')]
        lista_ordenada = sorted(outros_ativos) + sorted(ativos_com_final_11)
    except KeyError:
        st.error(f"A coluna '{coluna_ticker}' não foi encontrada na sua planilha. Verifique o nome da coluna.")
        st.button('Voltar', on_click=navegar_para_home)
        st.stop()

    col1, col2 = st.columns([0.7, 0.3])

    with col1:
        ticker_selecionado = st.selectbox('Selecione o Ativo para Análise:', options=lista_ordenada)

    with col2:
        janela_input = st.number_input(
            'Janela de tempo (dias):',
            min_value=30, step=30, format="%d", value=365
        )

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
            
    st.button('Voltar e carregar outra planilha', on_click=navegar_para_home)