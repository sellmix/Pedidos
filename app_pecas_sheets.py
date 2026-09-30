import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse


# ============================================================
# CONFIGURAÇÕES DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Sistema de Pedidos de Peças",
    page_icon="⚙️",
    layout="centered"
)
st.markdown(
    '<h1 style="font-size:28px;">📋 Solicitação de Peças</h1>',
    unsafe_allow_html=True
)


# ============================================================
# CONFIGURAÇÃO DE SEGURANÇA DO ADMINISTRADOR
# ============================================================

SENHA_ADMIN = "admin123"


# ============================================================
# CONEXÃO COM GOOGLE SHEETS
# ============================================================

conn = st.connection(
    "gsheets",
    type=GSheetsConnection
)


# ============================================================
# FUNÇÃO PARA CARREGAR OS DADOS
# ============================================================

def carregar_dados():

    # --------------------------------------------------------
    # LISTA DE PEÇAS
    # --------------------------------------------------------

    try:

        estoque = conn.read(
            worksheet="Lista Peças",
            ttl=0
        )

    except Exception:

        st.error(
            "❌ Erro ao ler a planilha 'Lista Peças'. "
            "Verifique os Secrets e a conexão com o Google Sheets."
        )

        estoque = pd.DataFrame(
            columns=[
                "Código",
                "Descrição",
                "Utilizado",
                "Un",
                "Max",
                "Min",
                "Foto"
            ]
        )


    # --------------------------------------------------------
    # PEDIDOS
    # --------------------------------------------------------

    try:

        pedidos = conn.read(
            worksheet="Pedidos em Andamento",
            ttl=0
        )

    except Exception:

        pedidos = pd.DataFrame(
            columns=[
                "Data",
                "Código",
                "Descrição",
                "Quantidade",
                "Solicitante",
                "Situação",
                "SC",
                "OF"
            ]
        )


    # ========================================================
    # VALIDAR ESTOQUE
    # ========================================================

    if (
        estoque.empty
        or "Descrição" not in estoque.columns
    ):

        estoque = pd.DataFrame(
            columns=[
                "Código",
                "Descrição",
                "Utilizado",
                "Un",
                "Max",
                "Min",
                "Foto"
            ]
        )


    if "Foto" not in estoque.columns:

        estoque["Foto"] = ""


    # ========================================================
    # VALIDAR PEDIDOS
    # ========================================================

    if (
        pedidos.empty
        or "Situação" not in pedidos.columns
    ):

        pedidos = pd.DataFrame(
            columns=[
                "Data",
                "Código",
                "Descrição",
                "Quantidade",
                "Solicitante",
                "Situação",
                "SC",
                "OF"
            ]
        )


    # --------------------------------------------------------
    # Garantir SC
    # --------------------------------------------------------

    if "SC" not in pedidos.columns:

        pedidos["SC"] = ""


    # --------------------------------------------------------
    # Garantir OF
    # --------------------------------------------------------

    if "OF" not in pedidos.columns:

        pedidos["OF"] = ""


    # ========================================================
    # IMPORTANTE:
    # CONVERTER CAMPOS EDITÁVEIS PARA TEXTO
    # ========================================================

    for coluna in ["SC", "OF", "Situação"]:

        if coluna not in pedidos.columns:

            pedidos[coluna] = ""

        pedidos[coluna] = (
            pedidos[coluna]
            .fillna("")
            .astype(str)
        )


    return estoque, pedidos


# ============================================================
# CARREGAR DADOS
# ============================================================

estoque_df, pedidos_df = carregar_dados()


# ============================================================
# TÍTULO PRINCIPAL
# ============================================================

st.title("📋 Solicitação de Peças")

st.write(
    "Busque a peça que precisa e adicione ao pedido em andamento."
)


# ============================================================
# ABAS
# ============================================================

aba_usuario, aba_admin = st.tabs(
    [
        "👤 Fazer Pedido",
        "🔒 Painel do Administrador"
    ]
)


# ################################################################
# ################################################################
#
#                       ABA DO USUÁRIO
#
# ################################################################
# ################################################################

