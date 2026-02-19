DOMAIN = "netcup_dyndns"

CONF_CUSTOMER_NUMBER = "customer_number"
CONF_API_KEY = "api_key"
CONF_API_PASSWORD = "api_password"
CONF_DOMAINNAME = "domainname"
CONF_HOSTNAME = "hostname"
CONF_UPDATE_IPV4 = "update_ipv4"
CONF_UPDATE_IPV6 = "update_ipv6"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_HOSTNAME = "@"
DEFAULT_UPDATE_IPV4 = True
DEFAULT_UPDATE_IPV6 = False
DEFAULT_SCAN_INTERVAL = 300  # seconds

SERVICE_UPDATE = "update"

PLATFORMS: list[str] = ["sensor", "button"]
