import os
from apikey import apikey_openai
from apikey import apikey_serpapi
os.environ["OPENAI_API_KEY"] = apikey_openai
os.environ["SERPAPI_API_KEY"] = apikey_serpapi

import openai
import base64
import json

from openai.error import ServiceUnavailableError
from datetime import date
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from AI_function import decode_with_charset, print_mail_error, fill_string, select_query, number_of_email_found

openai.api_key = os.getenv("OPENAI_API_KEY")
SCOPES = ['https://mail.google.com/']

global today
global signature
global language
global MAX_EMAIL

# The signature at the end of each email
signature = "Jacob"

# The language the AI should answer
language = "french"

# The maximum number of email that will be retrive per request.
MAX_EMAIL = 20

today = date.today()


##################################################
# Build gmail service and create token.json file #
##################################################

creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

service = build('gmail', 'v1', credentials=creds)

###########################################################################

#################################################
# Create draft with info give by the chat model #
#################################################

def create_draft(to, subject, body):
    message = MIMEText(body)

    # Add email headers
    message['to'] = to
    message['subject'] = subject

    # Convert the message to a string
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Create draft
    draft = service.users().drafts().create(
        userId='me',
        body={'message': {'raw': raw_message}}
    ).execute()
    return draft["id"]

###########################################################################

#######################################################
# Search Email with a specific keyword, email or date #
#######################################################

def search_email(keyword, mailbox, date):
    query = select_query(keyword, mailbox, date)
    if (mailbox == "draft"):
        response = service.users().drafts().list(
        userId='me',
        q=query,
        maxResults= MAX_EMAIL
        ).execute()
        messages = response.get('drafts', [])
    else:
        response = service.users().messages().list(
            userId='me',
            q=query,
            maxResults= MAX_EMAIL,
        ).execute()
        messages = response.get('messages', [])
    number_of_email_found(messages, keyword, date, mailbox)
    return messages

###########################################################################

#################################################################
# Retrieve information from all the email found in search_email #
#################################################################

def get_email_information(all_email_ids, mailbox):
    email_skip_content = 0
    email_skip_decode = 0
    all_email = []
    separator = "------"
    for email in all_email_ids:
        email_id = email['id']
        if (mailbox == "draft"):
            email_info = service.users().drafts().get(
                userId='me',
                id=email_id
            ).execute()
            full_message_info = email_info.get("message")
            message_info = full_message_info.get("payload")
            mailbox_ids = full_message_info.get('labelIds')
        else:
            email_info = service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
            message_info = email_info.get('payload')
            mailbox_ids = email_info.get('labelIds')

        # Extract Email information. From, To, Subject and Date
        headers = message_info.get('headers', [])
        sender = next((header['value'] for header in headers if header['name'] == 'From'), None)
        if not sender:
            sender = "Unknown Sender"
        recipient = next((header['value'] for header in headers if header['name'] == 'To'), None)
        if not recipient:
            recipient = "Unknown Recipient"
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), None)
        if not subject:
            subject = "(no subject)"
        date = next((header['value'] for header in headers if header['name'] == 'Date'), "")
        
        try:
            if "SENT" in mailbox_ids or "DRAFT" in mailbox_ids:
                body = message_info.get('body')
            else:
                body = message_info.get('parts')[0].get('body')
            if 'data' in body:
                raw_content = body['data']
            else:
                email_skip_content += 1
                continue
        except TypeError:
            print(f"Can't access email body, This email will be skip: {subject}")
            continue
        
        if "SENT" in mailbox_ids or "DRAFT" in mailbox_ids:
            charset =  next((header['value'] for header in headers if header['name'] == 'Content-Type'), None)
        else:
            charset_part = message_info.get('parts')[1]
            charset = next((header['value'] for header in charset_part['headers'] if header['name'] == 'Content-Type'), None)

        decoded_content = decode_with_charset(charset, raw_content)
        if not decoded_content:
            email_skip_decode += 1
            continue

        email_entry = {
            "From": sender,
            "To": recipient,
            "Subject": subject,
            "Date": date,
            "Content": decoded_content,
            "SEPARATOR": separator
        }
        all_email.append(email_entry)

    email_string = ""
    email_string = fill_string(all_email, mailbox)
    print_mail_error(email_skip_content, email_skip_decode)
    return email_string
###########################################################################

######################################################
# Create a response to the query with the email list #
######################################################