with aba_usuario:

    st.subheader("Nova Solicitação")


    # ========================================================
    # VERIFICAR ESTOQUE
    # ========================================================

    if estoque_df.empty:

        st.warning(
            "⚠️ O catálogo de peças aparece vazio. "
            "Certifique-se de que os Secrets estão configurados "
            "corretamente."
        )

    else:

        # ====================================================
        # MONTAR LISTA DE PEÇAS
        # ====================================================

        lista_pecas = (
            estoque_df["Descrição"]
            .dropna()
            .unique()
            .tolist()
        )


        lista_pecas = [
            str(p).strip()
            for p in lista_pecas
            if str(p).strip() != ""
        ]


        lista_pecas.sort()


        # ====================================================
        # SELECIONAR PEÇA
        # ====================================================

        peca_selecionada = st.selectbox(
            "Selecione a Peça (Busque digitando):",
            ["Selecione..."] + lista_pecas
        )


        # ====================================================
        # FOTO DA PEÇA
        # ====================================================

        if peca_selecionada != "Selecione...":

            linha_peca = estoque_df[
                estoque_df["Descrição"]
                .astype(str)
                .str.strip()
                == peca_selecionada
            ]


            if (
                not linha_peca.empty
                and "Foto" in estoque_df.columns
            ):

                valor_foto = str(
                    linha_peca.iloc[0]["Foto"]
                ).strip()


                # ------------------------------------------------
                # CASO 1 - BUSCAR FOTO NO GOOGLE
                # ------------------------------------------------

                if valor_foto.lower() == "procurar":

                    termo_seguro = (
                        urllib.parse.quote_plus(
                            peca_selecionada
                        )
                    )


                    link_google = (
                        "https://www.google.com/search"
                        f"?q={termo_seguro}&tbm=isch"
                    )


                    st.link_button(
                        "🔍 Clique aqui para buscar fotos no Google",
                        link_google,
                        type="secondary"
                    )


                # ------------------------------------------------
                # CASO 2 - LINK REAL DE FOTO
                # ------------------------------------------------

                elif valor_foto.lower().startswith("http"):

                    try:

                        st.image(
                            valor_foto,
                            caption=(
                                f"Visualização: "
                                f"{peca_selecionada}"
                            ),
                            width=300
                        )

                    except Exception:

                        st.caption(
                            "🖼️ *Erro ao carregar o link "
                            "da imagem fornecido na planilha.*"
                        )


                # ------------------------------------------------
                # CASO 3 - SEM FOTO
                # ------------------------------------------------

                else:

                    st.caption(
                        "🖼️ *Foto não disponível para esta peça.*"
                    )


        # ====================================================
        # QUANTIDADE
        # ====================================================

        quantidade = st.number_input(
            "Quantidade necessária:",
            min_value=1,
            value=1,
            step=1
        )


        # ====================================================
        # SOLICITANTE
        # ====================================================

        solicitante = st.text_input(
            "Seu Nome / Identificação:"
        )


        # ====================================================
        # BOTÃO INCLUIR PEDIDO
        # ====================================================

        if st.button(
            "Incluir no Pedido",
            type="primary"
        ):


            # ------------------------------------------------
            # VALIDAR PEÇA
            # ------------------------------------------------

            if peca_selecionada == "Selecione...":

                st.error(
                    "Por favor, selecione uma peça válida."
                )


            # ------------------------------------------------
            # VALIDAR SOLICITANTE
            # ------------------------------------------------

            elif not solicitante.strip():

                st.error(
                    "Por favor, insira o seu nome."
                )


            else:

                # ============================================
                # VERIFICAR DUPLICIDADE
                # ============================================

                ja_existe = False

                quem_pediu = ""


                if (
                    not pedidos_df.empty
                    and "Situação" in pedidos_df.columns
                ):


                    duplicados = pedidos_df[
                        (
                            pedidos_df["Descrição"]
                            .astype(str)
                            .str.strip()
                            ==
                            str(peca_selecionada).strip()
                        )
                        &
                        (
                            pedidos_df["Situação"]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            !=
                            "entregue"
                        )
                    ]


                    if not duplicados.empty:

                        ja_existe = True

                        quem_pediu = str(
                            duplicados.iloc[0]["Solicitante"]
                        )


                # ============================================
                # PEDIDO JÁ EXISTENTE
                # ============================================

                if ja_existe:

                    st.error(
                        f"⚠️ **Aviso de Duplicidade:** "
                        f"Já existe um pedido em andamento "
                        f"para a peça *'{peca_selecionada}'* "
                        f"feito por **{quem_pediu}**."
                    )


                # ============================================
                # CRIAR NOVO PEDIDO
                # ============================================

                else:

                    linha_estoque = estoque_df[
                        estoque_df["Descrição"]
                        .astype(str)
                        .str.strip()
                        ==
                        peca_selecionada
                    ]


                    if (
                        not linha_estoque.empty
                        and "Código" in estoque_df.columns
                    ):

                        codigo_peca = (
                            linha_estoque.iloc[0]["Código"]
                        )

                    else:

                        codigo_peca = ""


                    # ----------------------------------------
                    # DATA
                    # ----------------------------------------

                    data_atual = datetime.now().strftime(
                        "%d/%m/%Y"
                    )


                    # ----------------------------------------
                    # NOVO PEDIDO
                    # ----------------------------------------

                    novo_pedido = pd.DataFrame(
                        [
                            {
                                "Data": data_atual,
                                "Código": str(codigo_peca),
                                "Descrição": peca_selecionada,
                                "Quantidade": int(quantidade),
                                "Solicitante": solicitante.strip(),
                                "Situação": "Solicitado",
                                "SC": "",
                                "OF": ""
                            }
                        ]
                    )


                    # ----------------------------------------
                    # GARANTIR TIPOS
                    # ----------------------------------------

                    novo_pedido["SC"] = (
                        novo_pedido["SC"]
                        .astype(str)
                    )

                    novo_pedido["OF"] = (
                        novo_pedido["OF"]
                        .astype(str)
                    )

                    novo_pedido["Situação"] = (
                        novo_pedido["Situação"]
                        .astype(str)
                    )


                    # ----------------------------------------
                    # JUNTAR PEDIDOS
                    # ----------------------------------------

                    pedidos_atualizados = pd.concat(
                        [
                            pedidos_df,
                            novo_pedido
                        ],
                        ignore_index=True
                    )


                    # ----------------------------------------
                    # GARANTIR SC/OF COMO TEXTO
                    # ----------------------------------------

                    for coluna in [
                        "SC",
                        "OF",
                        "Situação"
                    ]:

                        pedidos_atualizados[coluna] = (
                            pedidos_atualizados[coluna]
                            .fillna("")
                            .astype(str)
                        )


                    # ----------------------------------------
                    # SALVAR GOOGLE SHEETS
                    # ----------------------------------------

                    conn.update(
                        worksheet="Pedidos em Andamento",
                        data=pedidos_atualizados
                    )


                    st.success(
                        f"✅ Sucesso! "
                        f"{quantidade}x "
                        f"'{peca_selecionada}' "
                        f"adicionado com sucesso."
                    )


                    st.rerun()


    # ========================================================
    # LISTA DE PEDIDOS ATUAIS
    # ========================================================

    st.markdown("---")

    st.subheader(
        "👀 Pedidos Atuais em Andamento"
    )


    if (
        not pedidos_df.empty
        and "Situação" in pedidos_df.columns
    ):


        ativos = pedidos_df[
            pedidos_df["Situação"]
            .astype(str)
            .str.strip()
            .str.lower()
            != "entregue"
        ]


        if not ativos.empty:

            colunas_visiveis = [
                c
                for c in [
                    "Data",
                    "Código",
                    "Descrição",
                    "Quantidade",
                    "Solicitante",
                    "Situação"
                ]
                if c in ativos.columns
            ]


            st.dataframe(
                ativos[colunas_visiveis],
                use_container_width=True,
                hide_index=True
            )


        else:

            st.info(
                "Nenhum pedido em andamento."
            )


    else:

        st.info(
            "Nenhum pedido registrado."
        )


