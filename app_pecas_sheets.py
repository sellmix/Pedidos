import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

# Configurações iniciais da página
st.set_page_config(page_title="Sistema de Pedidos de Peças", page_icon="⚙️", layout="centered")

# CONFIGURAÇÃO DE SEGURANÇA DO ADMIN
SENHA_ADMIN = "admin123"     # Altere para a senha que desejar

# Inicializa a conexão oficial usando os Secrets com a Service Account no formato padrão
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        estoque = conn.read(worksheet="Lista Peças", ttl=0)
    except Exception as e:
        st.error(f"Erro ao ler 'Lista Peças'. Verifique os Secrets.")
        estoque = pd.DataFrame(columns=["Código", "Descrição", "Utilizado", "Un", "Max", "Min", "Foto"])
        
    try:
        pedidos = conn.read(worksheet="Pedidos em Andamento", ttl=0)
    except Exception:
        pedidos = pd.DataFrame(columns=["Data", "Código", "Descrição", "Quantidade", "Solicitante", "Situação", "SC", "OF"])
    
    # Validação estrutural de colunas (incluindo a coluna Foto)
    if estoque.empty or "Descrição" not in estoque.columns:
        estoque = pd.DataFrame(columns=["Código", "Descrição", "Utilizado", "Un", "Max", "Min", "Foto"])
    if "Foto" not in estoque.columns:
        estoque["Foto"] = ""
        
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
        st.warning("⚠️ O catálogo de peças aparece vazio. Certifique-se de que os Secrets estão configurados no formato correto.")
    else:
        lista_pecas = estoque_df["Descrição"].dropna().unique().tolist()
        lista_pecas = [str(p).strip() for p in lista_pecas if str(p).strip() != ""]
        lista_pecas.sort()
        
        peca_selecionada = st.selectbox("Selecione a Peça (Busque digitando):", ["Selecione..."] + lista_pecas)
        
        # --- LÓGICA DE FOTOS CORRIGIDA ---
        if peca_selecionada != "Selecione...":
            linha_peca = estoque_df[estoque_df["Descrição"] == peca_selecionada]
            if not linha_peca.empty and "Foto" in estoque_df.columns:
                # CORREÇÃO CRUCIAL: Uso correto do .iloc[0] para extrair o valor da linha do Pandas
                valor_foto = str(linha_peca.iloc[0]["Foto"]).strip()
                
                # Caso 1: Está escrito "procurar"
                if valor_foto.lower() == "procurar":
                    termo_seguro = urllib.parse.quote_plus(peca_selecionada)
                    link_google = f"https://google.com/search?q={termo_seguro}&tbm=isch"
                    st.link_button("🔍 Clique aqui para buscar fotos no Google", link_google, type="secondary")
                
                # Caso 2: Contém um link real
                elif valor_foto.lower().startswith("http"):
                    try:
                        st.image(valor_foto, caption=f"Visualização: {peca_selecionada}", width=300)
                    except Exception:
                        st.caption("🖼️ *(Erro ao carregar o link da imagem fornecido na planilha)*")
                
                # Caso 3: Está vazio, tem 'nan' ou qualquer outro texto
                else:
                    st.caption("🖼️ *Foto não disponível para esta peça.*")
        # -----------------------------------------------------
        
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
                        quem_pediu = duplicados.iloc[0]["Solicitante"]
                
                if já_existe:
                    st.error(f"⚠️ **Aviso de Duplicidade:** Já existe um pedido **Pendente** para a peça *'{peca_selecionada}'* feito por **{quem_pediu}**.")
                else:
                    linha_estoque = estoque_df[estoque_df["Descrição"] == peca_selecionada]
                    codigo_peca = linha_estoque.iloc[0]["Código"] if not linha_estoque.empty and "Código" in estoque_df.columns else ""
                    
                    data_atual = datetime.now().strftime("%d/%m/%Y")
                    
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
                    
                    conn.update(worksheet="Pedidos em Andamento", data=pedidos_atualizados)
                    st.success(f"✅ Sucesso! {quantidade}x '{peca_selecionada}' adicionado com sucesso.")
                    st.rerun()

    st.markdown("---")
    st.subheader("👀 Pedidos Atuais em Andamento")
    if not pedidos_df.empty and "Situação" in pedidos_df.columns:
        ativos = pedidos_df[pedidos_df["Situação"].astype(str).str.lower().str.strip() == "pendente"]
        if not ativos.empty:
            colunas_visiveis = [c for c in ["Data", "Código", "Descrição", "Quantidade", "Solicitante", "Situação"] if c in ativos.columns]
            st.dataframe(ativos[colunas_visiveis], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum pedido pendente no momento.")
    else:
        st.info("Nenhum pedido registrado.")

# ==================== ABA DO ADMINISTRADOR ====================
# ==================== ABA DO ADMINISTRADOR ====================
with aba_admin:
    st.subheader("🔒 Painel do Administrador")

    senha_inserida = st.text_input(
        "Digite a senha do Administrador:",
        type="password"
    )

    if senha_inserida == SENHA_ADMIN:

        st.success("🔓 Acesso liberado!")

        st.write("### 📋 Controle de Pedidos")

        if not pedidos_df.empty and "Situação" in pedidos_df.columns:

            # ==================================================
            # MOSTRAR TODOS OS PEDIDOS DIFERENTES DE ENTREGUE
            # ==================================================

            pedidos_admin = pedidos_df[
                pedidos_df["Situação"]
                .astype(str)
                .str.strip()
                .str.lower() != "entregue"
            ].copy()

            if pedidos_admin.empty:

                st.info("✅ Não existem pedidos pendentes.")

            else:

                # Garantir que as colunas existam
                if "SC" not in pedidos_admin.columns:
                    pedidos_admin["SC"] = ""

                if "OF" not in pedidos_admin.columns:
                    pedidos_admin["OF"] = ""

                # Lista de situações permitidas
                situacoes = [
                    "Solicitado",
                    "Com Pedido",
                    "Entregue"
                ]

                # ==================================================
                # PREPARAR TABELA PARA EDIÇÃO
                # ==================================================

                colunas_edicao = [
                    "Data",
                    "Código",
                    "Descrição",
                    "Quantidade",
                    "Solicitante",
                    "Situação",
                    "SC",
                    "OF"
                ]

                colunas_edicao = [
                    c for c in colunas_edicao
                    if c in pedidos_admin.columns
                ]

                tabela_editor = pedidos_admin[colunas_edicao].copy()

                # ==================================================
                # EDITOR
                # ==================================================

                dados_editados = st.data_editor(
                    tabela_editor,
                    hide_index=True,
                    use_container_width=True,
                    column_config={

                        "Data": st.column_config.TextColumn(
                            "Data",
                            disabled=True
                        ),

                        "Código": st.column_config.TextColumn(
                            "Código",
                            disabled=True
                        ),

                        "Descrição": st.column_config.TextColumn(
                            "Descrição",
                            disabled=True
                        ),

                        "Quantidade": st.column_config.NumberColumn(
                            "Quantidade",
                            disabled=True
                        ),

                        "Solicitante": st.column_config.TextColumn(
                            "Solicitante",
                            disabled=True
                        ),

                        "Situação": st.column_config.SelectboxColumn(
                            "Situação",
                            options=situacoes,
                            required=True
                        ),

                        "SC": st.column_config.TextColumn(
                            "SC",
                            help="Número da Solicitação de Compra"
                        ),

                        "OF": st.column_config.TextColumn(
                            "OF",
                            help="Número da Ordem de Fornecimento"
                        )
                    },
                    disabled=[
                        c for c in [
                            "Data",
                            "Código",
                            "Descrição",
                            "Quantidade",
                            "Solicitante"
                        ]
                        if c in tabela_editor.columns
                    ],
                    key="editor_pedidos"
                )

                st.markdown("---")

                # ==================================================
                # BOTÃO SALVAR
                # ==================================================

                if st.button(
                    "💾 Salvar alterações",
                    type="primary",
                    use_container_width=True
                ):

                    try:

                        # Criar cópia do DataFrame original
                        pedidos_novos = pedidos_df.copy()

                        # Atualizar somente os registros exibidos
                        for posicao, indice_original in enumerate(
                            pedidos_admin.index
                        ):

                            pedidos_novos.loc[
                                indice_original,
                                "Situação"
                            ] = dados_editados.iloc[
                                posicao
                            ]["Situação"]

                            pedidos_novos.loc[
                                indice_original,
                                "SC"
                            ] = dados_editados.iloc[
                                posicao
                            ]["SC"]

                            pedidos_novos.loc[
                                indice_original,
                                "OF"
                            ] = dados_editados.iloc[
                                posicao
                            ]["OF"]

                        # Salvar no Google Sheets
                        conn.update(
                            worksheet="Pedidos em Andamento",
                            data=pedidos_novos
                        )

                        st.success(
                            "✅ Alterações salvas com sucesso!"
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"❌ Erro ao salvar alterações: {e}"
                        )

        else:

            st.info(
                "Nenhum pedido cadastrado no banco de dados."
            )

    elif senha_inserida != "":
        st.error("❌ Senha incorreta. Tente novamente.")
