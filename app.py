import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
from pypdf import PdfReader, PdfWriter
import io
import zipfile
import re
from PIL import Image, ImageOps, ImageEnhance

# Configuração da Página
st.set_page_config(page_title="Frequência Individual", page_icon="📄")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("Folha de Frequência Individual")
st.sidebar.header("Configurações")
dpi_value = st.sidebar.slider("Qualidade do OCR (DPI)", min_value=150, max_value=300, value=250)

def extrair_nome_estrito(text, page_num):
    # 1. Limpeza inicial de quebras de linha e espaços duplos
    text_limpo = " ".join(text.split()).upper()
    
    # 2. Tenta a captura precisa entre "Eu." e "RG"
    match = re.search(r"EU[\.,]\s*(.*?)\s*(?:RG|INFOPEN|CUSTODIADO)", text_limpo)
    
    if match:
        nome = match.group(1).strip()
    else:
        # 3. Se falhar o Regex, removemos os termos do governo e pegamos o que sobrou
        sujeira = ["GOVERNO", "ESTADO", "SECRETARIA", "ADMINISTRAÇÃO", "PENITENCIÁRIA", "DECLARO"]
        for s in sujeira:
            text_limpo = text_limpo.replace(s, "")
        
        palavras = text_limpo.split()
        # Filtra palavras curtas que costumam ser ruído de OCR
        palavras_reais = [p for p in palavras if len(p) > 2]
        nome = " ".join(palavras_reais)

    # 4. LIMPEZA FINAL E TRAVAS SOLICITADAS:
    # Remove qualquer coisa que não seja letra ou espaço
    nome = re.sub(r'[^A-Z\s]', '', nome).strip()
    
    # Se o nome ficou gigante (como o do seu log), pegamos apenas as 2 primeiras palavras
    partes = nome.split()
    if len(nome) > 35 and len(partes) >= 2:
        nome = f"{partes[0]} {partes[1]}"
    
    # Trava final de 35 caracteres (evita nomes de arquivos inválidos/extensos)
    nome_final = nome[:35].strip()
    
    # Se ainda assim estiver vazio, usa o padrão de página
    if len(nome_final) < 3:
        return f"REVISAR_PAG_{page_num}"
        
    return nome_final


meses = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
]
mes_selecionado = st.selectbox("Selecione o mês de referência:", meses)
uploaded_file = st.file_uploader("Insira o PDF aqui", type="pdf")

if uploaded_file:
    if st.button("Iniciar"):
        file_bytes = uploaded_file.read()
        
        try:
            with st.status("Processando documento...", expanded=True) as status:
                st.write("Convertendo PDF em imagens...")
                images = convert_from_bytes(file_bytes, dpi=dpi_value)
                
                reader = PdfReader(io.BytesIO(file_bytes))
                total_pages = len(reader.pages)
                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i in range(0, total_pages, 2):
                        # Pega a página de declaração (par)
                        p_index = i + 1 if (i + 1) < total_pages else i
                        st.write(f"Analisando interno: Páginas {i+1}-{i+2}")
                        
                        ocr_text = pytesseract.image_to_string(images[p_index], lang='por')
                        nome_interno = extrair_nome_estrito(ocr_text, i+1) # Adicionado o i+1 aqui
                      
                        if not nome_interno:
                            nome_interno = f"REVISAR_PAG_{i+1}"
                        
                        st.write(f"Identificado: **{nome_interno}**")

                        # Criar PDF individual
                        writer = PdfWriter()
                        writer.add_page(reader.pages[i])
                        if i + 1 < total_pages:
                            writer.add_page(reader.pages[i+1])
                        
                        pdf_output = io.BytesIO()
                        writer.write(pdf_output)
                        zf.writestr(f"{nome_interno}_{mes_selecionado}.pdf", pdf_output.getvalue())
                
                status.update(label="Processamento concluído!", state="complete", expanded=False)

            st.success("Tudo pronto! Clique no botão abaixo para baixar.")
            st.download_button(
                label="Baixar Arquivos (ZIP) ⬇️",
                data=zip_buffer.getvalue(),
                file_name="Frequencia_Individual_" + mes_selecionado +".zip",
                mime="application/zip"
            )

        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")