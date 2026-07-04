import streamlit as st
import ollama
import os
from PIL import Image
from docx import Document
import pdfplumber
from PyPDF2 import PdfReader
import pytesseract

class ResumeSorter:
    def __init__(self):
        self.temp_dir = "temp_resumes"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def extract_text_from_pdf(self, pdf_path):
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
        return text
    
    def extract_text_from_docx(self, docx_path):
        doc = Document(docx_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text

# Set up the look of the website
st.set_page_config(page_title="AI Resume Sorter", page_icon="📄", layout="wide")

# Create an instance of the class
resume_sorter = ResumeSorter()

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
                
                    if file.type == "application/pdf":
                        text = resume_sorter.extract_text_from_pdf(temp_path)
                    elif file.type == "application/msword" or file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        text = resume_sorter.extract_text_from_docx(temp_path)
                    else:
                        with Image.open(temp_path) as img:
                            # Use OCR to extract text from the image
                            text = pytesseract.image_to_string(img, lang='eng')
                    
                    prompt_text = f"""
                    You are an expert HR assistant. Analyze this resume against the following Job Description.
                    
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
                        response = ollama.generate(
                            model='gemma4:e4b',
                            prompt=prompt_text,
                            images=[temp_path],
                            options={
                                "num_ctx": 2048,
                                "num_gpu": 99
                            }
                        )
                    
                        output = response['response']
                        score, summary = self.parse_response(output)
                    
                        results.append({"Candidate Name": file.name, "Score / 100": score, "AI Summary": summary})
                    
                    except Exception as e:
                        st.error(f"Error processing {file.name}: {e}")
                
                progress_bar.progress((index + 1) / len(uploaded_files))
            
            status_text.success("🎉 All resumes processed successfully!")
        
            sorted_results = sorted(results, key=lambda x: x["Score / 100"], reverse=True)
        
            st.subheader("📊 AI Leaderboard Ranking Results")
            st.dataframe(sorted_results, use_container_width=True)

# Helper functions
def parse_response(response):
    lines = response.split('\n')
    score = int(lines[0].split(': ')[1])
    summary = lines[1].split(': ')[1]
    return score, summary

# Sidebar options
with st.sidebar:
    with st.container():
        st.header("Additional Options")
        if st.button("Save Results as CSV"):
            import pandas as pd
            df = pd.DataFrame(results)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name='resume_rankings.csv',
                mime='text/csv',
            )

        if st.button("Clear Cache"):
            if os.path.exists(resume_sorter.temp_dir):
                for filename in os.listdir(resume_sorter.temp_dir):
                    os.remove(os.path.join(resume_sorter.temp_dir, filename))
                os.rmdir(resume_sorter.temp_dir)
            st.experimental_rerun()
