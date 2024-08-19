import win32com.client

def check_outlook_inbox(label):
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    inbox = outlook.GetDefaultFolder(6)  # 6 refers to the inbox
    messages = inbox.Items
    for message in messages:
        if label in message.Subject:
            return True
    return False
