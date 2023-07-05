import base64

def decode_with_charset(charset, raw_content):
    decoded_content = ""
    if charset.find("UTF-8") != -1:
        decoded_content = base64.urlsafe_b64decode(raw_content).decode('UTF-8')
    elif (charset.find("utf-8") != -1):
        decoded_content = base64.urlsafe_b64decode(raw_content).decode('utf-8')
    return (decoded_content)

def print_mail_error(email_skip_content, email_skip_decode):
    if email_skip_decode > 0:
        print(f"Error: {email_skip_decode} email were skip because impossible to decode (not UTF-8 or utf-8).")
    if email_skip_content > 0:
        print(f"Error: {email_skip_content} email were skip because the body is empty (no content).")

#############################################

def fill_string(all_email, mailbox):
    email_string = ""
    email_skip = 0
    too_many_mail = 0
    for email_entry in all_email:

        if mailbox == "sent":
            mail_len = len( f"To: {email_entry['To']}\n" + f"Date: {email_entry['Date']}\n" + f"Content:\n{email_entry['Content']}\n" + f"{email_entry['SEPARATOR']}\n")
        else:
            mail_len = len( f"From: {email_entry['From']}\n" + f"Date: {email_entry['Date']}\n" + f"Content:\n{email_entry['Content']}\n" + f"{email_entry['SEPARATOR']}\n")
        if (mail_len > 3000):
            email_skip += 1
            continue

        total_len = len(email_string) + mail_len
        if total_len >= 4000:
            email_skip += 1
            break
        
        email_string += fill_template(email_entry, mailbox)
    if too_many_mail == 1:
        print(f"Too many email for one prompt. {email_skip} email has been skip.")
    elif email_skip > 0:
        print(f"Some email has too many character. {email_skip} email has been skip")
    return (email_string)

def fill_template(email_entry, mailbox):
    new_string = ""
    if mailbox == "sent":
        new_string += f"To: {email_entry['To']}\n"
    else:
        new_string += f"From: {email_entry['From']}\n"
    new_string += f"Date: {email_entry['Date']}\n"
    new_string += f"Content:\n{email_entry['Content']}\n"
    new_string += f"{email_entry['SEPARATOR']}\n"
    return (new_string)

#############################################

def select_query(keyword, mailbox, date):
    new_query = ""
    if keyword and date:
        new_query = f"{keyword} in:{mailbox} after:{date}"
    elif keyword:
        new_query = f"{keyword} in:{mailbox}"
    elif date:
        new_query = f"after:{date} in:{mailbox}"
    else:
        new_query = f"in:{mailbox}"
    return (new_query)

def number_of_email_found(messages, keyword, date, mailbox):
    if keyword and date:
        print("Found", len(messages), "email with keyword", keyword, "after date", date, "in mailbox", mailbox)
    elif keyword:
        print("Found", len(messages), "email with keyword", keyword, "in mailbox", mailbox)
    elif date:
        print("Found", len(messages), "email after date", date, "in mailbox", mailbox)
    else:
        print("Found", len(messages), "email in mailbox", mailbox)