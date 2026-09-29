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
        # Lê a aba de estoque de peças desligando o cache (ttl=0)
        estoque = conn.read(worksheet="Lista Peças", ttl=0)
    except Exception as e:
        st.error(f"Erro ao tentar ler a aba 'Lista Peças': {str(e)}")
        estoque = pd.DataFrame()
        
    try:
        # Lê a aba de pedidos desligando o cache (ttl=0)
        pedidos = conn.read(worksheet="Pedidos em Andamento", ttl=0)
    except Exception as e:
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
    
    # Se o catálogo estiver vazio ou não encontrar a coluna "Descrição"
    if estoque_df.empty or "Descrição" not in estoque_df.columns:
        st.warning("⚠️ O catálogo de peças aparece vazio no aplicativo.")
        
        # ÁREA DE DIAGNÓSTICO IMPRESSA NA TELA
        st.markdown("---")
        st.subheader("🔍 Diagnóstico da Planilha para o Administrador:")
        st.write("O robô do Streamlit está conseguindo ler a planilha, mas encontrou a seguinte estrutura:")
        
        try:
            st.write("**Colunas reais encontradas na aba 'Lista Peças':**", list(estoque_df.columns))
            st.write("**Quantidade de linhas preenchidas lidas:**", len(estoque_df))
        except Exception:
            st.write("Não foi possível listar as colunas. Verifique se o nome da aba está 100% correto.")
            
        st.markdown("""
        **O que verificar no seu Google Sheets para corrigir:**
        1. O nome da aba na parte de baixo da planilha deve ser exatamente: `Lista Peças` (com espaço e o Ç).
        2. A linha 1 dessa aba deve conter uma coluna escrita exatamente como: `Descrição` (com o Ç e o Til).
        3. Garanta que você digitou itens nas linhas de baixo (Linha 2, Linha 3, etc.).
        """)
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
                
                if not pedidos_df.empty and "Situação" in pedidos_df.columns:
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
                    # Busca o código correspondente à peça selecionada
                    linha_estoque = estoque_df[estoque_df["Descrição"] == peca_selecionada]
                    codigo_peca = linha_estoque["Código"].values[0] if not linha_estoque.empty and "Código" in estoque_df.columns else ""
                    
                    data_atual = datetime.now().strftime("%d/%m/%Y")
                    
                    # Preparar nova linha para salvar
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

    elif senha_inserida != "":
        st.error("Senha incorreta. Tente novamente.")
