import streamlit as st
import ollama
import os
import re
from PIL import Image
from docx import Document
import pdfplumber
import pytesseract

def configure_tesseract():
    standard_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")
    ]
    for path in standard_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return True
    return False

def get_installed_models():
    try:
        models_info = ollama.list()
        models_list = []
        if isinstance(models_info, dict):
            models_list = models_info.get('models', [])
        elif hasattr(models_info, 'models'):
            models_list = models_info.models
        elif hasattr(models_info, 'get'):
            models_list = models_info.get('models', [])
            
        names = []
        for m in models_list:
            if isinstance(m, dict):
                name = m.get('model')
            else:
                name = getattr(m, 'model', None)
            if name:
                names.append(name)
        return names if names else ['gemma4:e4b']
    except Exception:
        return ['gemma4:e4b']

def parse_response(response):
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    score = 0
    summary = "No summary provided."
    for line in lines:
        if "score" in line.lower():
            match = re.search(r'\d+', line)
            if match:
                score = int(match.group())
        elif "summary" in line.lower():
            parts = line.split(':', 1)
            if len(parts) > 1:
                summary = parts[1].strip()
    return score, summary

class ResumeSorter:
    def __init__(self):
        self.temp_dir = "temp_resumes"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def extract_text_from_pdf(self, pdf_path):
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def extract_text_from_docx(self, docx_path):
        doc = Document(docx_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text])
        return text

# Set up the look of the website
st.set_page_config(page_title="AI Resume Sorter", page_icon="📄", layout="wide")

# Create an instance of the class
resume_sorter = ResumeSorter()

# Sidebar options (defined early so the main script can use selected_model)
with st.sidebar:
    st.header("Model Configuration")
    installed_models = get_installed_models()
    default_model = 'gemma4:e4b' if 'gemma4:e4b' in installed_models else installed_models[0]
    selected_model = st.selectbox(
        "Select LLM Model:",
        options=installed_models,
        index=installed_models.index(default_model) if default_model in installed_models else 0
    )
    
    st.header("Additional Options")
    if st.button("Clear Cache"):
        if os.path.exists(resume_sorter.temp_dir):
            for filename in os.listdir(resume_sorter.temp_dir):
                try:
                    os.remove(os.path.join(resume_sorter.temp_dir, filename))
                except Exception:
                    pass
            try:
                os.rmdir(resume_sorter.temp_dir)
            except Exception:
                pass
        st.rerun()

st.title("📄 AI Resume Sorter & Ranker")
st.write("Upload candidate resumes (images, Word, PDF) to automatically read, score, and rank them using Gemma via your GPU!")

# Step 1: Input Job requirements
with st.container():
    st.header("Step 1: Define Job Requirements")
    job_description = st.text_area(
        "Paste the Job Description or key skills you are looking for here:",
        placeholder="e.g., Looking for a video editor who knows Premiere Pro and After Effects...",
        height=200
    )

# Step 2: Upload Files
with st.container():
    st.header("Step 2: Upload Resumes")
    uploaded_files = st.file_uploader(
        "Drag and drop resume files (PNG, JPG, JPEG, DOCX, PDF):", 
        type=["png", "jpg", "jpeg", "docx", "pdf"], 
        accept_multiple_files=True
    )

# Step 3: Run Engine
with st.container():
    st.header("Step 3: Process and Rank")

    if st.button("🚀 Run AI Ranking Engine"):
        if not job_description:
            st.error("Please enter a job description first!")
        elif not uploaded_files:
            st.error("Please upload at least one resume!")
        else:
            results = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
        
            for index, file in enumerate(uploaded_files):
                with st.spinner(f"Processing resume {index + 1} of {len(uploaded_files)}: {file.name}..."):
                    temp_path = os.path.join(resume_sorter.temp_dir, file.name)
                    with open(temp_path, "wb") as f:
                        f.write(file.getbuffer())
                
                    is_image = file.type not in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
                    
                    ocr_success = False
                    text = ""
                    
                    if is_image:
                        # Try OCR first
                        try:
                            configure_tesseract()
                            text = pytesseract.image_to_string(Image.open(temp_path))
                            if text.strip():
                                ocr_success = True
                        except Exception:
                            pass
                            
                    if not is_image or ocr_success:
                        if not is_image:
                            if file.type == "application/pdf":
                                text = resume_sorter.extract_text_from_pdf(temp_path)
                            else:
                                text = resume_sorter.extract_text_from_docx(temp_path)
                            
                        prompt_text = f"""
                        You are an expert HR assistant. Analyze this resume against the following Job Description.
                        
                        RESUME TEXT:
                        {text}
                        
                        JOB DESCRIPTION:
                        {job_description}
                        
                        INSTRUCTIONS:
                        1. Assign a Score out of 100 based on how well the candidate matches the job description.
                        2. Provide a 1-sentence summary explanation of their core skills.
                        
                        OUTPUT FORMAT:
                        You MUST reply ONLY in this format. Do not write an introduction or conclusion.
                        Score: [Insert number here]
                        Summary: [Insert summary here]
                        """
                    else:
                        prompt_text = f"""
                        You are an expert HR assistant. Analyze the attached resume image against the following Job Description.
                        
                        JOB DESCRIPTION:
                        {job_description}
                        
                        INSTRUCTIONS:
                        1. Assign a Score out of 100 based on how well the candidate matches the job description.
                        2. Provide a 1-sentence summary explanation of their core skills.
                        
                        OUTPUT FORMAT:
                        You MUST reply ONLY in this format. Do not write an introduction or conclusion.
                        Score: [Insert number here]
                        Summary: [Insert summary here]
                        """
                
                    try:
                        generate_args = {
                            "model": selected_model,
                            "prompt": prompt_text,
                            "options": {
                                "num_ctx": 2048,
                                "num_gpu": 99
                            }
                        }
                        if is_image and not ocr_success:
                            generate_args["images"] = [temp_path]
                            
                        response = ollama.generate(**generate_args)
                    
                        output = response['response']
                        score, summary = parse_response(output)
                    
                        results.append({"Candidate Name": file.name, "Score / 100": score, "AI Summary": summary})
                    
                    except Exception as e:
                        err_str = str(e).lower()
                        if "image" in err_str or "multimodal" in err_str or "projector" in err_str or "vision" in err_str:
                            st.error(
                                f"Error processing {file.name}: The selected model '{selected_model}' is not a vision-enabled model and cannot process image files directly, and Tesseract OCR was not found on your system.\n\n"
                                "To scan images, please do one of the following:\n"
                                "1. **Install Tesseract OCR**: Download and install Tesseract OCR (e.g., from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)). Once installed, the application will automatically extract text from image files and score them using your selected model.\n"
                                "2. **Use a Vision Model**: Pull a vision model in Ollama by running:\n"
                                "   `ollama pull moondream` (recommended, 829MB) or `ollama pull llama3.2-vision` (7.9GB)\n"
                                "   Then, select that vision model in the sidebar configuration."
                            )
                        else:
                            st.error(f"Error processing {file.name}: {e}")
                
                progress_bar.progress((index + 1) / len(uploaded_files))
            
            status_text.success("🎉 All resumes processed successfully!")
        
            sorted_results = sorted(results, key=lambda x: x["Score / 100"], reverse=True)
        
            st.subheader("📊 AI Leaderboard Ranking Results")
            st.dataframe(sorted_results, use_container_width=True)
