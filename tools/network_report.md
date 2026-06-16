# Network Report Script - RHEL 9

Simple and clean script to generate a network report on freshly installed RHEL 9 systems.

## Features

- Lists all network interfaces (except loopback)
- Shows status (UP/DOWN)
- MAC Address
- IP Address
- Configuration type (DHCP or Static)
- Default Gateway
- Configured DNS servers
- NTP (Chrony) status and sources

## Requirements

- RHEL 9 (or compatible)
- Run as root or with `sudo`
- `ip` command and `chronyc` (usually pre-installed)

## How to Use

1. **Download / Create the script**

```bash
cat > network_report.sh << 'EOF'
# Paste the entire script content here
EOF
