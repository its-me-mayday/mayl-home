output "container_ip" {
  description = "IP address of the mayl-home container"
  value       = proxmox_lxc.mayl_home.network[0].ip
}

output "container_hostname" {
  description = "Hostname of the mayl-home container"
  value       = proxmox_lxc.mayl_home.hostname
}
