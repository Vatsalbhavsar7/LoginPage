import os
import pyotp
import importlib.util
from SmartApi.smartConnect import SmartConnect
from tkinter import Tk, messagebox, filedialog
from tkinter import ttk

class SmartAPIClient:
    def __init__(self, api_key, client_id, pin, totp_secret):
        self.api_key = api_key
        self.client_id = client_id
        self.pin = pin
        self.totp_secret = totp_secret
        self.smart_api = SmartConnect(api_key=api_key)

        self.auth_token = None
        self.refresh_token = None
        self.feed_token = None
        self.exchanges = None
        self.client_code = None
        self.user_name = None

    def _log(self, message, level="info"):
        print(f"[{level.upper()}]: {message}")

    def safe_api_call(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self._log(str(e), "exception")
            return None

    def login(self):
        try:
            otp = pyotp.TOTP(self.totp_secret).now()
            session = self.safe_api_call(self.smart_api.generateSession, self.client_id, self.pin, otp)

            if not session or not session.get("status"):
                self._log(f"Login failed: {session}", "error")
                return False

            self.auth_token = session["data"]["jwtToken"]
            self.refresh_token = session["data"]["refreshToken"]
            self.feed_token = self.smart_api.getfeedToken()
            self.exchanges = session["data"]["exchanges"]
            self.client_code = session["data"]["clientcode"]
            self.user_name = session["data"]["name"]

            self._log(f"Login successful for user: {self.user_name}")
            return (
                self.auth_token,
                self.refresh_token,
                self.feed_token,
                self.exchanges,
                self.smart_api,
                self.client_code,
                self.user_name,
            )
        except Exception as e:
            self._log("Login error", "exception")
            return False

    def logout(self):
        result = self.safe_api_call(self.smart_api.terminateSession, self.client_code)
        self._log(f"Logout result: {result}")
        return result

class Application(Tk):
    def __init__(self):
        super().__init__()
        self.title("SmartAPI Login GUI")
        self.geometry("400x300")
        self.resizable(True, True)

        style = ttk.Style(self)
        style.theme_use("clam")

        self.shared_state = {}
        self.create_login_page()

    def create_login_page(self):
        self.clear_widgets()

        ttk.Label(self, text="SmartAPI Login", font=("Helvetica", 16)).grid(row=0, column=0, columnspan=2, pady=(10, 20))

        ttk.Label(self, text="API Key:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.api_key_entry = ttk.Entry(self, width=30, show="*")
        self.api_key_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(self, text="Username:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.username_entry = ttk.Entry(self, width=30)
        self.username_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(self, text="PIN:").grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.pin_entry = ttk.Entry(self, width=30, show="*")
        self.pin_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(self, text="TOTP Secret:").grid(row=4, column=0, sticky='e', padx=5, pady=5)
        self.totp_entry = ttk.Entry(self, width=30, show="*")
        self.totp_entry.grid(row=4, column=1, padx=5, pady=5)

        ttk.Button(self, text="Login", command=self.login).grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(self, text="Create Sample File", command=self.create_sample_file).grid(row=6, column=0, columnspan=2, pady=2)
        ttk.Button(self, text="Import Credentials", command=self.import_credentials).grid(row=7, column=0, columnspan=2, pady=2)

    def create_home_page(self, user_name):
        self.clear_widgets()
        ttk.Label(self, text=f"Welcome {user_name}", font=("Helvetica", 16)).pack(pady=20)
        ttk.Button(self, text="Logout", command=self.logout).pack(pady=10)

    def clear_widgets(self):
        for widget in self.winfo_children():
            widget.destroy()

    def create_sample_file(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python File", "*.py")],
            initialfile="sample_login.py"
        )
        if not file_path:
            return
        sample_data = (
            'api_key = "your_api_key"\n'
            'username = "your_username"\n'
            'pin = "your_pin"\n'
            'totp = "your_totp_secret"\n'
        )
        try:
            with open(file_path, "w") as f:
                f.write(sample_data)
            messagebox.showinfo("File Saved", f"Sample file saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def import_credentials(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if not file_path:
            return
        try:
            creds = {}
            with open(file_path, "r") as f:
                exec(f.read(), creds)
            self.api_key_entry.insert(0, creds.get("api_key", ""))
            self.username_entry.insert(0, creds.get("username", ""))
            self.pin_entry.insert(0, creds.get("pin", ""))
            self.totp_entry.insert(0, creds.get("totp", ""))
            messagebox.showinfo("Success", "Credentials imported.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import credentials: {e}")

    def login(self):
        api_key = self.api_key_entry.get()
        username = self.username_entry.get()
        pin = self.pin_entry.get()
        totp = self.totp_entry.get()

        if not all([api_key, username, pin, totp]):
            messagebox.showerror("Missing Fields", "Please fill all fields")
            return

        self.client = SmartAPIClient(api_key, username, pin, totp)
        result = self.client.login()

        if result:
            self.shared_state["client"] = self.client
            self.create_home_page(self.client.user_name)
        else:
            messagebox.showerror("Login Failed", "Check your credentials or internet connection.")

    def logout(self):
        if "client" in self.shared_state:
            result = self.shared_state["client"].logout()
            messagebox.showinfo("Logout", f"{result}")
        self.create_login_page()

if __name__ == "__main__":
    app = Application()
    app.mainloop()
