import requests
import zipfile
import io
import pandas as pd
import re
import sqlite3
import os
from bs4 import BeautifulSoup

def encontrar_urls_disponiveis():
    """
    Acessa a página da CVM e encontra as URLs para TODOS os arquivos .zip de informes mensais.
    Esta versão é robusta e pega tanto os arquivos anuais quanto os mensais, se existirem.
    """
    print("Buscando todas as URLs de arquivos disponíveis no portal da CVM...")
    url_base = 'https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/'
    urls = []
    try:
        response = requests.get(url_base)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Padrão de regex que captura "..._2020.zip" e também "..._202101.zip"
        for link in soup.find_all('a', href=re.compile(r'inf_mensal_fii_20\d{2,6}\.zip')):
            urls.append(url_base + link.get('href'))
            
        if not urls:
            print("Nenhuma URL encontrada. O layout da página da CVM pode ter mudado.")
            return []
            
        print(f"{len(urls)} arquivos encontrados para processar.")
        return sorted(urls)
    except Exception as e:
        print(f"Erro ao tentar encontrar as URLs disponíveis: {e}")
        return []

def processar_um_arquivo_cvm(url):
    """
    Baixa e processa um único arquivo .zip da CVM, vindo de uma URL completa,
    e padroniza as colunas usando um mapa de sinônimos.
    """
    nome_do_arquivo_zip = url.split('/')[-1]
    print(f"\n--- Processando arquivo: {nome_do_arquivo_zip} ---")
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  -> Erro no download do arquivo: {e}")
        return None

    try:
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        lista_dfs = []
        for nome_arquivo_csv in zip_file.namelist():
            if 'complemento' in nome_arquivo_csv:
                with zip_file.open(nome_arquivo_csv, 'r') as csv_file:
                    df_mensal = pd.read_csv(csv_file, sep=';', encoding='latin-1')
                    
                    # --- HIGIENIZAÇÃO E PADRONIZAÇÃO DAS COLUNAS ---
                    df_mensal.columns = df_mensal.columns.str.lower()
                    
                    # --- MAPA DE RENOMEAÇÃO DEFINITIVO ---
                    # Inclui todas as variações de nomes de coluna que encontramos.
                    mapa_renomeacao_final = {
                        'cnpj_fundo': 'cnpj',
                        'cnpj_fundo_classe': 'cnpj',  # A correção para anos pós-2020
                        'data_referencia': 'data_comptc',
                        'patrimonio_liquido': 'valor_patrim_liq',
                        'cotas_emitidas': 'qt_cotas',
                        'dt_comptc': 'data_comptc', # Mantém por segurança
                        'vl_patrimonio_liquido': 'valor_patrim_liq',
                        'vl_patrim_liq': 'valor_patrim_liq',
                        'nr_cotas': 'qt_cotas'
                    }
                    df_mensal.rename(columns=mapa_renomeacao_final, inplace=True)
                    
                    if 'cnpj' in df_mensal.columns:
                        df_mensal['cnpj'] = df_mensal['cnpj'].astype(str).str.replace(r'\D', '', regex=True)

                    lista_dfs.append(df_mensal)
        
        if not lista_dfs: return None
        return pd.concat(lista_dfs, ignore_index=True)
    except Exception as e:
        print(f"  -> Erro ao processar o arquivo zip: {e}")
        return None

def criar_banco_de_dados_vpa_completo():
    """
    Orquestra todo o processo com a nova lógica de busca e padronização corrigida.
    """
    urls_dos_arquivos = encontrar_urls_disponiveis()
    if not urls_dos_arquivos:
        print("Pipeline interrompido.")
        return

    lista_completa_dfs = []
    for url in urls_dos_arquivos:
        df_processado = processar_um_arquivo_cvm(url)
        if df_processado is not None and not df_processado.empty:
            lista_completa_dfs.append(df_processado)

    if not lista_completa_dfs:
        print("Pipeline interrompido: nenhum dado foi processado com sucesso.")
        return

    print("\n--- Consolidando todos os arquivos em um único DataFrame ---")
    df_master = pd.concat(lista_completa_dfs, ignore_index=True)
    
    print("Iniciando limpeza e transformação dos dados consolidados...")
    colunas_essenciais = ['cnpj', 'data_comptc', 'valor_patrim_liq', 'qt_cotas']
    for col in colunas_essenciais:
        if col not in df_master.columns:
            print(f"ERRO CRÍTICO: A coluna padronizada '{col}' não foi encontrada.")
            return

    df_master['data_comptc'] = pd.to_datetime(df_master['data_comptc'])
    numeric_cols = ['valor_patrim_liq', 'qt_cotas']
    for col in numeric_cols:
        df_master[col] = pd.to_numeric(df_master[col], errors='coerce')

    df_master.dropna(subset=numeric_cols, inplace=True)
    df_master = df_master[df_master['qt_cotas'] > 0]
    df_master['vpa'] = df_master['valor_patrim_liq'] / df_master['qt_cotas']
    df_final = df_master[['cnpj', 'data_comptc', 'vpa']].copy()
    df_final.sort_values(by=['cnpj', 'data_comptc'], inplace=True)
    
    print("Limpeza finalizada. Dados prontos para serem salvos.")
    
    # Garante que a pasta 'database' exista
    if not os.path.exists('database'):
        os.makedirs('database')

    nome_banco = 'database/dados_fii.db'
    nome_tabela = 'vpa_historico'
    try:
        conn = sqlite3.connect(nome_banco)
        df_final.to_sql(nome_tabela, conn, if_exists='replace', index=False)
        conn.close()
        print(f"\nSUCESSO! O banco de dados '{nome_banco}' foi criado/atualizado com a tabela '{nome_tabela}'.")
        print(f"Total de registros salvos: {len(df_final)}")
    except Exception as e:
        print(f"Erro ao salvar os dados no banco SQLite: {e}")
    return df_final

# --- Ponto de partida para executar o script ---
if __name__ == "__main__":
    df_final_vpa = criar_banco_de_dados_vpa_completo()
    if df_final_vpa is not None:
        print("\n--- Amostra dos Dados Finais Salvos (ordenados pelos mais recentes) ---")
        print(df_final_vpa.sort_values('data_comptc', ascending=False).head())