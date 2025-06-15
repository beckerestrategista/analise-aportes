import streamlit as st

st.set_page_config(
    page_title="Dashboard de Análise de FIIs",
    page_icon="📈",
    layout="wide"
)

st.title("Bem-vindo ao seu Dashboard de Análise de Investimentos 📈")

st.markdown("""
Esta aplicação foi desenvolvida para ajudar na visualização e análise de seus investimentos.

**Use o menu na barra lateral à esquerda para navegar entre as diferentes análises disponíveis:**

- **Análise de Aportes:** Faça o upload da sua planilha de negociações da B3 para visualizar suas compras em um gráfico de cotações.
- **Análise P/VP Histórico:** Explore o histórico do indicador Preço / Valor Patrimonial para qualquer FII.

---
""")

st.info("Para começar, selecione uma das páginas no menu lateral.", icon="👈")