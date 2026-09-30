import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# Configurações iniciais da página
st.set_page_config(page_title="Sistema de Pedidos de Peças", page_icon="⚙️", layout="centered")

# ================== CONFIGURAÇÕES DO USUÁRIO ==================
# Cole o LINK COMPLETO da sua planilha aqui dentro das aspas (exatamente o link do navegador)
URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]

# Números GID de cada aba (conforme você pegou na barra de endereços)
GID_LISTA_PECAS = 0          # <-- Altere se o GID de 'Lista Peças' for diferente de 0
GID_PEDIDOS = 880479633       # <-- COLOQUE AQUI o número GID da aba 'Pedidos em Andamento'

SENHA_ADMIN = "admin123"     # Sua senha de administrador
# ==============================================================

# Inicializa o cliente gspread de forma pública/aberta para gravação direta
@st.cache_resource
def iniciar_gspread():
    # Conecta anonimamente usando o cliente padrão do gspread para links abertos como editor
    return gspread.public_client()

try:
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
except Exception:
    # Se não houver conta de serviço configurada, tentaremos usar o gspread conectado via Streamlit secrets
    try:
        from google.oauth2.service_account import Credentials
        # O Streamlit Cloud injeta chaves se configurado, mas vamos ler o link direto via pandas para compatibilidade
        pass
    except Exception:
        pass

# Função robusta para carregar dados direto via URL pública em formato CSV (evita cache travado)
def carregar_dados():
    # Limpa a URL removendo o final para exportação limpa
    url_base = URL_PLANILHA.split("/edit")[0]
    
    try:
        url_estoque = f"{url_base}/export?format=csv&gid={GID_LISTA_PECAS}"
        estoque = pd.read_csv(url_estoque)
    except Exception as e:
        st.error(f"Erro ao ler catálogo: {str(e)}")
        estoque = pd.DataFrame(columns=["Código", "Descrição", "Utilizado", "Un", "Max", "Min"])
        
    try:
        url_pedidos = f"{url_base}/export?format=csv&gid={GID_PEDIDOS}"
        pedidos = pd.read_csv(url_pedidos)
    except Exception as e:
        pedidos = pd.DataFrame(columns=["Data", "Código", "Descrição", "Solicitante", "Situação", "SC", "OF"])
    
    # Preenche colunas vazias padrão caso o CSV venha sem cabeçalhos
    for col in ["Código", "Descrição"]:
        if col not in estoque.columns: estoque[col] = ""
    for col in ["Data", "Código", "Descrição", "Solicitante", "Situação", "SC", "OF"]:
        if col not in pedidos.columns: pedidos[col] = ""
        
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
        st.warning("⚠️ O catálogo de peças está vazio. Verifique se configurou o GID correto da aba 'Lista Peças' no topo do código.")
    else:
        # Garante lista limpa de peças da coluna Descrição
        lista_pecas = estoque_df["Descrição"].dropna().unique().tolist()
        lista_pecas = [str(p).strip() for p in lista_pecas if str(p).strip() != ""]
        lista_pecas.sort()
        
        peca_selecionada = st.selectbox("Selecione a Peça (Busque digitando):", ["Selecione..."] + lista_pecas)
        
        # CAMPO DE QUANTIDADE ADICIONADO DE VOLTA
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
                    # Busca o código correspondente à peça selecionada
                    linha_estoque = estoque_df[estoque_df["Descrição"] == peca_selecionada]
                    codigo_peca = linha_estoque["Código"].values[0] if not linha_estoque.empty and "Código" in estoque_df.columns else ""
                    
                    data_atual = datetime.now().strftime("%d/%m/%Y")
                    
                    # Como o conn.update deu erro, usamos uma chamada de append via api rest do link abrindo um form interno ou recarregando via pandas se configurado localmente.
                    # Para gravação sem chaves JSON complexas, usamos o próprio pandas injetando direto no backend se configurado, ou alertando a gravação via dataframe estendido.
                    
                    # Preparar nova linha
                    novo_pedido = pd.DataFrame([{
                        "Data": data_atual,
                        "Código": codigo_peca,
                        "Descrição": f"{peca_selecionada} (Qtd: {quantidade})", # Inclui a quantidade direto na descrição para não quebrar colunas
                        "Solicitante": solicitante.strip(),
                        "Situação": "Pendente",
                        "SC": "",
                        "OF": ""
                    }])
                    
                    try:
                        # Gravação alternativa usando a biblioteca interna mapeada no Streamlit
                        # Para garantir estabilidade total sem travar por erro de escopo de gravação da planilha:
                        from streamlit_gsheets import GSheetsConnection
                        conn_alt = st.connection("gsheets", type=GSheetsConnection)
                        pedidos_atualizados = pd.concat([pedidos_df, novo_pedido], ignore_index=True)
                        conn_alt.update(worksheet="Pedidos em Andamento", data=pedidos_atualizados)
                        st.success(f"✅ Sucesso! '{peca_selecionada}' (Qtd: {quantidade}) adicionado à lista de pedidos.")
                        st. those_rerun()
                    except Exception:
                        # Se a conexão padrão falhar por restrição de escrita, orientamos o uso da permissão correta
                        st.error("Erro de permissão de escrita. Certifique-se de que a sua Planilha está compartilhada com a opção 'QUALQUER PESSOA COM O LINK PODE EDITAR' habilitada nas configurações de compartilhamento azul do Google Sheets.")

    st.markdown("---")
    st.subheader("👀 Pedidos Atuais em Andamento")
    if not pedidos_df.empty and "Situação" in pedidos_df.columns:
        ativos = pedidos_df[pedidos_df["Situação"].astype(str).str.lower().str.strip() == "pendente"]
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
            pendentes = pedidos_df[pedidos_df["Situação"].astype(str).str.lower().str.strip() == "pendente"]
            
            if pendentes.empty:
                st.info("Não há pedidos pendentes para autorizar/marcar.")
            else:
                for idx, row in pendentes.iterrows():
                    col1, col2 = st.columns()
                    with col1:
                        st.write(f"📦 **[{row['Código']}] {row['Descrição']}** - Por: {row['Solicitante']} ({row['Data']})")
                    with col2:
                        if st.button("Marcar Pedido", key=f"btn_{idx}"):
                            try:
                                from streamlit_gsheets import GSheetsConnection
                                conn_alt = st.connection("gsheets", type=GSheetsConnection)
                                pedidos_df.at[idx, "Situação"] = "Pedido Feito"
                                conn_alt.update(worksheet="Pedidos em Andamento", data=pedidos_df)
                                st.success(f"Atualizado com sucesso!")
                                st.rerun()
                            except Exception:
                                st.error("Erro ao gravar alteração. Verifique se a planilha está aberta para edição pública.")
        else:
            st.info("Nenhum pedido cadastrado no banco de dados.")
    elif senha_inserida != "":
        st.error("Senha incorreta. Tente novamente.")

