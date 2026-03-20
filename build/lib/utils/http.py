import random
import time
import logging
import urllib3
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, config: dict):
        self._delay = config["rate_limit"]["delay_seconds"]
        self._timeout = config["http"]["timeout_seconds"]
        self._user_agents = config["http"]["user_agents"]
        self._verify_ssl = config["http"].get("verify_ssl", True)
        self._session = self._build_session(config["http"]["max_retries"])

    def _build_session(self, max_retries: int) -> Session:
        session = Session()
        retry = Retry(total=max_retries, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    @property
    def delay(self) -> float:
        return self._delay

    def get(self, url: str) -> str:
        self._session.headers.update({"User-Agent": random.choice(self._user_agents)})
        response = self._session.get(url, timeout=self._timeout, verify=self._verify_ssl)
        response.raise_for_status()
        return response.text
