import tkinter as tk
from tkinter import messagebox

class UrlMonitorApp:
    def __init__(self, master):
        self.master = master
        master.title("URL Monitor Configuration")

        # URL Entry
        self.label_url = tk.Label(master, text="URL to Monitor:")
        self.label_url.pack()

        self.entry_url = tk.Entry(master, width=50)
        self.entry_url.pack()

        # Twilio Configuration
        self.label_twilio = tk.Label(master, text="Twilio Configuration:")
        self.label_twilio.pack()

        self.label_account_sid = tk.Label(master, text="Account SID:")
        self.label_account_sid.pack()

        self.entry_account_sid = tk.Entry(master, width=50)
        self.entry_account_sid.pack()

        self.label_auth_token = tk.Label(master, text="Auth Token:")
        self.label_auth_token.pack()

        self.entry_auth_token = tk.Entry(master, width=50, show="*")
        self.entry_auth_token.pack()

        self.label_twilio_number = tk.Label(master, text="Twilio Phone Number:")
        self.label_twilio_number.pack()

        self.entry_twilio_number = tk.Entry(master, width=50)
        self.entry_twilio_number.pack()

        self.label_receiver_number = tk.Label(master, text="Receiver Phone Number (Limit 6):")
        self.label_receiver_number.pack()

        self.entry_receiver_number = tk.Entry(master, width=50)
        self.entry_receiver_number.pack()

        # Submit Button
        self.submit_button = tk.Button(master, text="Save Configuration", command=self.save_configuration)
        self.submit_button.pack()

    def save_configuration(self):
        url = self.entry_url.get()
        account_sid = self.entry_account_sid.get()
        auth_token = self.entry_auth_token.get()
        twilio_number = self.entry_twilio_number.get()
        receiver_number = self.entry_receiver_number.get()

        # Validate inputs
        if not url or not account_sid or not auth_token or not twilio_number or not receiver_number:
            messagebox.showerror("Error", "All fields are required!")
            return

        # Save configuration (you can implement this logic)
        # For simplicity, just print the values here
        print(f"URL: {url}")
        print(f"Account SID: {account_sid}")
        print(f"Auth Token: {auth_token}")
        print(f"Twilio Number: {twilio_number}")
        print(f"Receiver Number: {receiver_number}")

        messagebox.showinfo("Success", "Configuration saved successfully!")

def main():
    root = tk.Tk()
    app = UrlMonitorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
