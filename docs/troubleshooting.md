# Troubleshooting

## Redfish authentication fails

Symptoms:

- HTTP 401 or 403 from `/redfish/v1/`.
- `redfish_info` reports insufficient privilege.

Actions:

```bash
curl -k -u 'USER:PASSWORD' https://BMC/redfish/v1/
```

Verify that the account has login, remote console/virtual media, server control, and configuration/read privileges appropriate to the task. HPE and Dell privilege names differ.

## TLS validation fails

For production, import the issuing CA and configure:

```yaml
bmc_validate_certs: true
bmc_ca_path: /etc/pki/ca-trust/source/anchors/bmc-ca.pem
```

For an isolated lab only, `bmc_validate_certs: false` allows self-signed certificates.

## No NIC or incorrect provisioning MAC

Inspect:

```bash
jq '.normalized_nics, .nic_inventory' \
  artifacts/CLUSTER/raw/bmc-HOST.json
```

Then set one of:

```yaml
provisioning_nic_match: "LOM 1|Integrated NIC 1 Port 1"
```

or:

```yaml
provisioning_mac_override: "aa:bb:cc:dd:ee:ff"
```

The chosen MAC must be the MAC seen in the Assisted Installer host inventory.

## Virtual media insertion fails

Check:

1. The BMC can resolve and reach the ISO host.
2. The protocol is supported by the BMC firmware.
3. The virtual-media feature is licensed where the vendor requires licensing.
4. Another image is not locked or mounted by a different session.
5. `bmc_virtual_media_category` is correct. The default tries `Manager`, then `Systems`.
6. The ISO URL does not redirect to an interactive login page.

Test URL reachability from the BMC management network, not only from the Ansible control node.

## iLO-specific observations

- Update iLO firmware before troubleshooting schema behavior.
- Confirm the Redfish API is enabled and the account has Virtual Media and Virtual Power/Reset privileges.
- HPE iLO 5 and newer are the primary validation target. Older iLO generations can expose vendor-specific differences and should be tested explicitly.

## iDRAC-specific observations

- Confirm Redfish is enabled.
- The dynamically selected IDs often resemble `System.Embedded.1` and `iDRAC.Embedded.1`, but the playbook does not assume them.
- Review Lifecycle Controller jobs when power or virtual-media operations remain pending.

## ISO HTTP container fails

Check Podman and port ownership:

```bash
podman ps -a --filter name=ocp-assisted-iso-httpd
podman logs ocp-assisted-iso-httpd
ss -lntp | grep ':8080'
curl -I http://CONTROL_NODE_IP:8080/discovery.iso
```

Change `iso_http_port` when another process uses the port.

## Hosts do not register

Review:

```bash
jq . artifacts/CLUSTER/raw/hosts-initial.json
jq . artifacts/CLUSTER/raw/events.json
```

Confirm DNS, gateway, VLAN, bond mode, LACP configuration, MTU, and the `mac_interface_map` generated in the InfraEnv request.

## Installation is not ready

The playbook waits for the Assisted Installer cluster status to become `ready`. Use the Assisted Installer UI or events API to inspect blocking validations. Do not bypass failed hardware, DNS, network, NTP, or operator validations without understanding the installation impact.
