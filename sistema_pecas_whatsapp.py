import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Sistema de Peças", page_icon="⚙️", layout="centered")

# ==========================================
# CONFIGURAÇÕES E CREDENCIAIS (EDITÁVEIS)
# ==========================================
# Defina a senha do Administrador aqui
SENHA_ADMIN = "admin123"

# DICA DE CONEXÃO COM O GOOGLE SHEETS:
# Para conectar ao Google Sheets em produção no Streamlit Community Cloud:
# 1. Crie uma planilha no Google Drive com as abas 'Estoque_Pecas' e 'Pedidos_Andamento'.
# 2. No menu Compartilhar da planilha, permita que qualquer pessoa com o link possa ler/editar (ou use uma Service Account).
# 3. Use a biblioteca `streamlit-google-sheets` ou `gspread`.
# Exemplo básico de uso com st.connection:
# conn = st.connection("gsheets", type=GSheetsConnection)
# df = conn.read(worksheet="Estoque_Pecas")

# Para este exemplo funcional, usamos o st.session_state para simular o banco de dados em tempo real
if "estoque" not in st.session_state:
    st.session_state.estoque = pd.DataFrame([
        {"ID": 1, "Nome_Peca": "Filtro de Óleo - Motor AP", "Categoria": "Filtros"},
        {"ID": 2, "Nome_Peca": "Pastilha de Freio Dianteira", "Categoria": "Freios"},
        {"ID": 3, "Nome_Peca": "Correia Dentada Haste 124", "Categoria": "Correias"},
        {"ID": 4, "Nome_Peca": "Bela de Ignição Iridium", "Categoria": "Ignição"},
        {"ID": 5, "Nome_Peca": "Amortecedor Dianteiro Direito", "Categoria": "Suspensão"},
    ])

if "pedidos" not in st.session_state:
    st.session_state.pedidos = pd.DataFrame(columns=[
        "ID_Pedido", "Nome_Peca", "Quantidade", "Solicitante", "Data_Solicitacao", "Status"
    ])

# Título do App
st.title("⚙️ Sistema de Pedidos de Peças")
st.write("Abra este link pelo WhatsApp para solicitar ou gerenciar peças.")

# Criação das abas no App
aba_usuario, aba_admin = st.tabs(["🛒 Fazer Pedido", "👑 Painel do Administrador"])

# ==========================================
# ABA DO USUÁRIO (SOLICITAR PEÇAS)
# ==========================================
with aba_usuario:
    st.header("Solicitar Nova Peça")
    
    # Inputs do usuário
    nome_solicitante = st.text_input("Seu Nome / Identificação:", placeholder="Ex: João Silva")
    
    # Busca de peças do catálogo
    lista_pecas_catalogo = st.session_state.estoque["Nome_Peca"].tolist()
    peca_selecionada = st.selectbox("Selecione a Peça Desejada:", [""] + lista_pecas_catalogo)
    
    quantidade = st.number_input("Quantidade Necessária:", min_value=1, max_value=100, value=1, step=1)
    
    if st.button("Incluir no Pedido", type="primary"):
        if not nome_solicitante.strip():
            st.error("Por favor, preencha o seu nome antes de enviar.")
        elif peca_selecionada == "":
            st.error("Por favor, selecione uma peça válida da lista.")
        else:
            # Validação: Verificar se a peça já está na lista com status 'Pendente'
            df_pedidos = st.session_state.pedidos
            ja_existe = df_pedidos[
                (df_pedidos["Nome_Peca"] == peca_selecionada) & 
                (df_pedidos["Status"] == "Pendente")
            ]
            
            if not ja_existe.empty:
                solicitante_atual = ja_existe.iloc[0]["Solicitante"]
                qtd_atual = ja_existe.iloc[0]["Quantidade"]
                st.error(
                    f"⚠️ **Aviso de Duplicidade:** Já existe um pedido **Pendente** para a peça "
                    f"'{peca_selecionada}' feito por **{solicitante_atual}** (Qtd: {qtd_atual})."
                )
            else:
                # Adiciona o novo pedido à lista
                novo_id = len(df_pedidos) + 1
                novo_pedido = {
                    "ID_Pedido": novo_id,
                    "Nome_Peca": peca_selecionada,
                    "Quantidade": quantidade,
                    "Solicitante": nome_solicitante,
                    "Data_Solicitacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Status": "Pendente"
                }
                st.session_state.pedidos = pd.concat([df_pedidos, pd.DataFrame([novo_pedido])], ignore_index=True)
                st.success(f"✅ Sucesso! {quantidade}x '{peca_selecionada}' foi adicionada à lista de pedidos em andamento.")

    # Exibição da lista de pedidos em andamento para consulta pública
    st.write("---")
    st.subheader("📋 Pedidos Atuais em Andamento")
    
    df_exibicao = st.session_state.pedidos[st.session_state.pedidos["Status"] == "Pendente"]
    if df_exibicao.empty:
        st.info("Não há nenhum pedido pendente no momento. Todas as peças estão disponíveis para solicitação.")
    else:
        st.dataframe(
            df_exibicao[["Nome_Peca", "Quantidade", "Solicitante", "Data_Solicitacao"]],
            use_container_width=True,
            hide_index=True
        )

# ==========================================
# ABA DO ADMINISTRADOR
# ==========================================
with aba_admin:
    st.header("Acesso Restrito")
    senha_inserida = st.text_input("Digite a senha de Administrador:", type="password")
    
    if senha_inserida == SENHA_ADMIN:
        st.success("Acesso liberado!")
        st.subheader("Gerenciar Pedidos Pendentes")
        
        df_admin = st.session_state.pedidos
        
        if df_admin.empty:
            st.info("Nenhum histórico de pedidos registrado.")
        else:
            # Mostra todos os pedidos e permite mudar o status
            st.write("Selecione os pedidos que você já realizou a compra/pedido para atualizar o sistema:")
            
            # Criando uma lista para marcar como feito usando checkboxes de forma dinâmica
            for index, row in df_admin.iterrows():
                if row["Status"] == "Pendente":
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"📦 **{row['Nome_Peca']}** | Qtd: {row['Quantidade']} | Por: {row['Solicitante']} ({row['Data_Solicitacao']})")
                    with col2:
                        if st.button("Marcar como Pedido", key=f"btn_{row['ID_Pedido']}"):
                            st.session_state.pedidos.at[index, "Status"] = "Pedido Feito"
                            st.rerun()
            
            st.write("---")
            st.subheader("📜 Histórico Geral (Todos os Pedidos)")
            st.dataframe(st.session_state.pedidos, use_container_width=True, hide_index=True)
            
    elif senha_inserida != "":
        st.error("Senha incorreta. Acesso negado.")
