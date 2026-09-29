import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configurações iniciais da página
st.set_page_config(page_title="Sistema de Pedidos de Peças", page_icon="⚙️", layout="centered")

# CONFIGURAÇÃO DE SEGURANÇA
SENHA_ADMIN = "admin123"  # Altere para a senha que desejar antes de subir o app

# Inicializa a conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para ler os dados das abas com segurança
def carregar_dados():
    try:
        estoque = conn.read(worksheet="Estoque_Pecas", ttl="0m")
    except Exception:
        estoque = pd.DataFrame(columns=["ID", "Nome_Peca", "Categoria"])
        
    try:
        pedidos = conn.read(worksheet="Pedidos_Andamento", ttl="0m")
    except Exception:
        pedidos = pd.DataFrame(columns=["ID_Pedido", "Nome_Peca", "Quantidade", "Solicitante", "Status"])
        
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
        st.warning("O catálogo de peças está vazio ou não foi carregado corretamente no Google Sheets.")
    else:
        # Lista de peças para o seletor
        lista_pecas = estoque_df["Nome_Peca"].dropna().unique().tolist()
        
        # Formulário de entrada
        peca_selecionada = st.selectbox("Selecione a Peça:", ["Selecione..."] + lista_pecas)
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
                qtd_pedida = 0
                
                if not pedidos_df.empty:
                    # Garantir que a comparação ignore maiúsculas/minúsculas
                    duplicados = pedidos_df[
                        (pedidos_df["Nome_Peca"] == peca_selecionada) & 
                        (pedidos_df["Status"].str.lower() == "pendente")
                    ]
                    if not duplicados.empty:
                        já_existe = True
                        quem_pediu = duplicados.iloc[0]["Solicitante"]
                        qtd_pedida = duplicados.iloc[0]["Quantidade"]
                
                if já_existe:
                    st.error(f"⚠️ **Aviso de Duplicidade:** Já existe um pedido **Pendente** para a peça *'{peca_selecionada}'* feito por **{quem_pediu}** (Qtd: {qtd_pedida}).")
                else:
                    # Preparar nova linha para salvar
                    novo_id = len(pedidos_df) + 1
                    novo_pedido = pd.DataFrame([{
                        "ID_Pedido": novo_id,
                        "Nome_Peca": peca_selecionada,
                        "Quantidade": int(quantidade),
                        "Solicitante": solicitante.strip(),
                        "Status": "Pendente"
                    }])
                    
                    # Junta o novo pedido à tabela atual
                    pedidos_atualizados = pd.concat([pedidos_df, novo_pedido], ignore_index=True)
                    
                    # Salva direto no Google Sheets
                    conn.update(worksheet="Pedidos_Andamento", data=pedidos_atualizados)
                    st.success(f"✅ Sucesso! {quantidade}x '{peca_selecionada}' adicionado à lista de pedidos.")
                    st.rerun()

    # Visualização rápida para o usuário ver o que está pendente
    st.markdown("---")
    st.subheader("👀 Pedidos Atuais em Andamento")
    if not pedidos_df.empty:
        ativos = pedidos_df[pedidos_df["Status"].str.lower() == "pendente"]
        if not ativos.empty:
            st.dataframe(ativos[["Nome_Peca", "Quantidade", "Solicitante"]], use_container_width=True, hide_index=True)
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
            pendentes = pedidos_df[pedidos_df["Status"].str.lower() == "pendente"]
            
            if pendentes.empty:
                st.info("Não há pedidos pendentes para autorizar/marcar.")
            else:
                for idx, row in pendentes.iterrows():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📦 **{row['Nome_Peca']}** (Qtd: {row['Quantidade']}) - Por: {row['Solicitante']}")
                    with col2:
                        # Botão individual para o admin atualizar o status daquela linha
                        if st.button("Marcar como Pedido", key=f"btn_{row['ID_Pedido']}"):
                            pedidos_df.at[idx, "Status"] = "Pedido Feito"
                            conn.update(worksheet="Pedidos_Andamento", data=pedidos_df)
                            st.success(f"Status atualizado para o item {row['Nome_Peca']}!")
                            st.rerun()
        else:
            st.info("Nenhum pedido cadastrado no banco de dados.")
    elif senha_inserida != "":
        st.error("Senha incorreta. Tente novamente.")

