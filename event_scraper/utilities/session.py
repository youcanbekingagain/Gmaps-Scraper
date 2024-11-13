import os
import json


class Session:
    def __init__(self):
        self.session_data = {}

    def set_match_session(self, url, key, value):
        """Sets a match session with a key-value pair for a given URL."""
        if url not in self.session_data:
            self.session_data[url] = {}
        self.session_data[url][key] = value
        self.save_session_data(url)

    def get_match_session(self, url, key):
        """Retrieves the session data for a given URL."""
        return self.session_data.get(url, {}).get(key, None)

    def load_session_data(self, url):
        """Loads session data for a given URL from the corresponding JSON file."""
        filename = f"{self._sanitize_filename(url)}.json"
        filepath = os.path.join("session", filename)

        try:
            with open(filepath, "r") as f:
                self.session_data[url] = json.load(f)
        except FileNotFoundError:
            self.session_data[url] = {}

    def save_session_data(self, url):
        """Saves session data for a given URL to a JSON file."""
        filename = f"{self._sanitize_filename(url)}.json"
        filepath = os.path.join("session", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(self.session_data.get(url, {}), f)

    @staticmethod
    def _sanitize_filename(url):
        """Sanitizes the URL to create a valid filename."""
        return "".join([c if c.isalnum() else "_" for c in url])
