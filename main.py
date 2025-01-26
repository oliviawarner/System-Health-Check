import psutil
import csv
import smtplib
import platform
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# Load environment variables from GitHub Secrets or .env file
load_dotenv()
EMAIL = os.getenv('EMAIL')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL')

if not EMAIL or not EMAIL_PASSWORD or not RECEIVER_EMAIL:
    print("Error: Missing required environment variables.")
    exit()

ALERT_THRESHOLD = 80  # Set the CPU usage threshold

# Function to collect system health metrics and trigger alerts
def get_system_health():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    if cpu_usage > ALERT_THRESHOLD:
        send_alert_email(cpu_usage, memory.percent, disk.percent)

    return {
        "cpu": cpu_usage,
        "memory": memory.percent,
        "disk": disk.percent
    }

# Function to log metrics to a CSV file
def log_metrics(data):
    with open("system_health_log.csv", "a") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), data["cpu"], data["memory"], data["disk"], platform.system()])

# Function to generate a graph snapshot
def generate_graph_snapshot():
    df = pd.read_csv('system_health_log.csv', names=['timestamp', 'cpu', 'memory', 'disk', 'os'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    df = df.dropna().sort_values('timestamp')

    plt.figure(figsize=(8, 4))
    plt.plot(df['timestamp'], df['cpu'], label='CPU Usage')
    plt.plot(df['timestamp'], df['memory'], label='Memory Usage')
    plt.plot(df['timestamp'], df['disk'], label='Disk Usage')
    plt.xlabel('Time')
    plt.ylabel('Usage (%)')
    plt.title('System Health Over Time')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    graph_path = "system_health_graph.png"
    plt.savefig(graph_path)
    plt.close()
    return graph_path

# Function to generate a PDF report with graph
def generate_report_with_graph(cpu, memory, disk, os_name):
    report_filename = "system_health_report.pdf"
    doc = SimpleDocTemplate(report_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("System Health Report", styles['Title']))
    elements.append(Spacer(1, 20))
    summary = f"""
        <b>Operating System:</b> {os_name} <br/>
        <b>CPU Usage:</b> {cpu}% <br/>
        <b>Memory Usage:</b> {memory}% <br/>
        <b>Disk Usage:</b> {disk}%
    """
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 20))

    graph_image = generate_graph_snapshot()
    elements.append(Image(graph_image, width=400, height=300))

    doc.build(elements)
    print(f"Report with graph generated: {report_filename}")
    return report_filename

# Function to send email report with attachment
def send_email_report(report_file):
    sender_email = EMAIL
    receiver_email = RECEIVER_EMAIL
    password = EMAIL_PASSWORD
    current_date = datetime.now().strftime('%Y-%m-%d')

    if os.path.exists(report_file):
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"Automated System Health Report - {current_date}"

        body = "Please find the attached system health report."
        msg.attach(MIMEText(body, 'plain'))

        with open(report_file, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(report_file)}")
            msg.attach(part)

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, password)
            text = msg.as_string()
            server.sendmail(sender_email, receiver_email, text)
            server.quit()
            print("Email sent successfully.")
            os.remove(report_file)  # Delete report after sending to prevent resending
        except Exception as e:
            print(f"Failed to send email: {e}")

# Collect and log system metrics
health_data = get_system_health()
os_name = platform.system()
log_metrics(health_data)
report_file = generate_report_with_graph(health_data['cpu'], health_data['memory'], health_data['disk'], os_name)
send_email_report(report_file)
