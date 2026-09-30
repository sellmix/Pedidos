import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configurações iniciais da página
st.set_page_config(page_title="Sistema de Pedidos de Peças", page_icon="⚙️", layout="centered")

# CONFIGURAÇÃO DE SEGURANÇA DO ADMIN
SENHA_ADMIN = "admin123"     # Altere para a senha que desejar

# Inicializa a conexão oficial usando os Secrets com a Service Account
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Lendo diretamente pelo nome da aba graças à Conta de Serviço autorizada
        estoque = conn.read(worksheet="Lista Peças", ttl=0)
    except Exception as e:
        st.error(f"Erro ao ler 'Lista Peças': Envie o e-mail da Service Account como EDITOR na sua Planilha.")
        estoque = pd.DataFrame(columns=["Código", "Descrição", "Utilizado", "Un", "Max", "Min"])
        
    try:
        pedidos = conn.read(worksheet="Pedidos em Andamento", ttl=0)
    except Exception:
        pedidos = pd.DataFrame(columns=["Data", "Código", "Descrição", "Quantidade", "Solicitante", "Situação", "SC", "OF"])
    
    # Validação de colunas
    if estoque.empty or "Descrição" not in estoque.columns:
        estoque = pd.DataFrame(columns=["Código", "Descrição", "Utilizado", "Un", "Max", "Min"])
    if pedidos.empty or "Situação" not in pedidos.columns:
        pedidos = pd.DataFrame(columns=["Data", "Código", "Descrição", "Quantidade", "Solicitante", "Situação", "SC", "OF"])
        
    return estoque, pedidos

estoque_df, pedidos_df = carregar_dados()

st.title("📋 Solicitação de Peças")
st.write("Busque a peça que precisa e adicione ao pedido em andamento.")

aba_usuario, aba_admin = st.tabs(["👤 Fazer Pedido", "🔒 Painel do Administrador"])

# ==================== ABA DO USUÁRIO ====================
with aba_usuario:
    st.subheader("Nova Solicitação")
    
    if estoque_df.empty:
        st.warning("⚠️ O catálogo de peças aparece vazio. Certifique-se de que compartilhou a planilha com o e-mail da Service Account.")
    else:
        # Puxa e limpa a lista de itens da coluna Descrição
        lista_pecas = estoque_df["Descrição"].dropna().unique().tolist()
        lista_pecas = [str(p).strip() for p in lista_pecas if str(p).strip() != ""]
        lista_pecas.sort()
        
        peca_selecionada = st.selectbox("Selecione a Peça (Busque digitando):", ["Selecione..."] + lista_pecas)
        quantidade = st.number_input("Quantidade necessária:", min_value=1, value=1, step=1)
        solicitante = st.text_input("Seu Nome / Identificação:")
        
        if st.button("Incluir no Pedido", type="primary"):
            if peca_selecionada == "Selecione...":
                st.error("Por favor, selecione uma peça válida.")
            elif not solicitante.strip():
                st.error("Por favor, insira o seu nome.")
            else:
                # VERIFICAÇÃO DE DUPLICIDADE EM ANDAMENTO
                já_existe = False
                quem_pediu = ""
                
                if not pedidos_df.empty and "Situação" in pedidos_df.columns:
                    duplicados = pedidos_df[
                        (pedidos_df["Descrição"].astype(str) == str(peca_selecionada)) & 
                        (pedidos_df["Situação"].astype(str).str.lower().str.strip() == "pendente")
                    ]
                    if not duplicados.empty:
                        já_existe = True
                        quem_pediu = duplicados["Solicitante"].values[0]
                
                if já_existe:
                    st.error(f"⚠️ **Aviso de Duplicidade:** Já existe um pedido **Pendente** para a peça *'{peca_selecionada}'* feito por **{quem_pediu}**.")
                else:
                    # Coleta o código da peça
                    linha_estoque = estoque_df[estoque_df["Descrição"] == peca_selecionada]
                    codigo_peca = linha_estoque["Código"].values[0] if not linha_estoque.empty and "Código" in estoque_df.columns else ""
                    
                    data_atual = datetime.now().strftime("%d/%m/%Y")
                    
                    # Prepara a linha no formato exato da sua aba de Pedidos
                    novo_pedido = pd.DataFrame([{
                        "Data": data_atual,
                        "Código": str(codigo_peca),
                        "Descrição": peca_selecionada,
                        "Quantidade": int(quantidade),
                        "Solicitante": solicitante.strip(),
                        "Situação": "Pendente",
                        "SC": "",
                        "OF": ""
                    }])
                    
                    pedidos_atualizados = pd.concat([pedidos_df, novo_pedido], ignore_index=True)
                    
                    # Gravação via conexão autenticada
                    conn.update(worksheet="Pedidos em Andamento", data=pedidos_atualizados)
                    st.success(f"✅ Sucesso! {quantidade}x '{peca_selecionada}' adicionado à lista.")
                    st.rerun()

    st.markdown("---")
    st.subheader("👀 Pedidos Atuais em Andamento")
    if not pedidos_df.empty and "Situação" in pedidos_df.columns:
        ativos = pedidos_df[pedidos_df["Situação"].astype(str).str.lower().str.strip() == "pendente"]
        if not ativos.empty:
            colunas_visiveis = [c for c in ["Data", "Código", "Descrição", "Quantidade", "Solicitante"] if c in ativos.columns]
            st.dataframe(ativos[colunas_visiveis], use_container_width=True, hide_index=True)
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
            pendentes = pedidos_df[pedidos_df["Situação"].astype(str).str.lower().str.strip() == "pendente"]
            
            if pendentes.empty:
                st.info("Não há pedidos pendentes para autorizar.")
            else:
                for idx, row in pendentes.iterrows():
                    col1, col2 = st.columns()
                    with col1:
                        st.write(f"📦 **[{row['Código']}] {row['Descrição']}** (Qtd: {row['Quantidade']}) - Por: {row['Solicitante']} ({row['Data']})")
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


