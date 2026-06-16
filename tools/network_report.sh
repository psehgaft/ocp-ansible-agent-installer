#!/bin/bash
# =============================================================================
# Network Report Script for RHEL 9
# Generates a clean report of all network interfaces, IP, MAC, status,
# gateway, DNS and NTP information.
# =============================================================================

# Output file
REPORT_FILE="/tmp/network_report_$(hostname)_$(date +%Y%m%d_%H%M).txt"

echo "=============================================" > "$REPORT_FILE"
echo "NETWORK REPORT - $(hostname)" >> "$REPORT_FILE"
echo "Generated on: $(date)" >> "$REPORT_FILE"
echo "=============================================" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# --------------------- Network Interfaces ---------------------
echo "NETWORK INTERFACES" >> "$REPORT_FILE"
echo "==================" >> "$REPORT_FILE"
printf "%-15s %-8s %-20s %-18s %-15s\n" "INTERFACE" "STATUS" "MAC ADDRESS" "IP ADDRESS" "CONFIG TYPE" >> "$REPORT_FILE"
echo "--------------------------------------------------------------------------------" >> "$REPORT_FILE"

# Loop through all physical interfaces (excluding loopback)
for iface in $(ip -o link show | awk -F': ' '{print $2}' | grep -v lo); do
    # Interface status (UP/DOWN)
    state=$(ip -o link show "$iface" | awk '{print $9}')
    if [ "$state" = "UP" ]; then
        status="UP"
    else
        status="DOWN"
    fi

    # MAC Address
    mac=$(ip link show "$iface" | grep link/ether | awk '{print $2}' | head -n1)
    [ -z "$mac" ] && mac="N/A"

    # IP Address (IPv4)
    ip_addr=$(ip -4 addr show "$iface" | grep inet | awk '{print $2}' | head -n1)
    [ -z "$ip_addr" ] && ip_addr="N/A"

    # Configuration type (DHCP or Static)
    if ip addr show "$iface" | grep -q "dynamic"; then
        config_type="DHCP (bound)"
    else
        config_type="Static / Other"
    fi

    printf "%-15s %-8s %-20s %-18s %-15s\n" "$iface" "$status" "$mac" "$ip_addr" "$config_type" >> "$REPORT_FILE"
done

echo "" >> "$REPORT_FILE"

# --------------------- Default Gateway ---------------------
echo "DEFAULT GATEWAY" >> "$REPORT_FILE"
echo "================" >> "$REPORT_FILE"
ip route | grep default >> "$REPORT_FILE" 2>/dev/null || echo "No default gateway found" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# --------------------- DNS Servers ---------------------
echo "DNS SERVERS" >> "$REPORT_FILE"
echo "===========" >> "$REPORT_FILE"
if [ -f /etc/resolv.conf ]; then
    grep -E '^nameserver' /etc/resolv.conf >> "$REPORT_FILE" || echo "No DNS servers configured" >> "$REPORT_FILE"
else
    echo "/etc/resolv.conf not found" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# --------------------- NTP (Chrony) ---------------------
echo "NTP STATUS (Chrony)" >> "$REPORT_FILE"
echo "====================" >> "$REPORT_FILE"
if command -v chronyc >/dev/null 2>&1; then
    echo "chronyd service status: $(systemctl is-active chronyd.service 2>/dev/null || echo 'inactive/not found')" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "NTP Sources:" >> "$REPORT_FILE"
    chronyc sources -v | head -n 15 >> "$REPORT_FILE" 2>/dev/null || echo "Could not retrieve NTP sources" >> "$REPORT_FILE"
else
    echo "Chrony is not installed" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "=============================================" >> "$REPORT_FILE"
echo "Report saved to: $REPORT_FILE" >> "$REPORT_FILE"

# Display the report
cat "$REPORT_FILE"
echo ""
echo "Network report generated successfully: $REPORT_FILE"
