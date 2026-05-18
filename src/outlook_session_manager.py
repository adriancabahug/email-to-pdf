"""OutlookSessionManager - COM lifecycle, retry, backoff, and crash recovery."""

import random
import time
import subprocess
import win32com.client
import pythoncom
from typing import Any, Callable, List, Optional, Dict

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False  # type: ignore


DEFAULT_RETRY_CONFIG: Dict[str, int] = {
    "max_com_retries": 3,
    "max_outlook_restarts": 2,
}
DEFAULT_BACKOFF_CONFIG: Dict[str, float] = {
    "initial_sec": 2.0,
    "max_sec": 30.0,
    "jitter_sec": 1.0,
    "multiplier": 2.0,
}


class OutlookSessionManager:
    def __init__(
        self,
        retry_config: Optional[Dict[str, int]] = None,
        backoff_config: Optional[Dict[str, float]] = None,
    ):
        self._retry = retry_config or dict(DEFAULT_RETRY_CONFIG)
        self._backoff = backoff_config or dict(DEFAULT_BACKOFF_CONFIG)
        self._outlook_app: Optional[Any] = None
        self._namespace: Optional[Any] = None
        self._connected = False
        self._restart_count = 0

    def connect(self) -> bool:
        try:
            pythoncom.CoInitialize()
            self._outlook_app = win32com.client.Dispatch("Outlook.Application")
            self._namespace = self._outlook_app.GetNamespace("MAPI")
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._outlook_app = None
        self._namespace = None
        self._connected = False
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    def is_healthy(self) -> bool:
        if not self._connected or not self._namespace:
            return False
        try:
            _ = self._namespace.Folders.Count
            return True
        except Exception:
            return False

    def is_connected(self) -> bool:
        return self._connected

    def get_namespace(self) -> Optional[Any]:
        return self._namespace

    def get_inbox_folder(self, account_email: Optional[str] = None):
        return self._get_default_folder(6, account_email)

    def get_sent_items_folder(self, account_email: Optional[str] = None):
        return self._get_default_folder(5, account_email)

    def _get_default_folder(self, folder_const: int, account_email: Optional[str]):
        ns = self.get_namespace()
        if ns is None:
            raise RuntimeError("Not connected to Outlook")
        if account_email:
            for store in ns.Folders:
                if store.Name.lower() == account_email.lower():
                    return store.Folders.Item(folder_const)
        return ns.GetDefaultFolder(folder_const)

    def get_all_accounts(self) -> List[Any]:
        def _call():
            if not self._connected:
                raise RuntimeError("Not connected to Outlook")
            accounts = []
            for folder in self._namespace.Folders:
                accounts.append(folder)
            return accounts
        return self.wrap(_call)

    def get_all_folders_recursive(self, root_folder: Any) -> List[Any]:
        def _call():
            folders = []
            for folder in root_folder.Folders:
                folders.append(folder)
                folders.extend(self.get_all_folders_recursive(folder))
            return folders
        return self.wrap(_call)

    def discover_email_from_name(self, first_name: str, last_name: str) -> Optional[str]:
        def _call():
            search_name = f"{first_name} {last_name}".lower()
            accounts = self.get_all_accounts()
            for account in accounts:
                folders = [account]
                folders.extend(self.get_all_folders_recursive(account))
                for folder in folders:
                    try:
                        if not hasattr(folder, "Items"):
                            continue
                        messages = folder.Items
                        for message in messages:
                            try:
                                sender_name = str(message.SenderName).lower()
                                if search_name in sender_name:
                                    return message.SenderEmailAddress
                            except Exception:
                                continue
                    except Exception:
                        continue
            return None
        return self.wrap(_call)

    def wrap(self, com_call: Callable[..., Any]) -> Any:
        max_retries = self._retry.get("max_com_retries", 3)
        initial_delay = self._backoff.get("initial_sec", 2)
        max_delay = self._backoff.get("max_sec", 30)
        jitter = self._backoff.get("jitter_sec", 1)
        multiplier = self._backoff.get("multiplier", 2)
        max_restarts = self._retry.get("max_outlook_restarts", 2)

        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                return com_call()
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = min(initial_delay * (multiplier ** (attempt - 1)), max_delay)
                    actual_delay = delay + random.uniform(-jitter, jitter)
                    time.sleep(actual_delay)

        if last_error:
            self._escalate(max_restarts)
            return com_call()

    def _escalate(self, max_restarts: int) -> None:
        if self._restart_count >= max_restarts:
            self._raise_category_d()

        if _HAS_PSUTIL:
            outlook_procs = self._get_outlook_processes()
            if not outlook_procs:
                self._launch_outlook()
            elif self._is_unresponsive():
                self._terminate_and_launch()
            else:
                self._terminate_and_launch()
        else:
            self._terminate_and_launch()

        self._restart_count += 1

    def _get_outlook_processes(self) -> List[Any]:
        if not _HAS_PSUTIL:
            return []
        processes = []
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and "OUTLOOK" in proc.info["name"].upper():
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes

    def _is_unresponsive(self) -> bool:
        if not _HAS_PSUTIL:
            return False
        procs = self._get_outlook_processes()
        for proc in procs:
            try:
                if not proc.is_running():
                    return True
                if proc.status() == psutil.STATUS_NOT_RESPONDING:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    def _terminate_and_launch(self) -> None:
        if _HAS_PSUTIL:
            for proc in self._get_outlook_processes():
                try:
                    proc.terminate()
                    proc.wait(timeout=15)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied):
                    pass
        else:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "OUTLOOK.EXE"],
                    capture_output=True,
                    timeout=15
                )
            except Exception:
                pass
        self._launch_outlook()

    def _launch_outlook(self) -> None:
        self._connected = False
        try:
            self._outlook_app = win32com.client.Dispatch("Outlook.Application")
            time.sleep(3)
            self._namespace = self._outlook_app.GetNamespace("MAPI")
            self._connected = True
        except Exception:
            self._outlook_app = None
            self._namespace = None

    def _raise_category_d(self) -> None:
        raise RuntimeError(
            "Outlook requires user intervention (profile prompt, login, or modal dialog). "
            "Please sign in to Outlook manually and restart the application."
        )