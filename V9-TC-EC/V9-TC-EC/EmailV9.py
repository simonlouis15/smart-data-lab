import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject, body, to_email):
    from_email = "thermalsdl@gmail.com"
    password = "vtgg kmii epal bvzl"  # better to use an app password if using Gmail

    # Build the email
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Connect to the SMTP server (example: Gmail)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print("Error sending email:", e)

# Example usage
'''
condition = True  # replace with your own condition
if condition:
    send_email("Alert!", "Something happened!", "m93.ebrahimiazar@gmail.com")
'''