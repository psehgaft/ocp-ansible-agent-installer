# RHOSO Demo Lab Playground

This repository houses automation scripts, playbooks, and documentation for upgrading Red Hat OpenStack Platform (RHOSP) 17.1 to Red Hat OpenStack Services on OpenShift (RHOSO) 18.

## Overview

This repository provides automation and documentation for the following RHOSO lab scenarios:

1. **RHOSO Installation (Connected Environment)** - Install Red Hat OpenStack Services on OpenShift in a connected environment
2. **RHOSP 17.1 to RHOSO 18 Upgrade** - Upgrade/adopt RHOSP 17.1 to RHOSO 18 using the adoption mechanism
3. **RHOSO Updates Lab** - Manage and apply updates to RHOSO deployments
4. **GitOps with ArgoCD** - Install and discover RHOSO using GitOps with ArgoCD

## Repository Structure

```
.
├── docs/                          # Documentation
│   ├── installation/              # RHOSO installation guides
│   ├── upgrade/                   # Upgrade/adoption guides
│   ├── updates/                   # Update procedures
│   └── gitops/                    # GitOps and ArgoCD guides
├── automation/                    # Automation scripts and playbooks
│   ├── installation/              # Installation automation
│   ├── upgrade/                   # Upgrade automation
│   ├── updates/                   # Update automation
│   └── gitops/                    # GitOps automation
└── examples/                      # Example configurations
    ├── manifests/                 # Kubernetes/OpenShift manifests
    └── configs/                   # Configuration files
```

## Getting Started

### Prerequisites

- OpenShift 4.18_x+ cluster
- RHOSP 17.1 environment (for upgrade scenarios)
- Access to Red Hat registries
- Ansible 2.9+ (for automation playbooks)
- oc CLI tools
- Git

### Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/gutseb/rhoso-demo-lab-playground.git
   cd rhoso-demo-lab-playground
   ```

2. Review the documentation in the `docs/` directory for your specific scenario

3. Follow the step-by-step guides or use the automation scripts in the `automation/` directory

## Lab Scenarios

### 1. RHOSO Installation (Connected Environment)

Install RHOSO 18 on OpenShift in a connected environment.

- **Documentation**: [docs/installation/README.md](docs/installation/README.md)
- **Automation**: [automation/installation/](automation/installation/)

### 2. RHOSP 17.1 to RHOSO 18 Upgrade

Upgrade/adopt an existing RHOSP 17.1 deployment to RHOSO 18.

- **Documentation**: [docs/upgrade/README.md](docs/upgrade/README.md)
- **Automation**: [automation/upgrade/](automation/upgrade/)

### 3. RHOSO Updates Lab

Learn how to manage and apply updates to RHOSO deployments.

- **Documentation**: [docs/updates/README.md](docs/updates/README.md)
- **Automation**: [automation/updates/](automation/updates/)

### 4. GitOps with ArgoCD

Install and manage RHOSO using GitOps principles with ArgoCD.

- **Documentation**: [docs/gitops/README.md](docs/gitops/README.md)
- **Automation**: [automation/gitops/](automation/gitops/)

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for improvements.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Resources

- [Red Hat OpenStack Services on OpenShift Documentation](https://access.redhat.com/documentation/en-us/red_hat_openstack_services_on_openshift/)
- [OpenShift Documentation](https://docs.openshift.com/)
- [Ansible Documentation](https://docs.ansible.com/)

## License

This project is for demonstration and educational purposes. 
