variable "proxmox_host" {
  description = "IP address of the Proxmox server"
  default     = "192.168.178.50"
}

variable "proxmox_user" {
  description = "Proxmox API user (e.g. root@pam)"
  default     = "root@pam"
}

variable "proxmox_password" {
  description = "Proxmox API password — never commit this value, use terraform.tfvars"
  sensitive   = true
}

variable "container_ip" {
  description = "Static IP address assigned to the mayl-home LXC container"
  default     = "192.168.178.80/24"
}

variable "gateway" {
  description = "Default network gateway for the LXC container"
  default     = "192.168.178.1"
}

variable "container_hostname" {
  description = "Hostname of the LXC container"
  default     = "mayl-home"
}

variable "container_cores" {
  description = "Number of CPU cores assigned to the container"
  default     = 2
}

variable "container_memory" {
  description = "RAM in MB assigned to the container"
  default     = 4096
}

variable "container_disk" {
  description = "Root disk size for the container"
  default     = "20G"
}
