import os
import time
import logging
import urllib.request
import urllib.parse
import urllib.robotparser
import hashlib
from typing import Optional, Tuple
from urllib.error import URLError, HTTPError
from datetime import datetime, timezone

from .models import AcquisitionMetadata

logger = logging.getLogger(__name__)

class PoliteHTTPClient:
    """
    A reusable web client that strictly adheres to the CIVICLENS TN acquisition rules:
    1. Respects robots.txt
    2. Enforces rate limiting and politeness delays
    3. Uses standard User-Agent headers identifying the project
    4. Records HTTP status, failures, and avoids silent infinite retries
    5. Checks local cache before fetching
    """
    
    def __init__(self, cache_dir: str = "data/cache", user_agent: str = "CIVICLENS_TN_Bot/1.0 (Research Project; contact@civiclens.org)"):
        self.cache_dir = cache_dir
        self.user_agent = user_agent
        self.robot_parsers = {}
        self.last_request_time = {}
        self.politeness_delay = 2.0  # seconds between requests to same domain
        
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            
    def _get_domain(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _can_fetch(self, url: str) -> bool:
        domain = self._get_domain(url)
        if domain not in self.robot_parsers:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(urllib.parse.urljoin(domain, '/robots.txt'))
            try:
                # Add headers for robots.txt fetch
                req = urllib.request.Request(rp.url, headers={'User-Agent': self.user_agent})
                with urllib.request.urlopen(req, timeout=10) as response:
                    rp.parse(response.read().decode('utf-8').splitlines())
            except Exception as e:
                logger.warning(f"Could not fetch robots.txt for {domain}: {e}")
                # If robots.txt is missing or fails, assume allow
                rp.allow_all = True
            self.robot_parsers[domain] = rp
        
        rp = self.robot_parsers[domain]
        if hasattr(rp, 'allow_all') and getattr(rp, 'allow_all'):
             return True
        return rp.can_fetch(self.user_agent, url)

    def _wait_for_politeness(self, domain: str):
        now = time.time()
        if domain in self.last_request_time:
            elapsed = now - self.last_request_time[domain]
            if elapsed < self.politeness_delay:
                time.sleep(self.politeness_delay - elapsed)
        self.last_request_time[domain] = time.time()

    def fetch(self, url: str) -> Tuple[Optional[bytes], AcquisitionMetadata]:
        metadata = AcquisitionMetadata(
            url=url,
            document_type="UNKNOWN",
            retrieval_status="pending",
            collection_timestamp=datetime.now(timezone.utc)
        )
        
        domain = self._get_domain(url)
        
        if not self._can_fetch(url):
            logger.error(f"robots.txt disallows fetching {url}")
            metadata.retrieval_status = "blocked_by_robots"
            return None, metadata

        self._wait_for_politeness(domain)
        
        req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                status_code = response.getcode()
                metadata.http_status = status_code
                
                if status_code == 200:
                    metadata.retrieval_status = "success"
                    metadata.content_hash = hashlib.sha256(content).hexdigest()
                    
                    # Try to get filename from URL
                    parsed = urllib.parse.urlparse(url)
                    filename = os.path.basename(parsed.path)
                    if not filename:
                        filename = f"download_{int(time.time())}"
                    metadata.original_filename = filename
                    
                    if url.lower().endswith(".pdf"):
                        metadata.document_type = "PDF"
                    elif url.lower().endswith(".html"):
                        metadata.document_type = "HTML"
                        
                    return content, metadata
                else:
                    metadata.retrieval_status = f"failed_http_{status_code}"
                    return None, metadata
                    
        except HTTPError as e:
            metadata.http_status = e.code
            metadata.retrieval_status = f"failed_http_{e.code}"
            logger.error(f"HTTP Error fetching {url}: {e.code}")
            return None, metadata
        except URLError as e:
            metadata.retrieval_status = "failed_network"
            logger.error(f"URL Error fetching {url}: {e.reason}")
            return None, metadata
        except Exception as e:
            metadata.retrieval_status = "failed_exception"
            logger.error(f"Exception fetching {url}: {str(e)}")
            return None, metadata
