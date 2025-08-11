import random
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class BrowserType(Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"
    OPERA = "opera"

class DeviceType(Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"

@dataclass
class UserAgentInfo:
    """Informações de um User Agent."""
    user_agent: str
    browser: BrowserType
    device: DeviceType
    os: str
    version: str
    popularity_score: float = 1.0
    last_used: Optional[float] = None
    success_count: int = 0
    failure_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calcula a taxa de sucesso do user agent."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

class UserAgentRotator:
    """Sistema de rotação de User Agents com base em popularidade e sucesso."""
    
    def __init__(self):
        self.user_agents: List[UserAgentInfo] = []
        self.current_index = 0
        self.min_interval_between_uses = 60  # 1 minuto entre usos do mesmo UA
        self._load_default_user_agents()
    
    def _load_default_user_agents(self):
        """Carrega user agents padrão mais populares e atuais."""
        
        # Chrome Desktop (mais populares)
        chrome_desktop = [
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "browser": BrowserType.CHROME,
                "device": DeviceType.DESKTOP,
                "os": "Windows 10",
                "version": "120.0",
                "popularity_score": 0.9
            },
            {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "browser": BrowserType.CHROME,
                "device": DeviceType.DESKTOP,
                "os": "macOS",
                "version": "120.0",
                "popularity_score": 0.85
            },
            {
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "browser": BrowserType.CHROME,
                "device": DeviceType.DESKTOP,
                "os": "Linux",
                "version": "120.0",
                "popularity_score": 0.7
            }
        ]
        
        # Firefox Desktop
        firefox_desktop = [
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "browser": BrowserType.FIREFOX,
                "device": DeviceType.DESKTOP,
                "os": "Windows 10",
                "version": "121.0",
                "popularity_score": 0.8
            },
            {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
                "browser": BrowserType.FIREFOX,
                "device": DeviceType.DESKTOP,
                "os": "macOS",
                "version": "121.0",
                "popularity_score": 0.75
            }
        ]
        
        # Safari Desktop
        safari_desktop = [
            {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
                "browser": BrowserType.SAFARI,
                "device": DeviceType.DESKTOP,
                "os": "macOS",
                "version": "17.1",
                "popularity_score": 0.65
            }
        ]
        
        # Edge Desktop
        edge_desktop = [
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                "browser": BrowserType.EDGE,
                "device": DeviceType.DESKTOP,
                "os": "Windows 10",
                "version": "120.0",
                "popularity_score": 0.6
            }
        ]
        
        # Chrome Mobile
        chrome_mobile = [
            {
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
                "browser": BrowserType.CHROME,
                "device": DeviceType.MOBILE,
                "os": "iOS",
                "version": "120.0",
                "popularity_score": 0.8
            },
            {
                "user_agent": "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
                "browser": BrowserType.CHROME,
                "device": DeviceType.MOBILE,
                "os": "Android",
                "version": "120.0",
                "popularity_score": 0.85
            }
        ]
        
        # Safari Mobile
        safari_mobile = [
            {
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
                "browser": BrowserType.SAFARI,
                "device": DeviceType.MOBILE,
                "os": "iOS",
                "version": "17.1",
                "popularity_score": 0.75
            }
        ]
        
        # Combinar todas as listas
        all_user_agents = (
            chrome_desktop + firefox_desktop + safari_desktop + 
            edge_desktop + chrome_mobile + safari_mobile
        )
        
        # Converter para objetos UserAgentInfo
        for ua_data in all_user_agents:
            ua_info = UserAgentInfo(**ua_data)
            self.user_agents.append(ua_info)
        
        logger.info(f"Carregados {len(self.user_agents)} user agents")
    
    def get_random_user_agent(self, device_type: DeviceType = None, 
                             browser: BrowserType = None) -> str:
        """Obtém um user agent aleatório baseado nos filtros."""
        filtered_agents = self.user_agents
        
        # Filtrar por tipo de dispositivo
        if device_type:
            filtered_agents = [ua for ua in filtered_agents if ua.device == device_type]
        
        # Filtrar por browser
        if browser:
            filtered_agents = [ua for ua in filtered_agents if ua.browser == browser]
        
        if not filtered_agents:
            logger.warning("Nenhum user agent encontrado com os filtros especificados")
            filtered_agents = self.user_agents
        
        # Filtrar user agents que não foram usados recentemente
        current_time = time.time()
        available_agents = [
            ua for ua in filtered_agents
            if not ua.last_used or 
            (current_time - ua.last_used) > self.min_interval_between_uses
        ]
        
        if not available_agents:
            available_agents = filtered_agents
        
        # Selecionar baseado em popularidade e taxa de sucesso
        weights = [
            ua.popularity_score * ua.success_rate 
            for ua in available_agents
        ]
        
        selected_ua = random.choices(available_agents, weights=weights)[0]
        selected_ua.last_used = current_time
        
        logger.debug(f"User agent selecionado: {selected_ua.browser.value} {selected_ua.device.value}")
        return selected_ua.user_agent
    
    def get_user_agent_with_headers(self, device_type: DeviceType = None, 
                                   browser: BrowserType = None) -> Dict[str, str]:
        """Obtém user agent com headers complementares realistas."""
        user_agent = self.get_random_user_agent(device_type, browser)
        
        # Headers base comuns
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9,pt;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Headers específicos por browser
        if "Chrome" in user_agent:
            headers.update({
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0" if device_type != DeviceType.MOBILE else "?1",
                "sec-ch-ua-platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            })
        elif "Firefox" in user_agent:
            headers.update({
                "Cache-Control": "max-age=0",
                "Pragma": "no-cache"
            })
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            headers.update({
                "Cache-Control": "max-age=0"
            })
        
        return headers
    
    def mark_success(self, user_agent: str):
        """Marca um user agent como bem-sucedido."""
        for ua in self.user_agents:
            if ua.user_agent == user_agent:
                ua.success_count += 1
                break
    
    def mark_failure(self, user_agent: str):
        """Marca um user agent como falhado."""
        for ua in self.user_agents:
            if ua.user_agent == user_agent:
                ua.failure_count += 1
                break
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas dos user agents."""
        total = len(self.user_agents)
        
        by_browser = {}
        by_device = {}
        
        for ua in self.user_agents:
            # Estatísticas por browser
            browser_name = ua.browser.value
            if browser_name not in by_browser:
                by_browser[browser_name] = {"count": 0, "avg_success_rate": 0.0}
            by_browser[browser_name]["count"] += 1
            by_browser[browser_name]["avg_success_rate"] += ua.success_rate
            
            # Estatísticas por dispositivo
            device_name = ua.device.value
            if device_name not in by_device:
                by_device[device_name] = {"count": 0, "avg_success_rate": 0.0}
            by_device[device_name]["count"] += 1
            by_device[device_name]["avg_success_rate"] += ua.success_rate
        
        # Calcular médias
        for browser_stats in by_browser.values():
            if browser_stats["count"] > 0:
                browser_stats["avg_success_rate"] /= browser_stats["count"]
        
        for device_stats in by_device.values():
            if device_stats["count"] > 0:
                device_stats["avg_success_rate"] /= device_stats["count"]
        
        return {
            "total": total,
            "by_browser": by_browser,
            "by_device": by_device
        }
    
    def add_custom_user_agent(self, user_agent: str, browser: BrowserType, 
                             device: DeviceType, os: str, version: str, 
                             popularity_score: float = 1.0):
        """Adiciona um user agent customizado."""
        ua_info = UserAgentInfo(
            user_agent=user_agent,
            browser=browser,
            device=device,
            os=os,
            version=version,
            popularity_score=popularity_score
        )
        self.user_agents.append(ua_info)
        logger.info(f"User agent customizado adicionado: {browser.value} {device.value}")