# ################################################################
# ################################################################
#
#                    ABA ADMINISTRADOR
#
# ################################################################
# ################################################################

with aba_admin:

    st.subheader(
        "🔒 Painel do Administrador"
    )


    # ========================================================
    # SENHA
    # ========================================================

    senha_inserida = st.text_input(
        "Digite a senha do Administrador:",
        type="password"
    )


    # ========================================================
    # ACESSO LIBERADO
    # ========================================================

    if senha_inserida == SENHA_ADMIN:

        st.success(
            "🔓 Acesso liberado!"
        )


        st.write(
            "### 📋 Controle de Pedidos"
        )


        # ====================================================
        # VERIFICAR PEDIDOS
        # ====================================================

        if (
            not pedidos_df.empty
            and "Situação" in pedidos_df.columns
        ):


            # ------------------------------------------------
            # MOSTRAR TODOS MENOS ENTREGUES
            # ------------------------------------------------

            pedidos_admin = pedidos_df[
                pedidos_df["Situação"]
                .astype(str)
                .str.strip()
                .str.lower()
                != "entregue"
            ].copy()


            # ------------------------------------------------
            # NENHUM PEDIDO
            # ------------------------------------------------

            if pedidos_admin.empty:

                st.info(
                    "✅ Não existem pedidos pendentes."
                )


            else:

                # ============================================
                # GARANTIR SC E OF
                # ============================================

                if "SC" not in pedidos_admin.columns:

                    pedidos_admin["SC"] = ""


                if "OF" not in pedidos_admin.columns:

                    pedidos_admin["OF"] = ""


                # ============================================
                # COLUNAS DO ADMIN
                # ============================================

                colunas_admin = [
                    "Data",
                    "Código",
                    "Descrição",
                    "Quantidade",
                    "Solicitante",
                    "Situação",
                    "SC",
                    "OF"
                ]


                colunas_admin = [
                    c
                    for c in colunas_admin
                    if c in pedidos_admin.columns
                ]


                tabela_editor = (
                    pedidos_admin[
                        colunas_admin
                    ]
                    .copy()
                    .reset_index(drop=True)
                )


                # ============================================
                # CONVERTER CAMPOS EDITÁVEIS PARA TEXTO
                # ============================================

                for coluna in [
                    "SC",
                    "OF",
                    "Situação"
                ]:

                    if coluna in tabela_editor.columns:

                        tabela_editor[coluna] = (
                            tabela_editor[coluna]
                            .fillna("")
                            .astype(str)
                        )


                # ============================================
                # EDITOR DE PEDIDOS
                # ============================================

                dados_editados = st.data_editor(

                    tabela_editor,

                    hide_index=True,

                    use_container_width=True,

                    column_config={

                        "Data":
                            st.column_config.TextColumn(
                                "Data",
                                disabled=True
                            ),

                        "Código":
                            st.column_config.TextColumn(
                                "Código",
                                disabled=True
                            ),

                        "Descrição":
                            st.column_config.TextColumn(
                                "Descrição",
                                disabled=True
                            ),

                        "Quantidade":
                            st.column_config.NumberColumn(
                                "Quantidade",
                                disabled=True
                            ),

                        "Solicitante":
                            st.column_config.TextColumn(
                                "Solicitante",
                                disabled=True
                            ),

                        "Situação":
                            st.column_config.SelectboxColumn(
                                "Situação",
                                options=[
                                    "Solicitado",
                                    "Com Pedido",
                                    "Entregue"
                                ],
                                required=True
                            ),

                        "SC":
                            st.column_config.TextColumn(
                                "SC",
                                help=(
                                    "Número da Solicitação "
                                    "de Compra"
                                )
                            ),

                        "OF":
                            st.column_config.TextColumn(
                                "OF",
                                help=(
                                    "Número da Ordem "
                                    "de Fornecimento"
                                )
                            )
                    },

                    key="editor_pedidos"
                )


                # ============================================
                # BOTÃO SALVAR
                # ============================================

                st.markdown("---")


                if st.button(
                    "💾 Salvar alterações",
                    type="primary",
                    use_container_width=True
                ):


                    try:

                        # ====================================
                        # COPIAR DADOS ORIGINAIS
                        # ====================================

                        pedidos_novos = pedidos_df.copy()


                        # ====================================
                        # GARANTIR COLUNAS
                        # ====================================

                        for coluna in [
                            "SC",
                            "OF",
                            "Situação"
                        ]:

                            if coluna not in pedidos_novos.columns:

                                pedidos_novos[coluna] = ""


                            pedidos_novos[coluna] = (
                                pedidos_novos[coluna]
                                .fillna("")
                                .astype(str)
                            )


                        # ====================================
                        # ATUALIZAR REGISTROS
                        # ====================================

                        for posicao, indice_original in enumerate(
                            pedidos_admin.index
                        ):


                            # --------------------------------
                            # SITUAÇÃO
                            # --------------------------------

                            pedidos_novos.loc[
                                indice_original,
                                "Situação"
                            ] = str(
                                dados_editados.iloc[
                                    posicao
                                ]["Situação"]
                            )


                            # --------------------------------
                            # SC
                            # --------------------------------

                            pedidos_novos.loc[
                                indice_original,
                                "SC"
                            ] = str(
                                dados_editados.iloc[
                                    posicao
                                ]["SC"]
                            )


                            # --------------------------------
                            # OF
                            # --------------------------------

                            pedidos_novos.loc[
                                indice_original,
                                "OF"
                            ] = str(
                                dados_editados.iloc[
                                    posicao
                                ]["OF"]
                            )


                        # ====================================
                        # GARANTIR NOVAMENTE COMO TEXTO
                        # ====================================

                        for coluna in [
                            "SC",
                            "OF",
                            "Situação"
                        ]:

                            pedidos_novos[coluna] = (
                                pedidos_novos[coluna]
                                .fillna("")
                                .astype(str)
                            )


                        # ====================================
                        # SALVAR GOOGLE SHEETS
                        # ====================================

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
                            "❌ Erro ao salvar as alterações."
                        )

                        st.exception(e)


        else:

            st.info(
                "Nenhum pedido cadastrado "
                "no banco de dados."
            )


    # ========================================================
    # SENHA INCORRETA
    # ========================================================

    elif senha_inserida != "":

        st.error(
            "❌ Senha incorreta. Tente novamente."
        )