def response_to_query_with_mail(all_email_info, original_prompt):
        if not all_email_info:
            all_email_info = "<Empty List>"
        try:
            chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                # "role": "system", "content": f"You are my VIRTUAL assistant. We have a LIVE conversation so DO NOT formulate as an email. Do not just throw email, comment it.",
                "role": "user", "content": f"You are my Virtual Assistant and I will ask you query. Answer querys with the help of the email list that will follow. You MUST answer in {language}. The email list will be in ordrer from most recent  to least recent. \nThe Query: {original_prompt}\n\nMy Email List: {all_email_info}"
                # "role":"user", f"content": "Each email is separate with these character: ------. When giving an email, give the field name only if you think it is necessary. Each email can contain these field: From: Who sent me this email, Date: The day I recieved this email, Content: The body, the main content of the email, To: To who the email is send. The email will be in ordrer from most recent to least recent. Please provide concise answers to the following request using the email list and giving your answer in {language}: \n\n" + original_prompt + "\n\nEmail list: \n" + all_email_info
            }]
            )
        except ServiceUnavailableError:
            print("Error: OpenAI server are overloaded or not ready yet. Please try again later.")
            return (None)
        # print("Token usage response_to_query_with_mail: " + str(chat_completion["usage"]["total_tokens"]))
        return (chat_completion["choices"][0]["message"]["content"])

###########################################################################

###########################################################################
# Main function, Run ChatModel and look at which function has been choose #
###########################################################################

def run_conversation(_query):
    # Everything related to the AI
    _message = [{
        "role":"system", "content" : "You are a Virtual Assistant that will be given the access to my a list of my mail. Your only purpose is to help for productivity and provide information you have access with the email list. You MUST give your answer in {language}",
        "role":"user", "content" : _query
        }]
    _function_mail = [
        {
            "name": "create_draft",
            "description": "This function is used to create a draft for an email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "The email address of the receiver, e.g., example@gmail.com."
                    },
                    "subject": {
                        "type": "string",
                        "description": "The subject of the email."
                    },
                    "body": {
                        "type": "string",
                        "description": f"The content of the email. If you sign it, the signature will always be: {signature}"
                    }
                },
                "required": ["subject", "body"]
            }
        },
        {
            "name": "search_email",
            "description": "This function is used to retrieve information from the mailbox. It need to be explicitly specify to search in my gmail.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "A keyword ONLY use when the query is searching for a subject (e.g. ONLY: email, name, company name, event). It CAN'T be a mail category: draft, inbox, anywhere, sent, spam, trash."
                    },
                    "mailbox": {
                        "type": "string",
                        "description": "Specify the mailbox to search in. Valid options are: anywhere (DEFAULT categories), draft (drafts only), sent (emails sent by me), inbox (standard), unread (unread email), spam, or trash. If the query is referring to another mailbox, provide the appropriate value. By default, you should give 'anywhere'."
                    },
                    # "date": {
                    #     "type": "string",
                    #     "description": "a date in format YYYY/MM/DD ONLY use when the query is asking for a specific DATE (A moment like today, yesterday does NOT need a date). It NEEDS to be blank if no DATE is specify in the query."
                    # }
                },
                "required": ["mailbox"]
            }
        }
    ]
    try:
        chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=_message,
            functions=_function_mail,
            )
    except ServiceUnavailableError:
        print("Error: OpenAI server are overloaded or not ready yet. Please try again later.")
        return
    finish_reason = chat_completion["choices"][0]["finish_reason"]
    final_answer = ""
    if (finish_reason == "function_call"):
        function_called = chat_completion["choices"][0]["message"]["function_call"]["name"]
        arguments = json.loads(chat_completion["choices"][0]["message"]["function_call"]["arguments"])
        if (function_called == "create_draft"):
            to = arguments.get("to")
            if not to:
                to = "example@gmail.com"
            subject = arguments.get("subject")
            body = arguments.get("body")
            draft_id = create_draft(to, subject, body)
            final_answer = "Draft created with ID:" + draft_id
        elif (function_called == "search_email"):
            keyword = arguments.get("keyword")
            mailbox = arguments.get("mailbox")
            date = None
            all_email_id = search_email(keyword, mailbox, date)
            if all_email_id:
                all_email_info = get_email_information(all_email_id, mailbox)
                final_answer = response_to_query_with_mail(all_email_info, _query)
            else:
                print("No emails found matching the search query.")
        else:
            print("ERROR\nFunction name not recognized.")
    else:
        final_answer = chat_completion["choices"][0]["message"]["content"]
    if (final_answer):
        print(final_answer)
    # print("Token usage in main: " + str(chat_completion["usage"]["total_tokens"]))

###########################################################################
