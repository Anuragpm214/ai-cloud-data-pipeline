import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_document():
    doc = docx.Document()

    # Set standard margins (1 inch)
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # --- TITLE & SUBTITLE ---
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title.add_run("AI-Powered Cloud Data Pipeline")
    run_title.font.size = Pt(24)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D) # Navy Blue
    title.paragraph_format.space_after = Pt(4)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = sub.add_run("Complete Interview Preparation Guide & System Architecture")
    run_sub.font.size = Pt(13)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    sub.paragraph_format.space_after = Pt(20)

    # Divider Box
    div_table = doc.add_table(rows=1, cols=1)
    div_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = div_table.rows[0].cells[0]
    set_cell_background(cell, "EBF3FA")
    set_cell_margins(cell, top=120, bottom=120, left=200, right=200)
    p = cell.paragraphs[0]
    p.add_run("Tech Stack: ").bold = True
    p.add_run("Python 3.11 | FastAPI | AWS S3 | AWS Lambda / SQS | AWS DynamoDB | PyTorch | Docker | LocalStack")
    p.runs[0].font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # --- SECTION 1: ELEVATOR PITCH ---
    h1 = doc.add_heading("1. Project Overview (Elevator Pitch for Interviewer)", level=1)
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(6)

    p = doc.add_paragraph()
    p.add_run("How to explain this project in 30 seconds:\n").bold = True
    p.add_run(
        "\"I designed and built an event-driven, scalable Cloud Data Pipeline using FastAPI, AWS S3, AWS DynamoDB, "
        "and PyTorch. It ingests structured (CSV/JSON) and unstructured (Text) datasets, automatically validates and transforms "
        "them into columnar Parquet format in the background, and triggers a containerized PyTorch deep learning model to run "
        "real-time and batch predictions. The system is completely decoupled using AWS S3 and SQS, ensuring zero API latency, "
        "high throughput, and resilient metadata tracking in DynamoDB without risk of Out-Of-Memory (OOM) crashes.\""
    )

    # --- SECTION 2: ARCHITECTURE & SYSTEM DESIGN ---
    h1 = doc.add_heading("2. System Architecture & End-to-End Workflow", level=1)
    h1.paragraph_format.space_before = Pt(16)
    h1.paragraph_format.space_after = Pt(6)

    p = doc.add_paragraph()
    p.add_run("The architecture consists of 4 decoupled layers:\n").bold = True

    # Visual Architecture Box
    arch_table = doc.add_table(rows=5, cols=2)
    arch_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    arch_table.autofit = False

    layers = [
        ("Layer 1: Ingestion Gateway\n(FastAPI)", "Accepts multipart file uploads & generates Presigned S3 URLs for large datasets. Immediately saves raw data to S3 and registers job metadata in DynamoDB with status UPLOADED."),
        ("Layer 2: Event Queue & Decoupling\n(AWS SQS / S3 Events)", "Emits asynchronous events upon file arrival. Decouples the user-facing API from heavy background transformation workloads."),
        ("Layer 3: ETL & Validation Worker\n(AWS Lambda / Worker)", "Picks messages from SQS, downloads raw data from S3, validates schema, imputes missing values, converts data to optimized Parquet format, and uploads to S3 Processed Bucket."),
        ("Layer 4: AI Inference Engine\n(PyTorch Service)", "Reads processed Parquet datasets, executes PyTorch Deep Learning forward pass, computes confidence scores, and stores predictions in DynamoDB."),
        ("Layer 5: Client Retrieval\n(REST API)", "Clients query GET /api/v1/jobs/{job_id} to fetch real-time job status, transformation profiling metrics, and final model predictions.")
    ]

    for idx, (layer_title, layer_desc) in enumerate(layers):
        row = arch_table.rows[idx]
        cell_0 = row.cells[0]
        cell_1 = row.cells[1]

        cell_0.width = Inches(2.2)
        cell_1.width = Inches(4.5)

        set_cell_background(cell_0, "F0F4F8" if idx % 2 == 0 else "E8EEF5")
        set_cell_background(cell_1, "FAFAFA" if idx % 2 == 0 else "FFFFFF")

        set_cell_margins(cell_0, top=100, bottom=100, left=150, right=150)
        set_cell_margins(cell_1, top=100, bottom=100, left=150, right=150)

        p0 = cell_0.paragraphs[0]
        p0.add_run(layer_title).bold = True
        p0.runs[0].font.size = Pt(10)
        p0.runs[0].font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)

        p1 = cell_1.paragraphs[0]
        p1.add_run(layer_desc)
        p1.runs[0].font.size = Pt(10)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # --- SECTION 3: STEP-BY-STEP REAL-WORLD EXAMPLE ---
    h1 = doc.add_heading("3. Step-by-Step Real-World Example (Loan / Fraud Risk)", level=1)
    h1.paragraph_format.space_before = Pt(16)
    h1.paragraph_format.space_after = Pt(6)

    p = doc.add_paragraph()
    p.add_run("Scenario: ").bold = True
    p.add_run("A banking client uploads a batch of 100,000 customer financial records to predict credit default risk.")

    steps = [
        ("Step 1: Ingestion API Call", "The client sends a POST request to /api/v1/upload with customer_records.csv. FastAPI writes the file directly to S3 bucket (s3://raw-data-bucket/structured/job101_customer_records.csv), registers job_101 in DynamoDB, and sends a notification to SQS. The API returns HTTP 200 with job_id: job_101 in under 200ms."),
        ("Step 2: Serverless Transformation", "The Pipeline Worker reads the SQS message, downloads the raw CSV from S3, fixes missing age/income values using median imputation, standardizes headers, and converts the dataset to compressed Parquet format. It stores the Parquet file in s3://processed-data-bucket/processed/job101/data.parquet and updates DynamoDB status to TRANSFORMED."),
        ("Step 3: PyTorch Neural Network Inference", "The PyTorch Inference Service is triggered. It loads the Parquet dataset and runs a Tabular Neural Network with BatchNorm and Dropout layers. It generates predictions (LOW_RISK or HIGH_RISK) along with confidence scores (e.g. 96.4%)."),
        ("Step 4: Persistence & Retrieval", "All predictions are stored into the DynamoDB ModelPredictions table, and job_101 is marked as INFERENCE_COMPLETED. When the client polls GET /api/v1/jobs/job101, they receive the full prediction breakdown.")
    ]

    for title_text, desc_text in steps:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f"{title_text}: ").bold = True
        p.add_run(desc_text)
        p.paragraph_format.space_after = Pt(4)

    # --- SECTION 4: KEY BENEFITS ---
    h1 = doc.add_heading("4. Key Benefits & Why This Architecture Was Chosen", level=1)
    h1.paragraph_format.space_before = Pt(16)
    h1.paragraph_format.space_after = Pt(6)

    benefits = [
        ("1. Zero API Timeout & Low Latency", "By decoupling ingestion from processing via S3 and SQS, API endpoints respond immediately. The user never waits for long-running compute jobs."),
        ("2. Prevention of Out-Of-Memory (OOM) Errors", "Large datasets are streamed directly into AWS S3 using presigned URLs or chunked uploads rather than being buffered entirely in the API server's RAM."),
        ("3. Storage & Analytics Optimization (Parquet Format)", "Converting raw CSV/JSON to columnar Parquet format reduces storage footprint by 60-80% and accelerates PyTorch data loading speed by over 10x."),
        ("4. Horizontal Auto-Scalability", "AWS S3, SQS, and serverless workers scale automatically to handle millions of simultaneous files without manual infrastructure management."),
        ("5. Cost Efficiency (Pay-As-You-Go)", "Heavy AI compute and ETL resources are spun up only when data arrives, eliminating the cost of 24/7 idle high-performance compute instances.")
    ]

    for title_text, desc_text in benefits:
        p = doc.add_paragraph()
        p.add_run(f"• {title_text}: ").bold = True
        p.add_run(desc_text)
        p.paragraph_format.space_after = Pt(4)

    # --- SECTION 5: TOP INTERVIEW QUESTIONS & ANSWERS ---
    h1 = doc.add_heading("5. Top Technical Interview Questions & Model Answers", level=1)
    h1.paragraph_format.space_before = Pt(16)
    h1.paragraph_format.space_after = Pt(6)

    qas = [
        (
            "Q1: Why did you choose an asynchronous event-driven architecture instead of processing data directly inside FastAPI?",
            "Answer: Synchronous processing in FastAPI would tie up worker threads, increase memory usage, and lead to HTTP request timeouts on large datasets (e.g. 500MB+ files). By offloading processing to S3, SQS, and background workers, the API remains highly responsive, lightweight, and resilient to traffic spikes."
        ),
        (
            "Q2: How does the pipeline handle very large files (e.g. 10GB) without causing Out-Of-Memory (OOM)?",
            "Answer: We implement Presigned S3 URLs which allow clients to upload datasets directly to S3 without routing traffic through the API server. In the processing layer, datasets are processed in streaming batches and converted into Parquet format, avoiding loading the entire dataset into memory at once."
        ),
        (
            "Q3: Why did you choose DynamoDB for metadata and prediction storage instead of a relational database (PostgreSQL)?",
            "Answer: DynamoDB provides single-digit millisecond latency at any scale with seamless horizontal partitioning. In an event-driven pipeline where workers write state concurrently and clients query by job_id, DynamoDB's key-value and Global Secondary Index (GSI) model is faster, serverless, and maintenance-free."
        ),
        (
            "Q4: How is the PyTorch model served and containerized?",
            "Answer: The PyTorch inference service is wrapped with FastAPI and containerized using Docker with CPU/CUDA optimization. It supports both single real-time inference (/predict/realtime) and high-throughput batch inference (/predict/batch) directly reading from S3 Parquet artifacts."
        )
    ]

    for q, a in qas:
        p = doc.add_paragraph()
        p.add_run(f"{q}\n").bold = True
        p.runs[0].font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
        p.add_run(a)
        p.paragraph_format.space_after = Pt(8)

    # Save document
    output_filename = "AI_Powered_Cloud_Data_Pipeline_Interview_Guide.docx"
    doc.save(output_filename)
    print(f"[+] Document created successfully: {output_filename}")

if __name__ == "__main__":
    create_document()
