from flask import Flask, request, jsonify
import json
import ollama # <--- Add this line
from fpdf import FPDF # <--- Add this line
from postmarker.core import PostmarkClient
import base64 # <--- Add this line for encoding the PDF


app = Flask(__name__)

OLLAMA_MODEL = "phi3:mini" # <--- IMPORTANT: Use the exact model name you pulled and tested!
# --- Postmark Outbound Configuration ---
POSTMARK_SERVER_API_TOKEN = "e3201578-2f3c-4eac-9603-20d48eb5fbd3" # Replace with your actual Server API Token
SENDER_EMAIL = "bb1291@srmist.edu.in" # Use a verified Sender Signature email address in Postmark
# --- END Postmark Outbound Configuration ---

@app.route('/webhook', methods=['POST'])
def receive_postmark_webhook():
    # Ensure the request is JSON
    if not request.is_json:
        print("Received a request that is not JSON.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    # Get the JSON payload sent by Postmark
    postmark_payload = request.get_json()

    print("\n--- Received Postmark Webhook Payload ---")
    # Pretty print the entire payload for easy viewing in your terminal
    print(json.dumps(postmark_payload, indent=2))
    print("-----------------------------------------\n")

    # --- Extracting Key Information from the Inbound Email ---
    # Get the sender's email address
# --- Extracting Key Information from the Inbound Email ---
    sender_email = None
    sender_full_list = postmark_payload.get('FromFull')
    if sender_full_list and isinstance(sender_full_list, list) and len(sender_full_list) > 0:
        sender_email = sender_full_list[0].get('Email')
    else:
        # Fallback if FromFull is missing or empty, try 'From' header
        sender_email = postmark_payload.get('From')

    # Get the subject of the email
    subject = postmark_payload.get('Subject')

    # Get the plain text body of the email (this is where the homework question will be)
    text_body = postmark_payload.get('TextBody')

    print(f"Sender Email: {sender_email}")
    print(f"Subject: {subject}")
    print(f"Homework Question (Text Body): {text_body}")

    # --- Your Homework Bot Logic Will Go Here ---
    # --- Your Homework Bot Logic Goes Here ---
    solution_text = "Sorry, I couldn't process your request." # Default fallback message

    try:
        # Send the homework question to Ollama
        ollama_response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': text_body}], # Use the extracted text_body as the prompt
            stream=False # We want the full response at once
        )
        solution_text = ollama_response['message']['content']
        print("\n--- Ollama's Solution ---")
        print(solution_text)
        print("-------------------------\n")

    except Exception as e:
        print(f"Error calling Ollama: {e}")
        solution_text = f"An error occurred while getting the solution: {e}"


    # --- Next steps will be PDF generation and sending email ---

    # --- PDF Generation ---
# ... (code before PDF Generation) ...

# --- PDF Generation ---
# ... (code before PDF Generation) ...

# --- PDF Generation ---
    pdf = FPDF(format='A4', unit='mm')
    pdf.add_page()

    # Set margins explicitly (e.g., 10mm all around)
    pdf.set_left_margin(10)
    pdf.set_right_margin(10)
    pdf.set_top_margin(10)
    pdf.set_auto_page_break(auto=True, margin=10)

    # Define the absolute path to your font file
    FONT_PATH = "/Users/bbhavna/Desktop/postmark/homework-bot/DejaVuSans.ttf" # <--- IMPORTANT: Verify this path!

    # Load the Unicode font using its absolute path
    pdf.add_font('DejaVuSans', '', FONT_PATH, uni=True)
    pdf.set_font("DejaVuSans", size=12)

    # Calculate available width for content
    available_width = pdf.w - pdf.l_margin - pdf.r_margin

    # Set the starting X position to the left margin for the first block
    pdf.set_x(pdf.l_margin) # <--- ADD/CONFIRM THIS LINE
    pdf.set_y(pdf.t_margin) # Keep this if you have it, ensures starting at top

    # Add the homework question to the PDF
    pdf.multi_cell(available_width, 10, txt=f"Homework Question:\n{text_body}\n\n", align='L')

    # Add a bit of vertical space before the solution
    pdf.ln(5)

    # --- CRUCIAL FIXES HERE ---
    # Reset X position to the left margin before the "Ollama's Solution" heading
    pdf.set_x(pdf.l_margin) # <--- ADD THIS LINE
    pdf.multi_cell(available_width, 10, txt="Ollama's Solution:", align='L')

    # Reset X position to the left margin before the actual solution text
    pdf.set_x(pdf.l_margin) # <--- ADD THIS LINE
    pdf.multi_cell(available_width, 10, txt=solution_text, align='L')
    # --- END CRUCIAL FIXES ---

    # Define the output path for the PDF
    pdf_output_path = "homework_solution.pdf"
    pdf.output(pdf_output_path)
    print(f"PDF created: {pdf_output_path}")

# --- END PDF Generation ---
        # ... (PDF Generation code, ending with print(f"PDF created: {pdf_output_path}") ) ...

    # --- Email Sending with Postmark ---
# ... (code before Email Sending block, including PDF generation) ...

# --- Email Sending with Postmarker ---
    try:
        with open(pdf_output_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('ascii')

        # Initialize Postmark client with your server API token (using PostmarkClient from postmarker)
        # Note: Variable name is 'postmark_client' for consistency, matching your docs' 'postmark'
        postmark_client = PostmarkClient(server_token=POSTMARK_SERVER_API_TOKEN) # <--- Initializing the client

        # Send the email using the client's emails.send method
        response = postmark_client.emails.send( # <--- Sending the email
            From=SENDER_EMAIL,
            To=sender_email,
            Subject=f"Your Homework Solution for: {subject}",
            TextBody=f"Hi there,\n\nHere is the solution to your homework question:\n\n{text_body}\n\n"
                    f"The full solution is attached as a PDF.\n\n"
                    f"Best regards,\nYour Homework Bot",
            # Attachments list is directly part of the send call
            Attachments=[{
                "Name": "homework_solution.pdf",
                "Content": pdf_base64,
                "ContentType": "application/pdf"
            }]
        )
        print(f"Postmark API Response: {response}") # <--- Optional: print Postmark's response for debugging
        print(f"Solution email sent to: {sender_email}")

    except Exception as e:
        print(f"Error sending email via Postmark: {e}")
        return jsonify({"status": "error", "message": f"Webhook processed, PDF created, but email failed: {e}"}), 500

    # --- END Email Sending ---

    # Final return statement (if email sending was successful)
    return jsonify({"status": "success", "message": "Webhook received, processed, PDF created, and email sent", "solution": solution_text, "pdf_file": pdf_output_path}), 200

# ... (rest of your app.py) ...
    # --- END Email Sending ---

    # Final return statement (if email sending was successful)
    return jsonify({"status": "success", "message": "Webhook received, processed, PDF created, and email sent", "solution": solution_text, "pdf_file": pdf_output_path}), 200


# --- END PDF Generation ---









if __name__ == '__main__':
    print("Flask app starting. Listening for webhooks on /webhook...")
    print("Remember to use ngrok to expose this to the internet!")
    app.run(debug=True, port=5000) # Runs on http://127.0.0.1:5000 by default