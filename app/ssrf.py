import socket
import ipaddress
from typing import Iterable


def _iter_addresses_for_host(hostname: str) -> Iterable[str]:
    # Returns the IP addresses (strings) for the hostname
    # Uses getaddrinfo to obtain both IPv4 and IPv6 addresses
    for res in socket.getaddrinfo(hostname, None):
        sockaddr = res[4]
        # sockaddr can be (addr, port) for IPv4 or (addr, port, flowinfo, scopeid) for IPv6
        if isinstance(sockaddr, tuple) and len(sockaddr) >= 1:
            yield sockaddr[0]


def _is_ip_private_or_reserved(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        # Not a parsable IP address - be conservative and treat as private
        return True

    # Reject loopback, private, link-local, multicast, unspecified, reserved
    if a.is_loopback or a.is_private or a.is_link_local or a.is_multicast or a.is_unspecified:
        return True

    # IPv4: reject broadcast/unspecified/reserved
    # ipaddress covers reserved via is_reserved attribute on newer Python versions
    if getattr(a, "is_reserved", False):
        return True

    return False


def is_hostname_public(hostname: str) -> bool:
    """
    Resolve `hostname` and return True only if ALL resolved addresses are public routable IPs.
    If resolution fails or any address is private/reserved/loopback/link-local/multicast, returns False.
    """
    # Quick reject common internal names
    if hostname.lower() in {"localhost", "ip6-localhost"}:
        return False

    try:
        addrs = list(_iter_addresses_for_host(hostname))
    except socket.gaierror:
        return False

    if not addrs:
        return False

    for addr in addrs:
        if _is_ip_private_or_reserved(addr):
            return False

    return True
