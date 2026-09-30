import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configurações iniciais da página
st.set_page_config(page_title="Sistema de Pedidos de Peças", page_icon="⚙️", layout="centered")

# ================== ADICIONE OS NÚMEROS AQUI ==================
GID_LISTA_PECAS = 0          # <-- APAGUE o 0 e coloque o número da aba 'Lista Peças'
GID_PEDIDOS = 880479633       # <-- APAGUE o 12345678 e coloque o número da aba 'Pedidos em Andamento'
SENHA_ADMIN = "admin123"     # Sua senha de administrador
# ==============================================================

# Inicializa a conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para ler os dados usando IDs numéricos (GIDs), evitando erros de espaço/caractere
def carregar_dados():
    # Monta o link base do secrets
    url_base = st.secrets["connections"]["gsheets"]["spreadsheet"].split("/edit")[0]
    
    try:
        # Força a leitura exata do catálogo por ID numérico
        url_estoque = f"{url_base}/export?format=csv&gid={GID_LISTA_PECAS}"
        estoque = pd.read_csv(url_estoque)
    except Exception as e:
        st.error(f"Erro ao ler catálogo por GID: {str(e)}")
        estoque = pd.DataFrame(columns=["Código", "Descrição", "Utilizado", "Un", "Max", "Min"])
        
    try:
        # Força a leitura dos pedidos por ID numérico
        url_pedidos = f"{url_base}/export?format=csv&gid={GID_PEDIDOS}"
        pedidos = pd.read_csv(url_pedidos)
    except Exception as e:
        pedidos = pd.DataFrame(columns=["Data", "Código", "Descrição", "Solicitante", "Situação", "SC", "OF"])
    
    # Garante cabeçalhos mínimos caso a tabela venha vazia
    if estoque.empty or "Descrição" not in estoque.columns:
        estoque = pd.DataFrame(columns=["Código", "Descrição", "Utilizado", "Un", "Max", "Min"])
    if pedidos.empty or "Situação" not in pedidos.columns:
        pedidos = pd.DataFrame(columns=["Data", "Código", "Descrição", "Solicitante", "Situação", "SC", "OF"])
        
    return estoque, pedidos

estoque_df, pedidos_df = carregar_dados()

# Título do App
st.title("📋 Solicitação de Peças")
st.write("Busque a peça que precisa e adicione ao pedido em andamento.")

# Criação das Abas na Interface
aba_usuario, aba_admin = st.tabs(["👤 Fazer Pedido", "🔒 Painel do Administrador"])

# ==================== ABA DO USUÁRIO ====================
with aba_usuario:
    st.subheader("Nova Solicitação")
    
    if estoque_df.empty:
        st.warning("⚠️ O catálogo de peças está vazio. Verifique se configurou o GID correto da aba 'Lista Peças' no código.")
    else:
        lista_pecas = estoque_df["Descrição"].dropna().unique().tolist()
        lista_pecas.sort()
        
        peca_selecionada = st.selectbox("Selecione a Peça (Busque digitando):", ["Selecione..."] + lista_pecas)
        solicitante = st.text_input("Seu Nome / Identificação:")
        
        if st.button("Incluir no Pedido", type="primary"):
            if peca_selecionada == "Selecione...":
                st.error("Por favor, selecione uma peça válida.")
            elif not solicitante.strip():
                st.error("Por favor, insira o seu nome.")
            else:
                já_existe = False
                quem_pediu = ""
                
                if not pedidos_df.empty:
                    duplicados = pedidos_df[
                        (pedidos_df["Descrição"] == peca_selecionada) & 
                        (pedidos_df["Situação"].astype(str).str.lower() == "pendente")
                    ]
                    if not duplicados.empty:
                        já_existe = True
                        quem_pediu = duplicados["Solicitante"].values[0]
                
                if já_existe:
                    st.error(f"⚠️ **Aviso de Duplicidade:** Já existe um pedido **Pendente** para a peça *'{peca_selecionada}'* feito por **{quem_pediu}**.")
                else:
                    linha_estoque = estoque_df[estoque_df["Descrição"] == peca_selecionada]
                    codigo_peca = linha_estoque["Código"].values[0] if not linha_estoque.empty and "Código" in estoque_df.columns else ""
                    
                    data_atual = datetime.now().strftime("%d/%m/%Y")
                    
                    novo_pedido = pd.DataFrame([{
                        "Data": data_atual,
                        "Código": codigo_peca,
                        "Descrição": peca_selecionada,
                        "Solicitante": solicitante.strip(),
                        "Situação": "Pendente",
                        "SC": "",
                        "OF": ""
                    }])
                    
                    pedidos_atualizados = pd.concat([pedidos_df, novo_pedido], ignore_index=True)
                    
                    # Salva utilizando a biblioteca padrão do gsheets para a aba correspondente
                    conn.update(worksheet="Pedidos em Andamento", data=pedidos_atualizados)
                    st.success(f"✅ Sucesso! '{peca_selecionada}' adicionado à lista de pedidos.")
                    st.rerun()

    st.markdown("---")
    st.subheader("👀 Pedidos Atuais em Andamento")
    if not pedidos_df.empty and "Situação" in pedidos_df.columns:
        ativos = pedidos_df[pedidos_df["Situação"].astype(str).str.lower() == "pendente"]
        if not ativos.empty:
            st.dataframe(ativos[["Data", "Código", "Descrição", "Solicitante"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum pedido pendente no momento.")
    else:
        st.info("Nenhum pedido registrado.")

# ==================== ABA DO ADMINISTRADOR ====================
with aba_admin:
    st.subheader("Acesso Restrito")
    senha_inserida = st.text_input("Digite a senha do Administrador:", type="password")
    
    if senha_inserida == SENHA_ADMIN:
        st.success("🔓 Acesso liberado!")
        st.write("Gerencie os pedidos pendentes abaixo:")
        
        if not pedidos_df.empty and "Situação" in pedidos_df.columns:
            pendentes = pedidos_df[pedidos_df["Situação"].astype(str).str.lower() == "pendente"]
            
            if pendentes.empty:
                st.info("Não há pedidos pendentes para autorizar/marcar.")
            else:
                for idx, row in pendentes.iterrows():
                    col1, col2 = st.columns()
                    with col1:
                        st.write(f"📦 **[{row['Código']}] {row['Descrição']}** - Por: {row['Solicitante']} ({row['Data']})")
                    with col2:
                        if st.button("Marcar Pedido", key=f"btn_{idx}"):
                            pedidos_df.at[idx, "Situação"] = "Pedido Feito"
                            conn.update(worksheet="Pedidos em Andamento", data=pedidos_df)
                            st.success(f"Atualizado!")
                            st.rerun()
        else:
            st.info("Nenhum pedido cadastrado no banco de dados.")
    elif senha_inserida != "":
        st.error("Senha incorreta. Tente novamente.")

