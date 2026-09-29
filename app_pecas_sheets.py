import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configurações iniciais da página
st.set_page_config(page_title="Sistema de Pedidos de Peças", page_icon="⚙️", layout="centered")

# CONFIGURAÇÃO DE SEGURANÇA
SENHA_ADMIN = "admin123"  # Altere para a senha que desejar antes de subir o app

# Inicializa a conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para ler os dados das abas com segurança adaptada à sua planilha
def carregar_dados():
    try:
        # Lê a aba de estoque de peças
        estoque = conn.read(worksheet="Lista Peças", ttl="0")
    except Exception:
        estoque = pd.DataFrame(columns=["Código", "Descrição", "Utilizado", "Un", "Max", "Min"])
        
    try:
        # Lê a aba de pedidos com a nomenclatura exata fornecida
        pedidos = conn.read(worksheet="Pedidos em Andamento", ttl="0")
    except Exception:
        pedidos = pd.DataFrame(columns=["Data", "Código", "Descrição", "Solicitante", "Situação", "SC", "OF"])
    
    # Garante que as colunas essenciais existam mesmo se a planilha estiver vazia
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
        st.warning("O catálogo de peças está vazio ou não foi carregado corretamente. Verifique se a aba se chama 'Lista Peças' e possui a coluna 'Descrição'.")
    else:
        # Lista de peças baseada na coluna "Descrição" que você passou
        lista_pecas = estoque_df["Descrição"].dropna().unique().tolist()
        lista_pecas.sort() # Organiza em ordem alfabética para facilitar a busca
        
        # Formulário de entrada
        peca_selecionada = st.selectbox("Selecione a Peça (Busque digitando):", ["Selecione..."] + lista_pecas)
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
                
                if not pedidos_df.empty:
                    # Filtra os pedidos pendentes para a peça selecionada usando "Descrição" e "Situação"
                    duplicados = pedidos_df[
                        (pedidos_df["Descrição"] == peca_selecionada) & 
                        (pedidos_df["Situação"].astype(str).str.lower() == "pendente")
                    ]
                    if not duplicados.empty:
                        já_existe = True
                        # Pega o primeiro valor da lista de solicitantes
                        quem_pediu = duplicados["Solicitante"].values[0]
                
                if já_existe:
                    st.error(f"⚠️ **Aviso de Duplicidade:** Já existe um pedido **Pendente** para a peça *'{peca_selecionada}'* feito por **{quem_pediu}**.")
                else:
                    # Busca o código correspondente à peça selecionada
                    linha_estoque = estoque_df[estoque_df["Descrição"] == peca_selecionada]
                    codigo_peca = linha_estoque["Código"].values[0] if not linha_estoque.empty else ""
                    
                    # Data atual formatada (DD/MM/AAAA)
                    data_atual = datetime.now().strftime("%d/%m/%Y")
                    
                    # Preparar nova linha para salvar com a estrutura exata da sua planilha
                    novo_pedido = pd.DataFrame([{
                        "Data": data_atual,
                        "Código": codigo_peca,
                        "Descrição": peca_selecionada,
                        "Solicitante": solicitante.strip(),
                        "Situação": "Pendente",
                        "SC": "",
                        "OF": ""
                    }])
                    
                    # Junta o novo pedido à tabela atual
                    pedidos_atualizados = pd.concat([pedidos_df, novo_pedido], ignore_index=True)
                    
                    # Salva direto no Google Sheets
                    conn.update(worksheet="Pedidos em Andamento", data=pedidos_atualizados)
                    st.success(f"✅ Sucesso! '{peca_selecionada}' adicionado à lista de pedidos.")
                    st.rerun()

    # Visualização rápida para o usuário ver o que está pendente
    st.markdown("---")
    st.subheader("👀 Pedidos Atuais em Andamento")
    if not pedidos_df.empty:
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
        
        if not pedidos_df.empty:
            # Filtra apenas os pendentes para gerenciar
            pendentes = pedidos_df[pedidos_df["Situação"].astype(str).str.lower() == "pendente"]
            
            if pendentes.empty:
                st.info("Não há pedidos pendentes para autorizar/marcar.")
            else:
                for idx, row in pendentes.iterrows():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📦 **[{row['Código']}] {row['Descrição']}** - Por: {row['Solicitante']} ({row['Data']})")
                    with col2:
                        # Botão individual para o admin atualizar a situação daquela linha
                        # Usamos o índice da linha como chave única do botão
                        if st.button("Marcar Pedido", key=f"btn_{idx}"):
                            pedidos_df.at[idx, "Situação"] = "Pedido Feito"
                            conn.update(worksheet="Pedidos em Andamento", data=pedidos_df)
                            st.success(f"Atualizado!")
                            st.rerun()
        else:
            st.info("Nenhum pedido cadastrado no banco de dados.")
    elif senha_inserida != "":
        st.error("Senha incorreta. Tente novamente.")
